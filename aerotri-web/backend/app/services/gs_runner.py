"""3D Gaussian Splatting (gaussian-splatting) training runner.

This runner launches the external gaussian-splatting optimizer (train.py) on top
of an existing SfM (COLMAP/GLOMAP) result for a Block.

We follow the same pattern as OpenMVSRunner:
- Persist status/progress/logs to DB + disk
- Support cancellation
- Recover orphaned RUNNING tasks on backend restart
"""

from __future__ import annotations

import asyncio
import os
import re
import shutil
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Deque, Dict, List, Optional, Tuple

from sqlalchemy import select

from ..models.block import Block
from ..models.database import AsyncSessionLocal
from ..settings import GS_PYTHON, GS_REPO_PATH


class GSProcessError(Exception):
    """Exception raised when gaussian-splatting training fails."""

    def __init__(self, return_code: int, logs: List[str]):
        self.return_code = return_code
        self.logs = logs
        super().__init__(self._build_message())

    def _build_message(self) -> str:
        msg = f"3DGS training failed with exit code {self.return_code}"
        if self.logs:
            msg += f"\nLast {min(10, len(self.logs))} log lines:\n"
            msg += "\n".join(self.logs[-10:])
        return msg


_TQDM_PERCENT_RE = re.compile(r"Training progress:\s*(\d+)%")


def _list_image_files(images_dir: str) -> List[str]:
    if not os.path.isdir(images_dir):
        return []
    out: List[str] = []
    for name in os.listdir(images_dir):
        lower = name.lower()
        if lower.endswith((".jpg", ".jpeg", ".png")):
            out.append(name)
    return out


def _validate_sparse0(sparse0_dir: str) -> Tuple[bool, str]:
    if not os.path.isdir(sparse0_dir):
        return False, f"sparse/0 not found: {sparse0_dir}"
    required_any = [
        ("cameras.bin", "cameras.txt"),
        ("images.bin", "images.txt"),
        ("points3D.bin", "points3D.txt"),
    ]
    missing = []
    for a, b in required_any:
        if not (os.path.exists(os.path.join(sparse0_dir, a)) or os.path.exists(os.path.join(sparse0_dir, b))):
            missing.append(f"{a}|{b}")
    if missing:
        return False, f"sparse/0 missing files: {', '.join(missing)}"
    return True, ""


def _safe_rmtree(path: str) -> None:
    try:
        if os.path.exists(path):
            shutil.rmtree(path)
    except Exception:
        # best-effort cleanup; don't crash server startup
        pass


class GSRunner:
    """Runner for gaussian-splatting training pipeline."""

    def __init__(self) -> None:
        self._log_buffers: Dict[str, Deque[str]] = {}
        self._processes: Dict[str, asyncio.subprocess.Process] = {}
        self._cancelled: Dict[str, bool] = {}
        self._recovery_done = False

    def _get_buffer(self, block_id: str) -> Deque[str]:
        buf = self._log_buffers.get(block_id)
        if buf is None:
            buf = deque(maxlen=2000)
            self._log_buffers[block_id] = buf
        return buf

    def get_log_tail(self, block_id: str, lines: int = 200) -> List[str]:
        buf = self._log_buffers.get(block_id)
        if buf:
            return list(buf)[-lines:]
        return []

    async def cancel_training(self, block_id: str) -> None:
        self._cancelled[block_id] = True
        proc = self._processes.get(block_id)
        if proc and proc.returncode is None:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                proc.kill()

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Block).where(Block.id == block_id))
            block = result.scalar_one_or_none()
            if not block:
                return
            block.gs_status = "CANCELLED"
            block.gs_current_stage = "cancelled"
            await db.commit()

    async def start_training(
        self,
        block: Block,
        gpu_index: int,
        train_params: dict,
    ) -> None:
        """Public entrypoint: start 3DGS training in background."""
        if not block.output_path:
            raise ValueError("Block has no output_path; SfM output missing.")
        if not GS_PYTHON:
            raise ValueError("GS_PYTHON is not set. Please configure GS_PYTHON env var.")

        gs_root = os.path.join(block.output_path, "gs")
        dataset_dir = os.path.join(gs_root, "dataset")
        model_dir = os.path.join(gs_root, "model")
        log_path = os.path.join(gs_root, "run_gs.log")

        # V1 semantics: keep only the latest run
        _safe_rmtree(gs_root)
        os.makedirs(gs_root, exist_ok=True)

        # Persist initial status
        block.gs_status = "RUNNING"
        block.gs_current_stage = "initializing"
        block.gs_progress = 0.0
        block.gs_output_path = gs_root
        block.gs_error_message = None
        block.gs_statistics = {
            "stage_times": {},
            "total_time": 0.0,
            "params": train_params,
            "gpu_index": gpu_index,
        }

        async with AsyncSessionLocal() as db:
            # refresh persistent instance
            result = await db.execute(select(Block).where(Block.id == block.id))
            db_block = result.scalar_one_or_none()
            if not db_block:
                raise ValueError("Block not found.")
            db_block.gs_status = block.gs_status
            db_block.gs_current_stage = block.gs_current_stage
            db_block.gs_progress = block.gs_progress
            db_block.gs_output_path = block.gs_output_path
            db_block.gs_error_message = block.gs_error_message
            db_block.gs_statistics = block.gs_statistics
            await db.commit()

        asyncio.create_task(
            self._run_training(
                block_id=block.id,
                gpu_index=gpu_index,
                gs_root=gs_root,
                dataset_dir=dataset_dir,
                model_dir=model_dir,
                log_path=log_path,
                train_params=train_params,
            )
        )

    def _prepare_dataset(self, block: Block, dataset_dir: str) -> Tuple[str, str]:
        images_src = block.working_image_path or block.image_path
        sparse0_src = os.path.join(block.output_path or "", "sparse", "0")

        os.makedirs(dataset_dir, exist_ok=True)

        # images: symlink the whole directory to avoid heavy per-file linking
        images_link = os.path.join(dataset_dir, "images")
        if os.path.lexists(images_link):
            os.unlink(images_link)
        os.symlink(images_src, images_link)

        # sparse/0: symlink the folder
        sparse_dir = os.path.join(dataset_dir, "sparse")
        os.makedirs(sparse_dir, exist_ok=True)
        sparse0_link = os.path.join(sparse_dir, "0")
        if os.path.lexists(sparse0_link):
            os.unlink(sparse0_link)
        os.symlink(sparse0_src, sparse0_link)

        # validations
        images = _list_image_files(images_src)
        if not images:
            raise ValueError(f"No images found under: {images_src}")

        ok, msg = _validate_sparse0(sparse0_src)
        if not ok:
            raise ValueError(msg)

        return images_src, sparse0_src

    async def _run_training(
        self,
        block_id: str,
        gpu_index: int,
        gs_root: str,
        dataset_dir: str,
        model_dir: str,
        log_path: str,
        train_params: dict,
    ) -> None:
        start_ts = time.time()
        buf = self._get_buffer(block_id)

        stage_times: Dict[str, float] = {}

        def log(line: str) -> None:
            buf.append(line)
            try:
                with open(log_path, "a", encoding="utf-8", errors="replace") as fp:
                    fp.write(line + "\n")
            except Exception:
                pass

        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Block).where(Block.id == block_id))
                block = result.scalar_one_or_none()
                if not block:
                    return

                # Stage: dataset_prepare
                block.gs_current_stage = "dataset_prepare"
                await db.commit()

                t0 = time.time()
                self._prepare_dataset(block, dataset_dir)
                stage_times["dataset_prepare"] = time.time() - t0

                os.makedirs(model_dir, exist_ok=True)

                # Stage: training
                block.gs_current_stage = "training"
                await db.commit()

                args = [
                    GS_PYTHON,
                    "train.py",
                    "-s",
                    dataset_dir,
                    "-m",
                    model_dir,
                    "--iterations",
                    str(int(train_params.get("iterations", 7000))),
                    "--resolution",
                    str(int(train_params.get("resolution", 2))),
                    "--data_device",
                    str(train_params.get("data_device", "cpu")),
                    "--sh_degree",
                    str(int(train_params.get("sh_degree", 3))),
                ]

                env = os.environ.copy()
                env["CUDA_VISIBLE_DEVICES"] = str(gpu_index)

                log(f"[GSRunner] cwd={str(GS_REPO_PATH)}")
                log(f"[GSRunner] cmd={' '.join(args)}")
                log(f"[GSRunner] CUDA_VISIBLE_DEVICES={env.get('CUDA_VISIBLE_DEVICES')}")

                proc = await asyncio.create_subprocess_exec(
                    *args,
                    cwd=str(GS_REPO_PATH),
                    env=env,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                )
                self._processes[block_id] = proc

                t_train = time.time()
                last_progress_commit = 0.0

                assert proc.stdout is not None
                while True:
                    if self._cancelled.get(block_id):
                        raise asyncio.CancelledError()

                    line_b = await proc.stdout.readline()
                    if not line_b:
                        break
                    line = line_b.decode("utf-8", errors="replace").rstrip("\n")
                    log(line)

                    m = _TQDM_PERCENT_RE.search(line)
                    if m:
                        pct = float(m.group(1))
                        # commit throttling: at most once per 0.5s to reduce DB writes
                        now = time.time()
                        if now - last_progress_commit > 0.5:
                            block.gs_progress = max(block.gs_progress or 0.0, pct)
                            await db.commit()
                            last_progress_commit = now

                rc = await proc.wait()
                stage_times["training"] = time.time() - t_train

                if self._cancelled.get(block_id):
                    block.gs_status = "CANCELLED"
                    block.gs_current_stage = "cancelled"
                    await db.commit()
                    return

                if rc != 0:
                    raise GSProcessError(return_code=rc, logs=list(buf))

                block.gs_status = "COMPLETED"
                block.gs_current_stage = "completed"
                block.gs_progress = 100.0
                # update statistics
                stats = block.gs_statistics or {}
                stats["stage_times"] = stage_times
                stats["total_time"] = time.time() - start_ts
                block.gs_statistics = stats
                await db.commit()

        except asyncio.CancelledError:
            log("[GSRunner] Cancelled")
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Block).where(Block.id == block_id))
                block = result.scalar_one_or_none()
                if block:
                    block.gs_status = "CANCELLED"
                    block.gs_current_stage = "cancelled"
                    await db.commit()
        except Exception as e:
            log(f"[GSRunner] Error: {e}")
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Block).where(Block.id == block_id))
                block = result.scalar_one_or_none()
                if block:
                    block.gs_status = "FAILED"
                    block.gs_current_stage = "failed"
                    block.gs_error_message = str(e)
                    stats = block.gs_statistics or {}
                    stats["stage_times"] = stage_times
                    stats["total_time"] = time.time() - start_ts
                    block.gs_statistics = stats
                    await db.commit()
        finally:
            self._processes.pop(block_id, None)

    async def recover_orphaned_gs_tasks(self) -> None:
        """Recover 3DGS tasks that were RUNNING when backend was killed."""
        if self._recovery_done:
            return
        self._recovery_done = True

        try:
            import psutil

            # Find active gaussian-splatting training processes
            running_pids = set()
            for proc in psutil.process_iter(["pid", "cmdline"]):
                try:
                    cmdline = proc.info.get("cmdline", []) or []
                    cmd = " ".join(str(x) for x in cmdline)
                    if "train.py" in cmd and "gaussian-splatting" in cmd:
                        running_pids.add(proc.info["pid"])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Block).where(Block.gs_status == "RUNNING"))
                running_blocks = result.scalars().all()
                if not running_blocks:
                    return

                for block in running_blocks:
                    if not block.gs_output_path:
                        block.gs_status = "FAILED"
                        block.gs_error_message = "3DGS lost during backend restart (no output path)"
                        block.gs_current_stage = "failed"
                        continue

                    root = Path(block.gs_output_path)
                    log_file = root / "run_gs.log"

                    # Detect completion by presence of point_cloud.ply
                    pc_dir = root / "model" / "point_cloud"
                    has_ply = False
                    if pc_dir.exists():
                        for ply in pc_dir.glob("iteration_*/point_cloud.ply"):
                            if ply.is_file() and ply.stat().st_size > 0:
                                has_ply = True
                                break

                    if has_ply:
                        block.gs_status = "COMPLETED"
                        block.gs_current_stage = "completed"
                        block.gs_progress = 100.0
                        continue

                    # If log is stale, consider failed; otherwise keep RUNNING
                    if log_file.exists():
                        time_since_update = time.time() - log_file.stat().st_mtime
                        if time_since_update > 1800:  # 30 minutes
                            block.gs_status = "FAILED"
                            block.gs_current_stage = "failed"
                            block.gs_error_message = "3DGS training lost during backend restart (no active process, stale log)"
                    else:
                        block.gs_status = "FAILED"
                        block.gs_current_stage = "failed"
                        block.gs_error_message = "3DGS training lost during backend restart (no log file)"

                await db.commit()
        except Exception:
            # best-effort, don't block startup
            pass


gs_runner = GSRunner()


