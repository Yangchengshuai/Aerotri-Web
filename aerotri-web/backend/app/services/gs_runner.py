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
import socket
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Deque, Dict, List, Optional, Tuple

from sqlalchemy import select

from ..models.block import Block
from ..models.database import AsyncSessionLocal
from ..conf.settings import get_settings

from .gs_tiles_runner import gs_tiles_runner  # 用于复用 PLY → SPZ 转换逻辑
from .task_notifier import task_notifier
from .task_runner_integration import on_task_failure

# Load 3DGS configuration from new system
_settings = get_settings()

GS_PYTHON = str(_settings.gaussian_splatting.python)
GS_REPO_PATH = str(_settings.gaussian_splatting.repo_path)
TENSORBOARD_PATH = str(_settings.gaussian_splatting.tensorboard_path)
TENSORBOARD_PORT_START = _settings.gaussian_splatting.tensorboard_port_start
TENSORBOARD_PORT_END = _settings.gaussian_splatting.tensorboard_port_end
NETWORK_GUI_IP = str(_settings.gaussian_splatting.network_gui_ip)
NETWORK_GUI_PORT_START = _settings.gaussian_splatting.network_gui_port_start
NETWORK_GUI_PORT_END = _settings.gaussian_splatting.network_gui_port_end

# Import COLMAP_PATH from task_runner
try:
    from .task_runner import COLMAP_PATH
except ImportError:
    COLMAP_PATH = os.environ.get("COLMAP_PATH", "/usr/local/bin/colmap")


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


def _check_camera_model(sparse0_dir: str) -> Optional[str]:
    """Check camera model in COLMAP sparse reconstruction.
    
    Returns:
        Camera model string (e.g., "OPENCV", "PINHOLE", "SIMPLE_PINHOLE") or None if cannot determine.
    """
    import struct
    
    # Try to read cameras.bin first
    cameras_bin = os.path.join(sparse0_dir, "cameras.bin")
    if os.path.exists(cameras_bin):
        try:
            with open(cameras_bin, "rb") as f:
                num_cameras = struct.unpack("<Q", f.read(8))[0]
                if num_cameras > 0:
                    # Read first camera
                    camera_id = struct.unpack("<I", f.read(4))[0]
                    model_id = struct.unpack("<I", f.read(4))[0]
                    width = struct.unpack("<Q", f.read(8))[0]
                    height = struct.unpack("<Q", f.read(8))[0]
                    num_params = struct.unpack("<Q", f.read(8))[0]
                    
                    # Skip params (we only need model_id)
                    # Params are doubles (8 bytes each)
                    # Note: num_params should be small (typically 1-8), but we read it as uint64
                    # So we need to convert to int safely
                    try:
                        num_params_int = int(num_params)
                        if 0 < num_params_int < 100:  # Sanity check
                            f.read(8 * num_params_int)
                    except (ValueError, OverflowError):
                        # If num_params is invalid, just skip (we already have model_id)
                        pass
                    
                    # Map model_id to model name
                    # COLMAP model IDs: 0=SIMPLE_PINHOLE, 1=PINHOLE, 2=SIMPLE_RADIAL, 3=RADIAL, 4=OPENCV, etc.
                    model_map = {
                        0: "SIMPLE_PINHOLE",
                        1: "PINHOLE",
                        2: "SIMPLE_RADIAL",
                        3: "RADIAL",
                        4: "OPENCV",
                        5: "OPENCV_FISHEYE",
                        6: "FULL_OPENCV",
                        7: "FOV",
                        8: "SIMPLE_RADIAL_FISHEYE",
                        9: "RADIAL_FISHEYE",
                        10: "THIN_PRISM_FISHEYE",
                    }
                    return model_map.get(model_id, "UNKNOWN")
        except Exception as e:
            # Log error for debugging but don't fail
            import traceback
            print(f"[_check_camera_model] Error reading cameras.bin: {e}")
            traceback.print_exc()
            pass
    
    # Fallback: try to read cameras.txt
    cameras_txt = os.path.join(sparse0_dir, "cameras.txt")
    if os.path.exists(cameras_txt):
        try:
            with open(cameras_txt, "r") as f:
                for line in f:
                    if line.strip() and not line.startswith("#"):
                        parts = line.split()
                        if len(parts) >= 4:
                            # Format: CAMERA_ID, MODEL, WIDTH, HEIGHT, PARAMS[]
                            return parts[1]  # MODEL
        except Exception:
            pass
    
    return None


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
        self._tensorboard_processes: Dict[str, asyncio.subprocess.Process] = {}
        self._tensorboard_ports: Dict[str, int] = {}
        self._network_gui_ports: Dict[str, int] = {}
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

    def _find_free_port(self, start_port: int, end_port: int) -> Optional[int]:
        """Find a free port in the given range, excluding already used ports."""
        used_ports = set(self._tensorboard_ports.values()) | set(self._network_gui_ports.values())
        for port in range(start_port, end_port):
            if port in used_ports:
                continue
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(("", port))
                    return port
            except OSError:
                continue
        return None

    async def _start_tensorboard(self, block_id: str, model_dir: str, log_func=None) -> Optional[int]:
        """Start TensorBoard service for a training task.
        
        Returns:
            Port number if successful, None otherwise.
        """
        if not os.path.exists(TENSORBOARD_PATH):
            if log_func:
                log_func(f"[GSRunner] TensorBoard not found at {TENSORBOARD_PATH}, skipping TensorBoard")
            return None

        # Check if model directory exists
        if not os.path.exists(model_dir):
            if log_func:
                log_func(f"[GSRunner] Model directory does not exist: {model_dir}, skipping TensorBoard")
            return None

        # Find a free port
        port = self._find_free_port(TENSORBOARD_PORT_START, TENSORBOARD_PORT_END)
        if not port:
            if log_func:
                log_func(f"[GSRunner] No free port available for TensorBoard (range {TENSORBOARD_PORT_START}-{TENSORBOARD_PORT_END})")
            return None

        # Start TensorBoard process
        cmd = [
            TENSORBOARD_PATH,
            "--logdir", model_dir,
            "--port", str(port),
            "--host", "0.0.0.0",
            "--reload_interval", "5",  # Reload every 5 seconds
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            self._tensorboard_processes[block_id] = proc
            self._tensorboard_ports[block_id] = port

            if log_func:
                log_func(f"[GSRunner] Started TensorBoard on port {port} for {block_id}")
                log_func(f"[GSRunner] TensorBoard URL: http://localhost:{port}")

            # Wait a bit to check if process started successfully
            await asyncio.sleep(1)
            if proc.returncode is not None:
                # Process exited immediately, likely an error
                stderr = await proc.stderr.read()
                error_msg = stderr.decode("utf-8", errors="replace")[:500] if stderr else "Unknown error"
                if log_func:
                    log_func(f"[GSRunner] TensorBoard failed to start: {error_msg}")
                self._tensorboard_processes.pop(block_id, None)
                self._tensorboard_ports.pop(block_id, None)
                return None

            return port
        except Exception as e:
            if log_func:
                log_func(f"[GSRunner] Failed to start TensorBoard: {e}")
            return None

    async def _stop_tensorboard(self, block_id: str, log_func=None) -> None:
        """Stop TensorBoard service for a training task."""
        proc = self._tensorboard_processes.get(block_id)
        if proc:
            try:
                if proc.returncode is None:
                    proc.terminate()
                    try:
                        await asyncio.wait_for(proc.wait(), timeout=5.0)
                    except asyncio.TimeoutError:
                        proc.kill()
                        await proc.wait()
                if log_func:
                    log_func(f"[GSRunner] Stopped TensorBoard for {block_id}")
            except Exception as e:
                if log_func:
                    log_func(f"[GSRunner] Error stopping TensorBoard: {e}")
            finally:
                self._tensorboard_processes.pop(block_id, None)
                self._tensorboard_ports.pop(block_id, None)

    def get_tensorboard_port(self, block_id: str) -> Optional[int]:
        """Get TensorBoard port for a block, if TensorBoard is running."""
        return self._tensorboard_ports.get(block_id)

    def get_network_gui_port(self, block_id: str) -> Optional[int]:
        """Get network_gui port for a block, if network_gui is enabled."""
        return self._network_gui_ports.get(block_id)

    async def cancel_training(self, block_id: str) -> None:
        self._cancelled[block_id] = True
        proc = self._processes.get(block_id)
        if proc and proc.returncode is None:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                proc.kill()

        # Stop TensorBoard
        await self._stop_tensorboard(block_id)

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
        
        # Send task started notification
        asyncio.create_task(task_notifier.on_task_started(
            block_id=block.id,
            block_name=block.name,
            task_type="gs",
        ))

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

    def _prepare_dataset(self, block: Block, dataset_dir: str, log_func=None) -> Tuple[str, str]:
        """Prepare dataset for 3DGS training.
        
        Args:
            block: Block instance
            dataset_dir: Dataset directory to prepare
            log_func: Optional logging function (for async context)
        
        Returns:
            Tuple of (images_source_path, sparse0_source_path)
        """
        images_src = block.working_image_path or block.image_path
        
        # Find sparse reconstruction directory
        # Priority order (same as openmvs_runner):
        # 1. block.output_colmap_path (set by OpenMVG, GLOMAP, etc.)
        # 2. merged/sparse/0 (partitioned SfM)
        # 3. openmvg_global/sparse/0 (OpenMVG fallback)
        # 4. sparse/0 (standard COLMAP)
        sparse0_src = None
        checked_paths = []
        output_path = block.output_path or ""
        
        # Check block.output_colmap_path first (e.g. OpenMVG sets this)
        if block.output_colmap_path and os.path.isdir(block.output_colmap_path):
            # Validate that required files exist
            has_cameras = (
                os.path.exists(os.path.join(block.output_colmap_path, "cameras.bin"))
                or os.path.exists(os.path.join(block.output_colmap_path, "cameras.txt"))
            )
            if has_cameras:
                sparse0_src = block.output_colmap_path
                if log_func:
                    log_func(f"[GSRunner] Using output_colmap_path: {sparse0_src}")
            checked_paths.append(block.output_colmap_path)
        
        # Check merged/sparse/0 for partitioned SfM
        if not sparse0_src:
            merged_sparse = os.path.join(output_path, "merged", "sparse", "0")
            if os.path.isdir(merged_sparse):
                has_cameras = (
                    os.path.exists(os.path.join(merged_sparse, "cameras.bin"))
                    or os.path.exists(os.path.join(merged_sparse, "cameras.txt"))
                )
                if has_cameras:
                    sparse0_src = merged_sparse
                    if log_func:
                        log_func(f"[GSRunner] Using merged/sparse/0: {sparse0_src}")
                checked_paths.append(merged_sparse)
        
        # Check openmvg_global/sparse/0 as fallback
        if not sparse0_src:
            openmvg_sparse = os.path.join(output_path, "openmvg_global", "sparse", "0")
            if os.path.isdir(openmvg_sparse):
                has_cameras = (
                    os.path.exists(os.path.join(openmvg_sparse, "cameras.bin"))
                    or os.path.exists(os.path.join(openmvg_sparse, "cameras.txt"))
                )
                if has_cameras:
                    sparse0_src = openmvg_sparse
                    if log_func:
                        log_func(f"[GSRunner] Using openmvg_global/sparse/0: {sparse0_src}")
                checked_paths.append(openmvg_sparse)
        
        # Check standard sparse/0
        if not sparse0_src:
            standard_sparse = os.path.join(output_path, "sparse", "0")
            if os.path.isdir(standard_sparse):
                has_cameras = (
                    os.path.exists(os.path.join(standard_sparse, "cameras.bin"))
                    or os.path.exists(os.path.join(standard_sparse, "cameras.txt"))
                )
                if has_cameras:
                    sparse0_src = standard_sparse
                    if log_func:
                        log_func(f"[GSRunner] Using sparse/0: {sparse0_src}")
            checked_paths.append(standard_sparse)
        
        if not sparse0_src:
            raise ValueError(
                f"No valid sparse reconstruction found. Checked paths: {checked_paths}"
            )

        os.makedirs(dataset_dir, exist_ok=True)

        # Check camera model - 3DGS only supports PINHOLE or SIMPLE_PINHOLE
        camera_model = _check_camera_model(sparse0_src)
        
        # Default to undistorting if we can't determine the model (safer)
        # Only skip undistortion if we're certain it's PINHOLE or SIMPLE_PINHOLE
        needs_undistort = True  # Default: do undistortion
        if camera_model in ("PINHOLE", "SIMPLE_PINHOLE"):
            needs_undistort = False
        
        if log_func:
            if camera_model:
                log_func(f"[GSRunner] Detected camera model: {camera_model}")
            else:
                log_func(f"[GSRunner] Could not determine camera model, will attempt undistortion")
            if needs_undistort:
                if camera_model:
                    log_func(f"[GSRunner] Camera model {camera_model} requires undistortion. Running COLMAP image_undistorter...")
                else:
                    log_func(f"[GSRunner] Running COLMAP image_undistorter to ensure PINHOLE model...")
        
        if needs_undistort:
            # Need to undistort: use COLMAP image_undistorter
            # This will create undistorted images and PINHOLE camera model
            undistorted_dir = os.path.join(dataset_dir, "undistorted")
            os.makedirs(undistorted_dir, exist_ok=True)
            
            # Run COLMAP image_undistorter
            cmd = [
                COLMAP_PATH,
                "image_undistorter",
                "--image_path", images_src,
                "--input_path", sparse0_src,
                "--output_path", undistorted_dir,
                "--output_type", "COLMAP",
            ]
            
            import subprocess
            if log_func:
                log_func(f"[GSRunner] Running: {' '.join(cmd)}")
            
            # Set up environment with library paths (same as task_runner)
            env = os.environ.copy()
            # Add Ceres library path (contains all required libraries including absl)
            from .task_runner import CERES_LIB_PATH
            current_ld_path = env.get("LD_LIBRARY_PATH", "")
            if CERES_LIB_PATH not in current_ld_path:
                env["LD_LIBRARY_PATH"] = f"{CERES_LIB_PATH}:{current_ld_path}" if current_ld_path else CERES_LIB_PATH
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=dataset_dir,
                env=env,
            )
            
            # After undistortion, check output (even if return code is non-zero)
            # COLMAP image_undistorter has known SIGSEGV issues but may still produce valid output
            undistorted_images = os.path.join(undistorted_dir, "images")
            undistorted_sparse_candidates = [
                os.path.join(undistorted_dir, "sparse", "0"),  # Standard path
                os.path.join(undistorted_dir, "sparse"),       # Alternative path
            ]
            
            # Check if output was actually generated
            has_images = os.path.exists(undistorted_images) and len(_list_image_files(undistorted_images)) > 0
            has_sparse = False
            actual_sparse = None
            
            for candidate in undistorted_sparse_candidates:
                if os.path.exists(candidate):
                    cameras_file = os.path.join(candidate, "cameras.bin")
                    if os.path.exists(cameras_file):
                        has_sparse = True
                        actual_sparse = candidate
                        break
            
            if result.returncode != 0:
                # Even with non-zero return code, check if output was generated
                if has_images and has_sparse:
                    # Output exists, treat as success (known COLMAP SIGSEGV issue)
                    if log_func:
                        log_func(
                            f"[GSRunner] Image undistortion completed (output validated despite exit code {result.returncode})"
                        )
                else:
                    # True failure: no output generated
                    error_msg = result.stderr[:500] if result.stderr else result.stdout[:500] if result.stdout else "Unknown error"
                    if log_func:
                        log_func(f"[GSRunner] COLMAP image_undistorter failed: {error_msg}")
                    raise RuntimeError(
                        f"COLMAP image_undistorter failed (camera model: {camera_model}). "
                        f"Error: {error_msg}"
                    )
            else:
                # Return code is 0, but still verify output exists
                if not has_images or not has_sparse:
                    raise RuntimeError(
                        f"COLMAP image_undistorter returned success but did not produce expected output. "
                        f"Expected images at {undistorted_images} and sparse at one of {undistorted_sparse_candidates}"
                    )
                if log_func:
                    log_func(f"[GSRunner] Image undistortion completed successfully")
            
            # Standardize directory structure: ensure we use sparse/0
            target_sparse = os.path.join(undistorted_dir, "sparse", "0")
            if actual_sparse != target_sparse:
                # Move files from sparse/ to sparse/0/
                os.makedirs(target_sparse, exist_ok=True)
                for f in ["cameras.bin", "images.bin", "points3D.bin"]:
                    src = os.path.join(actual_sparse, f)
                    dst = os.path.join(target_sparse, f)
                    if os.path.exists(src) and not os.path.exists(dst):
                        shutil.move(src, dst)
                        if log_func:
                            log_func(f"[GSRunner] Moved {f} from sparse/ to sparse/0/")
                actual_sparse = target_sparse
            
            # Final verification
            if not os.path.exists(undistorted_images) or not os.path.exists(actual_sparse):
                raise RuntimeError(
                    f"COLMAP image_undistorter did not produce expected output. "
                    f"Expected: {undistorted_images} and {actual_sparse}"
                )
            
            # Link to undistorted images and sparse
            images_link = os.path.join(dataset_dir, "images")
            if os.path.lexists(images_link):
                os.unlink(images_link)
            os.symlink(undistorted_images, images_link)
            
            sparse_dir = os.path.join(dataset_dir, "sparse")
            os.makedirs(sparse_dir, exist_ok=True)
            sparse0_link = os.path.join(sparse_dir, "0")
            if os.path.lexists(sparse0_link):
                os.unlink(sparse0_link)
            os.symlink(actual_sparse, sparse0_link)
            
            # Update source paths for return value
            images_src = undistorted_images
            sparse0_src = actual_sparse
        else:
            # No undistortion needed: use original images and sparse
            images_link = os.path.join(dataset_dir, "images")
            if os.path.lexists(images_link):
                os.unlink(images_link)
            os.symlink(images_src, images_link)

            sparse_dir = os.path.join(dataset_dir, "sparse")
            os.makedirs(sparse_dir, exist_ok=True)
            sparse0_link = os.path.join(sparse_dir, "0")
            if os.path.lexists(sparse0_link):
                os.unlink(sparse0_link)
            os.symlink(sparse0_src, sparse0_link)

        # validations
        final_images_dir = images_src if needs_undistort else (block.working_image_path or block.image_path)
        images = _list_image_files(final_images_dir)
        if not images:
            raise ValueError(f"No images found under: {final_images_dir}")

        ok, msg = _validate_sparse0(sparse0_src)
        if not ok:
            raise ValueError(msg)
        
        # Verify camera model after processing
        final_camera_model = _check_camera_model(sparse0_src)
        if final_camera_model and final_camera_model not in ("PINHOLE", "SIMPLE_PINHOLE"):
            raise RuntimeError(
                f"Camera model after processing is still {final_camera_model}, "
                "but 3DGS requires PINHOLE or SIMPLE_PINHOLE"
            )

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
                self._prepare_dataset(block, dataset_dir, log_func=log)
                stage_times["dataset_prepare"] = time.time() - t0

                os.makedirs(model_dir, exist_ok=True)

                # Start TensorBoard service
                tb_port = await self._start_tensorboard(block_id, model_dir, log_func=log)
                if tb_port:
                    # Update statistics with TensorBoard port
                    stats = block.gs_statistics or {}
                    stats["tensorboard_port"] = tb_port
                    block.gs_statistics = stats
                    await db.commit()

                # Stage: training
                block.gs_current_stage = "training"
                await db.commit()

                # Build command arguments
                args = [
                    GS_PYTHON,
                    "train.py",
                    "-s",
                    dataset_dir,
                    "-m",
                    model_dir,
                ]
                
                # Basic parameters
                if "iterations" in train_params and train_params["iterations"] is not None:
                    args.extend(["--iterations", str(int(train_params["iterations"]))])
                if "resolution" in train_params and train_params["resolution"] is not None:
                    args.extend(["--resolution", str(int(train_params["resolution"]))])
                if "data_device" in train_params and train_params["data_device"] is not None:
                    args.extend(["--data_device", str(train_params["data_device"])])
                if "sh_degree" in train_params and train_params["sh_degree"] is not None:
                    args.extend(["--sh_degree", str(int(train_params["sh_degree"]))])
                
                # Optimization parameters
                if "position_lr_init" in train_params and train_params["position_lr_init"] is not None:
                    args.extend(["--position_lr_init", str(float(train_params["position_lr_init"]))])
                if "position_lr_final" in train_params and train_params["position_lr_final"] is not None:
                    args.extend(["--position_lr_final", str(float(train_params["position_lr_final"]))])
                if "position_lr_delay_mult" in train_params and train_params["position_lr_delay_mult"] is not None:
                    args.extend(["--position_lr_delay_mult", str(float(train_params["position_lr_delay_mult"]))])
                if "position_lr_max_steps" in train_params and train_params["position_lr_max_steps"] is not None:
                    args.extend(["--position_lr_max_steps", str(int(train_params["position_lr_max_steps"]))])
                if "feature_lr" in train_params and train_params["feature_lr"] is not None:
                    args.extend(["--feature_lr", str(float(train_params["feature_lr"]))])
                if "opacity_lr" in train_params and train_params["opacity_lr"] is not None:
                    args.extend(["--opacity_lr", str(float(train_params["opacity_lr"]))])
                if "scaling_lr" in train_params and train_params["scaling_lr"] is not None:
                    args.extend(["--scaling_lr", str(float(train_params["scaling_lr"]))])
                if "rotation_lr" in train_params and train_params["rotation_lr"] is not None:
                    args.extend(["--rotation_lr", str(float(train_params["rotation_lr"]))])
                if "lambda_dssim" in train_params and train_params["lambda_dssim"] is not None:
                    args.extend(["--lambda_dssim", str(float(train_params["lambda_dssim"]))])
                if "percent_dense" in train_params and train_params["percent_dense"] is not None:
                    args.extend(["--percent_dense", str(float(train_params["percent_dense"]))])
                if "densification_interval" in train_params and train_params["densification_interval"] is not None:
                    args.extend(["--densification_interval", str(int(train_params["densification_interval"]))])
                if "opacity_reset_interval" in train_params and train_params["opacity_reset_interval"] is not None:
                    args.extend(["--opacity_reset_interval", str(int(train_params["opacity_reset_interval"]))])
                if "densify_from_iter" in train_params and train_params["densify_from_iter"] is not None:
                    args.extend(["--densify_from_iter", str(int(train_params["densify_from_iter"]))])
                if "densify_until_iter" in train_params and train_params["densify_until_iter"] is not None:
                    args.extend(["--densify_until_iter", str(int(train_params["densify_until_iter"]))])
                if "densify_grad_threshold" in train_params and train_params["densify_grad_threshold"] is not None:
                    args.extend(["--densify_grad_threshold", str(float(train_params["densify_grad_threshold"]))])
                
                # Advanced parameters
                if train_params.get("white_background", False):
                    args.append("--white_background")
                if train_params.get("random_background", False):
                    args.append("--random_background")
                if "test_iterations" in train_params and train_params["test_iterations"]:
                    args.extend(["--test_iterations"] + [str(int(x)) for x in train_params["test_iterations"]])
                if "save_iterations" in train_params and train_params["save_iterations"]:
                    args.extend(["--save_iterations"] + [str(int(x)) for x in train_params["save_iterations"]])
                if "checkpoint_iterations" in train_params and train_params["checkpoint_iterations"]:
                    args.extend(["--checkpoint_iterations"] + [str(int(x)) for x in train_params["checkpoint_iterations"]])
                if train_params.get("quiet", False):
                    args.append("--quiet")
                
                # Network GUI configuration
                # Only disable if explicitly requested, otherwise enable with port allocation
                if train_params.get("disable_viewer", False):
                    args.append("--disable_viewer")
                else:
                    # Allocate a port for network_gui
                    network_gui_port = self._find_free_port(
                        NETWORK_GUI_PORT_START, NETWORK_GUI_PORT_END
                    )
                    if network_gui_port:
                        self._network_gui_ports[block_id] = network_gui_port
                        args.extend(["--ip", NETWORK_GUI_IP])
                        args.extend(["--port", str(network_gui_port)])
                        log(f"[GSRunner] Network GUI enabled on {NETWORK_GUI_IP}:{network_gui_port}")
                    else:
                        log(f"[GSRunner] No free port for network_gui, disabling viewer")
                        args.append("--disable_viewer")

                env = os.environ.copy()
                env["CUDA_VISIBLE_DEVICES"] = str(gpu_index)
                
                # Set PYTHONPATH to include gaussian-splatting and all submodules
                # This is required for importing diff_gaussian_rasterization, simple_knn, etc.
                gs_repo_str = str(GS_REPO_PATH)
                submodules = [
                    os.path.join(gs_repo_str, "submodules", "diff-gaussian-rasterization"),
                    os.path.join(gs_repo_str, "submodules", "simple-knn"),
                    os.path.join(gs_repo_str, "submodules", "fused-ssim"),
                ]
                pythonpath_parts = [gs_repo_str] + submodules
                current_pythonpath = env.get("PYTHONPATH", "")
                if current_pythonpath:
                    pythonpath_parts.append(current_pythonpath)
                env["PYTHONPATH"] = ":".join(pythonpath_parts)
                
                # Set CUDA architecture for RTX 5090 (Blackwell sm_120) if not already set
                # This ensures CUDA kernels are available for sm_120
                if "TORCH_CUDA_ARCH_LIST" not in env:
                    env["TORCH_CUDA_ARCH_LIST"] = "12.0"
                    log(f"[GSRunner] Set TORCH_CUDA_ARCH_LIST=12.0 for RTX 5090 (sm_120) support")

                log(f"[GSRunner] cwd={str(GS_REPO_PATH)}")
                log(f"[GSRunner] cmd={' '.join(args)}")
                log(f"[GSRunner] CUDA_VISIBLE_DEVICES={env.get('CUDA_VISIBLE_DEVICES')}")
                log(f"[GSRunner] TORCH_CUDA_ARCH_LIST={env.get('TORCH_CUDA_ARCH_LIST', 'not set')}")
                log(f"[GSRunner] PYTHONPATH={env.get('PYTHONPATH', 'not set')}")

                # Increase limit to handle long progress lines (3DGS training may output long lines)
                # Default limit is 64KB, we set it to 10MB to handle very long progress outputs
                proc = await asyncio.create_subprocess_exec(
                    *args,
                    cwd=str(GS_REPO_PATH),
                    env=env,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                    limit=10 * 1024 * 1024,  # 10MB buffer limit
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
                total_time = time.time() - start_ts
                stats["total_time"] = total_time
                block.gs_statistics = stats
                await db.commit()
                
                # Send task completed notification
                await task_notifier.on_task_completed(
                    block_id=block.id,
                    block_name=block.name,
                    task_type="gs",
                    duration=total_time,
                )

                # Optional: export SPZ after training completes
                try:
                    export_spz = bool(train_params.get("export_spz_on_complete"))
                except Exception:
                    export_spz = False

                if export_spz and block.gs_output_path:
                    try:
                        from pathlib import Path

                        gs_output_path = Path(block.gs_output_path)
                        # 复用 3D Tiles runner 的 PLY 查找和 PLY→SPZ 转换逻辑
                        log("[GSRunner] export_spz_on_complete 已启用，开始自动导出 SPZ...")
                        ply_file = await gs_tiles_runner._find_ply_file(gs_output_path, iteration=None)
                        if not ply_file:
                            log("[GSRunner] 自动导出 SPZ: 未找到任何 point_cloud.ply，跳过")
                        else:
                            spz_output_dir = gs_output_path / "3dtiles"
                            spz_output_dir.mkdir(parents=True, exist_ok=True)
                            spz_file = await gs_tiles_runner._convert_ply_to_spz(
                                ply_file, spz_output_dir, block_id
                            )
                            if spz_file and spz_file.exists():
                                size_mb = spz_file.stat().st_size / (1024 * 1024)
                                log(f"[GSRunner] 自动导出 SPZ 完成: {spz_file} ({size_mb:.2f} MB)")
                                # 记录到统计信息，方便前端或运维查看
                                stats = block.gs_statistics or {}
                                stats.setdefault("export_spz", {})
                                stats["export_spz"]["enabled"] = True
                                stats["export_spz"]["spz_path"] = str(spz_file)
                                stats["export_spz"]["spz_size_mb"] = size_mb
                                block.gs_statistics = stats
                                await db.commit()
                            else:
                                log("[GSRunner] 自动导出 SPZ: 转换失败或未生成文件")
                    except Exception as e:
                        # 导出失败不影响训练结果，只在日志中提示
                        log(f"[GSRunner] 自动导出 SPZ 失败（忽略错误）: {e}")

                # Note: TensorBoard is kept running after training completes
                # so users can view the training metrics. It will be stopped
                # when the block is deleted or manually stopped.

        except asyncio.CancelledError:
            log("[GSRunner] Cancelled")
            # Stop TensorBoard on cancellation
            await self._stop_tensorboard(block_id, log_func=log)
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Block).where(Block.id == block_id))
                block = result.scalar_one_or_none()
                if block:
                    block.gs_status = "CANCELLED"
                    block.gs_current_stage = "cancelled"
                    await db.commit()
        except Exception as e:
            log(f"[GSRunner] Error: {e}")
            # Stop TensorBoard on error
            await self._stop_tensorboard(block_id, log_func=log)
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Block).where(Block.id == block_id))
                block = result.scalar_one_or_none()
                if block:
                    block.gs_status = "FAILED"
                    block.gs_current_stage = "failed"
                    block.gs_error_message = str(e)
                    stats = block.gs_statistics or {}
                    stats["stage_times"] = stage_times
                    total_time = time.time() - start_ts
                    stats["total_time"] = total_time
                    block.gs_statistics = stats
                    await db.commit()
                    
                    # Send task failed notification
                    log_tail = list(buf)[-10:] if buf else None
                    await task_notifier.on_task_failed(
                        block_id=block.id,
                        block_name=block.name,
                        task_type="gs",
                        error=str(e),
                        stage=block.gs_current_stage,
                        duration=total_time,
                        log_tail=log_tail,
                    )

                    # Trigger diagnostic agent (async, non-blocking)
                    try:
                        # Store current stage for diagnostic context
                        failed_stage = block.gs_current_stage or "training"
                        asyncio.create_task(on_task_failure(
                            block_id=block.id,
                            task_type="gs",
                            error_message=str(e),
                            stage=failed_stage,
                            auto_fix=True,
                        ))
                    except Exception as diag_e:
                        # Diagnostic failure should not affect main flow
                        log(f"[DIAGNOSTIC] Failed to trigger diagnosis: {diag_e}")
        finally:
            self._processes.pop(block_id, None)
            self._network_gui_ports.pop(block_id, None)

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


