"""OpenMVS reconstruction runner.

This module is responsible for running the dense reconstruction pipeline
on top of existing COLMAP/GLOMAP sparse outputs for a Block.
"""

import asyncio
import glob
import os
import shlex
import tempfile
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Deque, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.block import Block
from ..models.database import AsyncSessionLocal
from ..settings import (
    OPENMVS_INTERFACE_COLMAP,
    OPENMVS_DENSIFY,
    OPENMVS_RECONSTRUCT,
    OPENMVS_REFINE,
    OPENMVS_TEXTURE,
)
from .task_runner import task_runner, CERES_LIB_PATH


class OpenMVSProcessError(Exception):
    """Exception raised when an OpenMVS or COLMAP CLI fails."""

    def __init__(self, stage: str, return_code: int, logs: List[str]):
        self.stage = stage
        self.return_code = return_code
        self.logs = logs
        super().__init__(self._build_message())

    def _build_message(self) -> str:
        msg = f"Reconstruction stage '{self.stage}' failed with exit code {self.return_code}"
        if self.logs:
            msg += f"\nLast {min(10, len(self.logs))} log lines:\n"
            msg += "\n".join(self.logs[-10:])
        return msg


QUALITY_PRESETS: Dict[str, Dict[str, float]] = {
    "fast": {
        "reconstruct_decimate": 0.3,
        "reconstruct_thickness": 1.0,
        "refine_resolution_level": 2,
        "refine_max_face_area": 256,
    },
    "balanced": {
        "reconstruct_decimate": 0.5,
        "reconstruct_thickness": 1.5,
        "refine_resolution_level": 1,
        "refine_max_face_area": 128,
    },
    "high": {
        "reconstruct_decimate": 0.7,
        "reconstruct_thickness": 1.5,
        "refine_resolution_level": 0,
        "refine_max_face_area": 64,
    },
}


class OpenMVSRunner:
    """Runner for OpenMVS-based reconstruction pipeline."""

    def __init__(self) -> None:
        # Per-block in-memory log buffers (keyed by block_id)
        self._log_buffers: Dict[str, Deque[str]] = {}
        # Track running reconstruction subprocesses for cancellation
        self._processes: Dict[str, asyncio.subprocess.Process] = {}
        # Simple cancelled flags per block
        self._cancelled: Dict[str, bool] = {}
        self._recovery_done = False

    def _check_stage_completed(
        self,
        stage: str,
        dense_dir: str,
        mesh_dir: str,
        refine_dir: str,
        texture_dir: str,
        log_path: str,
    ) -> bool:
        """Check if a reconstruction stage has already been completed.
        
        Args:
            stage: Stage name (undistort, convert, densify, mesh, refine, texture)
            dense_dir: Path to dense directory
            mesh_dir: Path to mesh directory
            refine_dir: Path to refine directory
            texture_dir: Path to texture directory
            log_path: Path to log file for logging skip messages
            
        Returns:
            True if stage is completed (output files exist), False otherwise
        """
        if stage == "undistort":
            # 检查去畸变输出：
            # - COLMAP image_undistorter (--output_type COLMAP) 通常会生成：
            #   - <dense_dir>/images/*
            #   - <dense_dir>/sparse/{cameras.bin,images.bin,points3D.bin,...}
            #   有些环境也可能把 cameras.bin/txt 写在 dense_dir 根目录。
            #
            # 同时，如果后续阶段产物（scene.mvs / scene_dense.*）已经存在，
            # 也可认为 undistort 已经完成，避免重复执行导致覆盖/清理已有产物。
            images_dir = os.path.join(dense_dir, "images")
            # If later stages exist, undistort must have run.
            if self._check_stage_completed("convert", dense_dir, mesh_dir, refine_dir, texture_dir, log_path):
                return True
            if self._check_stage_completed("densify", dense_dir, mesh_dir, refine_dir, texture_dir, log_path):
                return True

            cameras_bin_candidates = [
                os.path.join(dense_dir, "cameras.bin"),
                os.path.join(dense_dir, "cameras.txt"),
                os.path.join(dense_dir, "sparse", "cameras.bin"),
                os.path.join(dense_dir, "sparse", "cameras.txt"),
            ]
            if os.path.isdir(images_dir):
                # 检查是否有图像文件
                image_files = [
                    f for f in os.listdir(images_dir)
                    if f.lower().endswith(('.jpg', '.jpeg', '.png'))
                ]
                has_cameras = any(os.path.exists(p) and os.path.getsize(p) > 0 for p in cameras_bin_candidates)
                if image_files and has_cameras:
                    return True
            return False
        
        elif stage == "convert":
            # 检查格式转换输出：scene.mvs 文件
            scene_mvs = os.path.join(dense_dir, "scene.mvs")
            if os.path.exists(scene_mvs) and os.path.getsize(scene_mvs) > 0:
                return True
            return False
        
        elif stage == "densify":
            # 检查稠密重建输出：scene_dense.ply 和 scene_dense.mvs
            dense_ply = os.path.join(dense_dir, "scene_dense.ply")
            dense_mvs = os.path.join(dense_dir, "scene_dense.mvs")
            if (os.path.exists(dense_ply) and os.path.getsize(dense_ply) > 0 and
                os.path.exists(dense_mvs) and os.path.getsize(dense_mvs) > 0):
                return True
            return False
        
        elif stage == "mesh":
            # 检查mesh重建输出：scene_dense_mesh.ply（可能在mesh_dir或dense_dir）
            mesh_ply_mesh = os.path.join(mesh_dir, "scene_dense_mesh.ply")
            mesh_ply_dense = os.path.join(dense_dir, "scene_dense_mesh.ply")
            if ((os.path.exists(mesh_ply_mesh) and os.path.getsize(mesh_ply_mesh) > 0) or
                (os.path.exists(mesh_ply_dense) and os.path.getsize(mesh_ply_dense) > 0)):
                return True
            return False
        
        elif stage == "refine":
            # 检查mesh优化输出：scene_dense_refine.ply 或 scene_dense_mesh_refine.ply
            # 可能在refine_dir或dense_dir
            refine_ply_refine1 = os.path.join(refine_dir, "scene_dense_refine.ply")
            refine_ply_refine2 = os.path.join(refine_dir, "scene_dense_mesh_refine.ply")
            refine_ply_dense1 = os.path.join(dense_dir, "scene_dense_refine.ply")
            refine_ply_dense2 = os.path.join(dense_dir, "scene_dense_mesh_refine.ply")
            
            for candidate in [refine_ply_refine1, refine_ply_refine2, refine_ply_dense1, refine_ply_dense2]:
                if os.path.exists(candidate) and os.path.getsize(candidate) > 0:
                    return True
            return False
        
        elif stage == "texture":
            # 检查纹理贴图输出：scene_dense_texture.obj 或 scene_dense_mesh_refine_texture.obj
            # 可能在texture_dir或dense_dir
            texture_obj_texture1 = os.path.join(texture_dir, "scene_dense_texture.obj")
            texture_obj_texture2 = os.path.join(texture_dir, "scene_dense_mesh_refine_texture.obj")
            texture_obj_dense1 = os.path.join(dense_dir, "scene_dense_texture.obj")
            texture_obj_dense2 = os.path.join(dense_dir, "scene_dense_mesh_refine_texture.obj")
            
            for candidate in [texture_obj_texture1, texture_obj_texture2, texture_obj_dense1, texture_obj_dense2]:
                if os.path.exists(candidate) and os.path.getsize(candidate) > 0:
                    return True
            return False
        
        return False

    async def start_reconstruction(
        self,
        block: Block,
        gpu_index: int,
        db: AsyncSession,
        quality_preset: str,
    ) -> None:
        """Public entrypoint: start reconstruction in background."""
        if quality_preset not in QUALITY_PRESETS:
            quality_preset = "balanced"

        # Initialize reconstruction fields on the given block
        recon_dir = os.path.join(block.output_path or "", "recon")
        dense_dir = os.path.join(recon_dir, "dense")
        mesh_dir = os.path.join(recon_dir, "mesh")
        refine_dir = os.path.join(recon_dir, "refine")
        texture_dir = os.path.join(recon_dir, "texture")

        os.makedirs(dense_dir, exist_ok=True)
        os.makedirs(mesh_dir, exist_ok=True)
        os.makedirs(refine_dir, exist_ok=True)
        os.makedirs(texture_dir, exist_ok=True)

        block.recon_status = "RUNNING"
        block.recon_current_stage = "initializing"
        block.recon_progress = 0.0
        block.recon_output_path = recon_dir
        block.recon_error_message = None
        block.recon_statistics = {
            "stage_times": {},
            "total_time": 0.0,
            "params": {
                "quality_preset": quality_preset,
                "openmvs": QUALITY_PRESETS[quality_preset],
            },
        }
        await db.commit()

        # Run the actual pipeline in a detached task with its own DB session
        asyncio.create_task(
            self._run_pipeline(
                block_id=block.id,
                gpu_index=gpu_index,
                quality_preset=quality_preset,
                recon_dir=recon_dir,
                dense_dir=dense_dir,
                mesh_dir=mesh_dir,
                refine_dir=refine_dir,
                texture_dir=texture_dir,
            )
        )

    async def _run_pipeline(
        self,
        block_id: str,
        gpu_index: int,
        quality_preset: str,
        recon_dir: str,
        dense_dir: str,
        mesh_dir: str,
        refine_dir: str,
        texture_dir: str,
    ) -> None:
        """Internal: run reconstruction pipeline in its own DB session."""
        stage_times: Dict[str, float] = {}

        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Block).where(Block.id == block_id))
                block = result.scalar_one_or_none()
                if not block:
                    return

                # Basic sanity checks: require existing sparse output
                # Prioritize merged/sparse/0 for partitioned SfM, fallback to sparse/0
                merged_sparse = os.path.join(block.output_path or "", "merged", "sparse", "0")
                regular_sparse = os.path.join(block.output_path or "", "sparse", "0")
                
                if os.path.isdir(merged_sparse) and (
                    os.path.exists(os.path.join(merged_sparse, "images.bin"))
                    or os.path.exists(os.path.join(merged_sparse, "images.txt"))
                ):
                    sparse_dir = merged_sparse
                elif os.path.isdir(regular_sparse) and (
                    os.path.exists(os.path.join(regular_sparse, "images.bin"))
                    or os.path.exists(os.path.join(regular_sparse, "images.txt"))
                ):
                    sparse_dir = regular_sparse
                else:
                    block.recon_status = "FAILED"
                    block.recon_error_message = (
                        f"Sparse output not found for reconstruction: checked {merged_sparse} and {regular_sparse}"
                    )
                    await db.commit()
                    return

                images_dir = block.working_image_path or block.image_path
                if not images_dir or not os.path.isdir(images_dir):
                    block.recon_status = "FAILED"
                    block.recon_error_message = (
                        f"Image directory not found for reconstruction: {images_dir}"
                    )
                    await db.commit()
                    return

                self._log_buffers[block_id] = []
                log_path = os.path.join(recon_dir, "run_recon.log")

                # Helper function to log skip message
                def log_skip(stage_name: str):
                    skip_msg = f"[SKIP] Stage '{stage_name}' already completed, skipping..."
                    self._log_buffers[block_id].append(skip_msg)
                    with open(log_path, "a", encoding="utf-8", buffering=1) as log_fp:
                        log_fp.write(skip_msg + "\n")

                # Stage 0.5: Validate and clean invalid images from reconstruction
                await self._validate_and_clean_images(
                    block_id=block_id,
                    images_dir=images_dir,
                    sparse_dir=sparse_dir,
                    log_path=log_path,
                )
                if self._cancelled.get(block_id):
                    block.recon_status = "CANCELLED"
                    block.recon_current_stage = "cancelled"
                    await db.commit()
                    return

                # Stage 1: COLMAP image undistortion
                if self._check_stage_completed("undistort", dense_dir, mesh_dir, refine_dir, texture_dir, log_path):
                    log_skip("undistort")
                    await self._update_block_stage(
                        db,
                        block,
                        stage="undistort",
                        progress=5.0,
                    )
                    stage_times["undistort"] = 0.0
                else:
                    stage_start = datetime.now()
                    await self._update_block_stage(
                        db,
                        block,
                        stage="undistort",
                        progress=5.0,
                    )
                    await self._run_undistort(
                        block_id=block_id,
                        images_dir=images_dir,
                        sparse_dir=sparse_dir,
                        dense_dir=dense_dir,
                        log_path=log_path,
                    )
                    if self._cancelled.get(block_id):
                        block.recon_status = "CANCELLED"
                        block.recon_current_stage = "cancelled"
                        await db.commit()
                        return
                    stage_times["undistort"] = (
                        datetime.now() - stage_start
                    ).total_seconds()

                # Stage 2: InterfaceCOLMAP -> scene.mvs
                if self._check_stage_completed("convert", dense_dir, mesh_dir, refine_dir, texture_dir, log_path):
                    log_skip("convert")
                    await self._update_block_stage(
                        db,
                        block,
                        stage="convert",
                        progress=15.0,
                    )
                    stage_times["convert"] = 0.0
                else:
                    stage_start = datetime.now()
                    await self._update_block_stage(
                        db,
                        block,
                        stage="convert",
                        progress=15.0,
                    )
                    await self._run_interface_colmap(
                        block_id=block_id,
                        dense_dir=dense_dir,
                        log_path=log_path,
                    )
                    if self._cancelled.get(block_id):
                        block.recon_status = "CANCELLED"
                        block.recon_current_stage = "cancelled"
                        await db.commit()
                        return
                    stage_times["convert"] = (
                        datetime.now() - stage_start
                    ).total_seconds()

                # Stage 3: DensifyPointCloud
                if self._check_stage_completed("densify", dense_dir, mesh_dir, refine_dir, texture_dir, log_path):
                    log_skip("densify")
                    await self._update_block_stage(
                        db,
                        block,
                        stage="densify",
                        progress=35.0,
                    )
                    stage_times["densify"] = 0.0
                else:
                    stage_start = datetime.now()
                    await self._update_block_stage(
                        db,
                        block,
                        stage="densify",
                        progress=35.0,
                    )
                    await self._run_densify(
                        block_id=block_id,
                        dense_dir=dense_dir,
                        gpu_index=gpu_index,
                        log_path=log_path,
                    )
                    if self._cancelled.get(block_id):
                        block.recon_status = "CANCELLED"
                        block.recon_current_stage = "cancelled"
                        await db.commit()
                        return
                    stage_times["densify"] = (
                        datetime.now() - stage_start
                    ).total_seconds()

                # Stage 4: ReconstructMesh
                if self._check_stage_completed("mesh", dense_dir, mesh_dir, refine_dir, texture_dir, log_path):
                    log_skip("mesh")
                    await self._update_block_stage(
                        db,
                        block,
                        stage="mesh",
                        progress=55.0,
                    )
                    stage_times["mesh"] = 0.0
                    # 即使跳过，也要确保文件在正确位置（从dense_dir移动到mesh_dir）
                    self._move_mesh_outputs(dense_dir, mesh_dir)
                else:
                    stage_start = datetime.now()
                    await self._update_block_stage(
                        db,
                        block,
                        stage="mesh",
                        progress=55.0,
                    )
                    await self._run_mesh(
                        block_id=block_id,
                        dense_dir=dense_dir,
                        mesh_dir=mesh_dir,
                        gpu_index=gpu_index,
                        quality_preset=quality_preset,
                        log_path=log_path,
                    )
                    if self._cancelled.get(block_id):
                        block.recon_status = "CANCELLED"
                        block.recon_current_stage = "cancelled"
                        await db.commit()
                        return
                    # ReconstructMesh 由于设置了 --working-folder，输出文件会写到 dense_dir
                    # 需要将输出文件移动到 mesh_dir 以保持目录结构
                    self._move_mesh_outputs(dense_dir, mesh_dir)
                    stage_times["mesh"] = (
                        datetime.now() - stage_start
                    ).total_seconds()

                # Stage 5: RefineMesh
                if self._check_stage_completed("refine", dense_dir, mesh_dir, refine_dir, texture_dir, log_path):
                    log_skip("refine")
                    await self._update_block_stage(
                        db,
                        block,
                        stage="refine",
                        progress=75.0,
                    )
                    stage_times["refine"] = 0.0
                    # 即使跳过，也要确保文件在正确位置（从dense_dir移动到refine_dir）
                    self._move_refine_outputs(dense_dir, refine_dir)
                else:
                    stage_start = datetime.now()
                    await self._update_block_stage(
                        db,
                        block,
                        stage="refine",
                        progress=75.0,
                    )
                    await self._run_refine(
                        block_id=block_id,
                        dense_dir=dense_dir,
                        mesh_dir=mesh_dir,
                        refine_dir=refine_dir,
                        quality_preset=quality_preset,
                        log_path=log_path,
                    )
                    if self._cancelled.get(block_id):
                        block.recon_status = "CANCELLED"
                        block.recon_current_stage = "cancelled"
                        await db.commit()
                        return
                    # RefineMesh 输出也可能写到 dense_dir，需要移动到 refine_dir
                    self._move_refine_outputs(dense_dir, refine_dir)
                    stage_times["refine"] = (
                        datetime.now() - stage_start
                    ).total_seconds()

                # Stage 6: TextureMesh
                if self._check_stage_completed("texture", dense_dir, mesh_dir, refine_dir, texture_dir, log_path):
                    log_skip("texture")
                    await self._update_block_stage(
                        db,
                        block,
                        stage="texture",
                        progress=90.0,
                    )
                    stage_times["texture"] = 0.0
                    # 即使跳过，也要确保文件在正确位置（从dense_dir移动到texture_dir）
                    self._move_texture_outputs(dense_dir, texture_dir)
                else:
                    stage_start = datetime.now()
                    await self._update_block_stage(
                        db,
                        block,
                        stage="texture",
                        progress=90.0,
                    )
                    await self._run_texture(
                        block_id=block_id,
                        dense_dir=dense_dir,
                        refine_dir=refine_dir,
                        texture_dir=texture_dir,
                        gpu_index=gpu_index,
                        log_path=log_path,
                    )
                    if self._cancelled.get(block_id):
                        block.recon_status = "CANCELLED"
                        block.recon_current_stage = "cancelled"
                        await db.commit()
                        return
                    # TextureMesh 输出也可能写到 dense_dir，需要移动到 texture_dir
                    self._move_texture_outputs(dense_dir, texture_dir)
                    stage_times["texture"] = (
                        datetime.now() - stage_start
                    ).total_seconds()

                # Mark reconstruction as completed
                block.recon_status = "COMPLETED"
                block.recon_current_stage = "completed"
                block.recon_progress = 100.0
                stats = block.recon_statistics or {}
                stats_stage_times = stats.get("stage_times", {})
                stats_stage_times.update(stage_times)
                stats["stage_times"] = stats_stage_times
                stats["total_time"] = sum(stats_stage_times.values())
                block.recon_statistics = stats
                await db.commit()

        except Exception as exc:
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Block).where(Block.id == block_id))
                block = result.scalar_one_or_none()
                if not block:
                    return
                # If user cancelled (SIGTERM), do not overwrite with FAILED.
                if self._cancelled.get(block_id):
                    block.recon_status = "CANCELLED"
                    block.recon_current_stage = "cancelled"
                    block.recon_error_message = None
                else:
                    block.recon_status = "FAILED"
                    # Prefer detailed message from OpenMVSProcessError
                    block.recon_error_message = str(exc)
                await db.commit()
        finally:
            self._log_buffers.pop(block_id, None)
            self._processes.pop(block_id, None)
            self._cancelled.pop(block_id, None)

    async def _update_block_stage(
        self,
        db: AsyncSession,
        block: Block,
        stage: str,
        progress: float,
    ) -> None:
        """Update reconstruction stage/progress on Block and notify WS."""
        block.recon_current_stage = stage
        block.recon_progress = progress
        await db.commit()

        # Notify WebSocket listeners via shared task_runner
        await task_runner._notify_progress(  # type: ignore[attr-defined]
            block.id,
            {
                "pipeline": "reconstruction",
                "stage": stage,
                "progress": progress,
                "message": f"Reconstruction stage: {stage}",
            },
        )

    async def _validate_and_clean_images(
        self,
        block_id: str,
        images_dir: str,
        sparse_dir: str,
        log_path: str,
    ) -> None:
        """Validate images in reconstruction and remove invalid ones."""
        from .task_runner import COLMAP_PATH  # Local import to avoid cycles
        
        # First, convert binary format to text format if needed for easier parsing
        images_txt = os.path.join(sparse_dir, "images.txt")
        images_bin = os.path.join(sparse_dir, "images.bin")
        
        # Convert to text format if binary exists but text doesn't
        if os.path.exists(images_bin) and not os.path.exists(images_txt):
            cmd_convert = [
                COLMAP_PATH,
                "model_converter",
                "--input_path",
                sparse_dir,
                "--output_path",
                sparse_dir,
                "--output_type",
                "TXT",
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd_convert,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.wait()
        
        # Read images from reconstruction
        invalid_images = []
        converted_mpo_count = 0
        if os.path.exists(images_txt):
            with open(images_txt, "r", encoding="utf-8") as f:
                lines = f.readlines()
                # Skip header lines (first 4 lines)
                for i in range(4, len(lines), 2):
                    if i >= len(lines):
                        break
                    line = lines[i].strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split()
                    if len(parts) < 10:
                        continue
                    image_name = parts[9]  # Image name is the 10th field
                    image_path = os.path.join(images_dir, image_name)
                    
                    # Check if image exists and is readable
                    if not os.path.exists(image_path):
                        invalid_images.append(image_name)
                        continue
                    
                    # Try to validate image using PIL
                    try:
                        from PIL import Image
                        with Image.open(image_path) as img:
                            img.verify()
                            # Re-open to check format (verify() closes the image)
                            with Image.open(image_path) as img2:
                                # Convert MPO (DJI stereo images) to JPEG
                                if img2.format == 'MPO':
                                    try:
                                        # Extract first frame and save as JPEG
                                        with Image.open(image_path) as mpo_img:
                                            # Seek to first frame (default is already first)
                                            mpo_img.seek(0)
                                            # Convert to RGB if needed
                                            if mpo_img.mode != 'RGB':
                                                mpo_img = mpo_img.convert('RGB')
                                            # Save as JPEG, replacing original
                                            mpo_img.save(image_path, 'JPEG', quality=95)
                                        # Count successful conversion
                                        converted_mpo_count += 1
                                    except Exception as conv_err:
                                        # If conversion fails, mark as invalid
                                        invalid_images.append(image_name)
                                        error_msg = f"[VALIDATE] Failed to convert MPO {image_name}: {str(conv_err)}"
                                        self._log_buffers[block_id].append(error_msg)
                                        with open(log_path, "a", encoding="utf-8", buffering=1) as log_fp:
                                            log_fp.write(error_msg + "\n")
                                # Reject other non-standard formats
                                elif img2.format not in ['JPEG', 'PNG', 'TIFF', 'BMP']:
                                    invalid_images.append(image_name)
                    except Exception:
                        invalid_images.append(image_name)
        
        # Log MPO conversion summary
        if converted_mpo_count > 0:
            summary_msg = f"[VALIDATE] Converted {converted_mpo_count} MPO images to JPEG format"
            self._log_buffers[block_id].append(summary_msg)
            with open(log_path, "a", encoding="utf-8", buffering=1) as log_fp:
                log_fp.write(summary_msg + "\n")
        
        # Remove invalid images from reconstruction
        if invalid_images:
            log_msg = f"[VALIDATE] Found {len(invalid_images)} invalid images, removing from reconstruction..."
            self._log_buffers[block_id].append(log_msg)
            with open(log_path, "a", encoding="utf-8", buffering=1) as log_fp:
                log_fp.write(log_msg + "\n")
                for img_name in invalid_images:
                    log_fp.write(f"  - {img_name}\n")
            
            # Use COLMAP image_deleter to remove invalid images
            # Create a temporary file with image names to delete
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as tmp_file:
                for img_name in invalid_images:
                    tmp_file.write(img_name + '\n')
                tmp_file_path = tmp_file.name
            
            try:
                cmd_delete = [
                    COLMAP_PATH,
                    "image_deleter",
                    "--input_path",
                    sparse_dir,
                    "--output_path",
                    sparse_dir,
                    "--image_names_path",
                    tmp_file_path,
                ]
                proc = await asyncio.create_subprocess_exec(
                    *cmd_delete,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await proc.communicate()
                await proc.wait()
                
                # Log the result
                if proc.returncode == 0:
                    success_msg = f"[VALIDATE] Successfully removed {len(invalid_images)} invalid image(s) from reconstruction"
                    self._log_buffers[block_id].append(success_msg)
                    with open(log_path, "a", encoding="utf-8", buffering=1) as log_fp:
                        log_fp.write(success_msg + "\n")
                else:
                    error_msg = f"[WARNING] Failed to remove invalid images: {stderr.decode('utf-8', errors='ignore')}"
                    self._log_buffers[block_id].append(error_msg)
                    with open(log_path, "a", encoding="utf-8", buffering=1) as log_fp:
                        log_fp.write(error_msg + "\n")
            finally:
                # Clean up temporary file
                try:
                    os.unlink(tmp_file_path)
                except Exception:
                    pass

    async def _run_undistort(
        self,
        block_id: str,
        images_dir: str,
        sparse_dir: str,
        dense_dir: str,
        log_path: str,
    ) -> None:
        from .task_runner import COLMAP_PATH  # Local import to avoid cycles

        cmd = [
            COLMAP_PATH,
            "image_undistorter",
            "--image_path",
            images_dir,
            "--input_path",
            sparse_dir,
            "--output_path",
            dense_dir,
            "--output_type",
            "COLMAP",
            "--max_image_size",
            "3200",
        ]
        await self._run_process(
            block_id=block_id,
            stage="undistort",
            cmd=cmd,
            log_path=log_path,
        )

    async def _run_interface_colmap(
        self,
        block_id: str,
        dense_dir: str,
        log_path: str,
    ) -> None:
        # 在 dense 目录下运行 InterfaceCOLMAP，并把 dense_dir 作为工作目录，
        # 这样后续生成的 scene.mvs 中相对路径会以该目录为基准。
        dense_dir_abs = str(Path(dense_dir).resolve())
        scene_path = os.path.join(dense_dir_abs, "scene.mvs")
        cmd = [
            str(OPENMVS_INTERFACE_COLMAP),
            "-i",
            dense_dir_abs,
            "-o",
            scene_path,
            "--image-folder",
            os.path.join(dense_dir_abs, "images"),
            "-v",
            "2",
        ]
        env = os.environ.copy()
        env["PWD"] = dense_dir_abs
        await self._run_process(
            block_id=block_id,
            stage="convert",
            cmd=cmd,
            log_path=log_path,
            cwd=dense_dir_abs,
            env=env,
        )

    async def _run_densify(
        self,
        block_id: str,
        dense_dir: str,
        gpu_index: int,
        log_path: str,
    ) -> None:
        # 在 dense 目录下运行 DensifyPointCloud，并显式设置 working-folder，
        # 保证 .mvs 中的相对路径 images/* 解析到 recon/dense/images，而不是后端工作目录。
        dense_dir_abs = str(Path(dense_dir).resolve())
        scene_path = os.path.join(dense_dir_abs, "scene.mvs")
        cmd = [
            str(OPENMVS_DENSIFY),
            scene_path,
            "--working-folder",
            dense_dir_abs,
            "--cuda-device",
            str(gpu_index),
            "--resolution-level",
            "1",
            "--number-views",
            "5",
            "--number-views-fuse",
            "3",
            "--estimate-colors",
            "1",
            "--estimate-normals",
            "1",
            "-v",
            "2",
        ]
        env = os.environ.copy()
        env["PWD"] = dense_dir_abs
        await self._run_process(
            block_id=block_id,
            stage="densify",
            cmd=cmd,
            log_path=log_path,
            cwd=dense_dir_abs,
            env=env,
        )

    def _move_mesh_outputs(self, dense_dir: str, mesh_dir: str) -> None:
        """Move mesh output files from dense_dir to mesh_dir.
        
        ReconstructMesh writes outputs to working-folder (dense_dir) instead of cwd.
        This function moves the output files to the expected mesh_dir location.
        """
        import shutil
        
        files_to_move = [
            "scene_dense_mesh.ply",
            "scene_dense_mesh.mvs",  # 如果存在
        ]
        
        for filename in files_to_move:
            src = os.path.join(dense_dir, filename)
            dst = os.path.join(mesh_dir, filename)
            if os.path.exists(src) and not os.path.exists(dst):
                try:
                    shutil.move(src, dst)
                except Exception:
                    # 如果移动失败，尝试复制
                    try:
                        shutil.copy2(src, dst)
                    except Exception:
                        pass  # 忽略错误，让后续阶段处理

    def _move_refine_outputs(self, dense_dir: str, refine_dir: str) -> None:
        """Move refine output files from dense_dir to refine_dir.
        
        RefineMesh may write outputs to working-folder (dense_dir) instead of cwd.
        This function moves the output files to the expected refine_dir location.
        Note: OpenMVS may output either 'scene_dense_refine.ply' or 'scene_dense_mesh_refine.ply'.
        """
        import shutil
        
        # OpenMVS 可能输出不同的文件名，需要检查所有可能的变体
        files_to_move = [
            "scene_dense_refine.ply",  # 常见格式
            "scene_dense_mesh_refine.ply",  # 带 mesh 前缀的格式
            "scene_dense_refine.mvs",  # 如果存在
            "scene_dense_mesh_refine.mvs",  # 如果存在
        ]
        
        for filename in files_to_move:
            src = os.path.join(dense_dir, filename)
            dst = os.path.join(refine_dir, filename)
            if os.path.exists(src) and not os.path.exists(dst):
                try:
                    shutil.move(src, dst)
                except Exception:
                    # 如果移动失败，尝试复制
                    try:
                        shutil.copy2(src, dst)
                    except Exception:
                        pass  # 忽略错误，让后续阶段处理

    def _move_texture_outputs(self, dense_dir: str, texture_dir: str) -> None:
        """Move texture output files from dense_dir to texture_dir.
        
        TextureMesh may write outputs to working-folder (dense_dir) instead of cwd.
        This function moves the output files to the expected texture_dir location.
        Note: OpenMVS may output 'scene_dense_texture.*' or 'scene_dense_mesh_refine_texture.*'.
        """
        import shutil
        import glob
        
        # TextureMesh 输出多种文件：.obj, .mtl, .png, .jpg 等
        # 使用通配符匹配所有可能的纹理相关文件
        # OpenMVS 可能输出两种命名模式：
        # 1. scene_dense_texture.* (常见)
        # 2. scene_dense_mesh_refine_texture.* (带完整前缀)
        patterns = [
            "scene_dense_texture.obj",
            "scene_dense_texture.mtl",
            "scene_dense_texture_*.png",
            "scene_dense_texture_*.jpg",
            "scene_dense_texture_*.jpeg",
            "scene_dense_mesh_refine_texture.obj",
            "scene_dense_mesh_refine_texture.mtl",
            "scene_dense_mesh_refine_texture_*.png",
            "scene_dense_mesh_refine_texture_*.jpg",
            "scene_dense_mesh_refine_texture_*.jpeg",
        ]
        
        for pattern in patterns:
            for src in glob.glob(os.path.join(dense_dir, pattern)):
                filename = os.path.basename(src)
                dst = os.path.join(texture_dir, filename)
                if not os.path.exists(dst):
                    try:
                        shutil.move(src, dst)
                    except Exception:
                        # 如果移动失败，尝试复制
                        try:
                            shutil.copy2(src, dst)
                        except Exception:
                            pass  # 忽略错误

    async def _run_mesh(
        self,
        block_id: str,
        dense_dir: str,
        mesh_dir: str,
        gpu_index: int,
        quality_preset: str,
        log_path: str,
    ) -> None:
        params = QUALITY_PRESETS.get(quality_preset, QUALITY_PRESETS["balanced"])
        # 使用 dense 目录作为 OpenMVS 的 working-folder，以便 scene_dense.mvs
        # 中的相对图像路径仍然解析到 recon/dense/images 下。
        # 注意：由于设置了 --working-folder，输出文件会写到 dense_dir，需要在
        # 阶段完成后移动到 mesh_dir。
        dense_dir_abs = str(Path(dense_dir).resolve())
        dense_mvs = os.path.join(dense_dir_abs, "scene_dense.mvs")
        cmd = [
            str(OPENMVS_RECONSTRUCT),
            dense_mvs,
            "--working-folder",
            dense_dir_abs,
            "--cuda-device",
            str(gpu_index),
            "--thickness-factor",
            str(params["reconstruct_thickness"]),
            "--quality-factor",
            "1.0",
            "--decimate",
            str(params["reconstruct_decimate"]),
            "-v",
            "2",
        ]
        env = os.environ.copy()
        env["PWD"] = mesh_dir
        await self._run_process(
            block_id=block_id,
            stage="mesh",
            cmd=cmd,
            log_path=log_path,
            cwd=mesh_dir,
            env=env,
        )

    async def _run_refine(
        self,
        block_id: str,
        dense_dir: str,
        mesh_dir: str,
        refine_dir: str,
        quality_preset: str,
        log_path: str,
    ) -> None:
        params = QUALITY_PRESETS.get(quality_preset, QUALITY_PRESETS["balanced"])
        # Refine 阶段仍然依赖 scene_dense.mvs 中的图像路径，因此 working-folder
        # 也需要指向 dense 目录；输出文件则位于 refine_dir。
        # scene_dense.mvs 在 dense_dir 下，mesh 输出可能在 mesh_dir 或 dense_dir。
        dense_dir_abs = str(Path(dense_dir).resolve())
        dense_mvs = os.path.join(dense_dir_abs, "scene_dense.mvs")
        # 优先从 mesh_dir 读取，如果不存在则从 dense_dir 读取
        mesh_ply = os.path.join(mesh_dir, "scene_dense_mesh.ply")
        if not os.path.exists(mesh_ply):
            mesh_ply = os.path.join(dense_dir_abs, "scene_dense_mesh.ply")
        cmd = [
            str(OPENMVS_REFINE),
            dense_mvs,
            "-m",
            mesh_ply,
            "--working-folder",
            dense_dir_abs,
            "--resolution-level",
            str(params["refine_resolution_level"]),
            "--max-face-area",
            str(params["refine_max_face_area"]),
            "--scales",
            "2",
            "--reduce-memory",
            "1",
            "-v",
            "2",
        ]
        env = os.environ.copy()
        env["PWD"] = refine_dir
        await self._run_process(
            block_id=block_id,
            stage="refine",
            cmd=cmd,
            log_path=log_path,
            cwd=refine_dir,
            env=env,
        )

    async def _run_texture(
        self,
        block_id: str,
        dense_dir: str,
        refine_dir: str,
        texture_dir: str,
        gpu_index: int,
        log_path: str,
    ) -> None:
        # 纹理阶段同样需要访问原始图像，working-folder 仍然应为 dense 目录；
        # 输出 OBJ/MTL/纹理图写入 texture_dir。
        # scene_dense.mvs 在 dense_dir 下，refine 输出可能在 refine_dir 或 dense_dir。
        dense_dir_abs = str(Path(dense_dir).resolve())
        dense_mvs = os.path.join(dense_dir_abs, "scene_dense.mvs")
        # 优先从 refine_dir 读取，如果不存在则从 dense_dir 读取
        # OpenMVS 可能输出 'scene_dense_refine.ply' 或 'scene_dense_mesh_refine.ply'
        refine_ply = None
        possible_names = [
            "scene_dense_refine.ply",
            "scene_dense_mesh_refine.ply",
        ]
        for name in possible_names:
            candidate = os.path.join(refine_dir, name)
            if os.path.exists(candidate):
                refine_ply = candidate
                break
        if not refine_ply:
            # 如果 refine_dir 中没有，尝试从 dense_dir 读取
            for name in possible_names:
                candidate = os.path.join(dense_dir_abs, name)
                if os.path.exists(candidate):
                    refine_ply = candidate
                    break
        if not refine_ply:
            # 如果都找不到，使用默认名称（优先 scene_dense_refine.ply）
            refine_ply = os.path.join(refine_dir, "scene_dense_refine.ply")
        cmd = [
            str(OPENMVS_TEXTURE),
            dense_mvs,
            "-m",
            refine_ply,
            "--working-folder",
            dense_dir_abs,
            "--cuda-device",
            str(gpu_index),
            "--resolution-level",
            "0",
            "--min-resolution",
            "1024",
            "--export-type",
            "obj",
            "-v",
            "2",
        ]
        env = os.environ.copy()
        env["PWD"] = texture_dir
        await self._run_process(
            block_id=block_id,
            stage="texture",
            cmd=cmd,
            log_path=log_path,
            cwd=texture_dir,
            env=env,
        )

    async def _run_process(
        self,
        block_id: str,
        stage: str,
        cmd: List[str],
        log_path: str,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> None:
        """Run a subprocess, stream logs to file and in-memory buffer."""
        pretty_cmd = " ".join(shlex.quote(str(x)) for x in cmd)
        buffer = self._log_buffers.setdefault(block_id, deque(maxlen=1000))

        # Prepare environment variables with library paths
        process_env = os.environ.copy()
        if env is not None:
            process_env.update(env)
        # Add Ceres library path (contains all required libraries including absl)
        current_ld_path = process_env.get("LD_LIBRARY_PATH", "")
        if CERES_LIB_PATH not in current_ld_path:
            process_env["LD_LIBRARY_PATH"] = f"{CERES_LIB_PATH}:{current_ld_path}" if current_ld_path else CERES_LIB_PATH

        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a", encoding="utf-8", buffering=1) as log_fp:
            log_fp.write(f"[CMD] {pretty_cmd}\n")

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=cwd,
                env=process_env,
                limit=10 * 1024 * 1024,
            )
            # Register process for cancellation
            self._processes[block_id] = process

            last_ws_update = 0.0

            while True:
                # Check for cooperative cancellation request
                if self._cancelled.get(block_id):
                    process.terminate()

                line = await process.stdout.readline()  # type: ignore[union-attr]
                if not line:
                    break
                line_str = line.decode("utf-8", errors="replace").rstrip("\n")
                if not line_str:
                    continue
                buffer.append(line_str)
                # Persist to log file
                log_fp.write(line_str + "\n")

                # Throttled WS heartbeat for this stage
                now = time.time()
                if now - last_ws_update >= 1.0:
                    last_ws_update = now
                    await task_runner._notify_progress(  # type: ignore[attr-defined]
                        block_id,
                        {
                            "pipeline": "reconstruction",
                            "stage": stage,
                            "progress": 0.0,
                            "message": line_str,
                        },
                    )

            await process.wait()

            if process.returncode != 0:
                # Treat SIGTERM/SIGKILL triggered by user cancellation as CANCELLED, not FAILED.
                # asyncio subprocess returncode is negative signal number when terminated by signal.
                if self._cancelled.get(block_id) or process.returncode in (-15, -2, -9):
                    cancel_msg = f"[CANCELLED] Stage '{stage}' terminated (returncode {process.returncode})"
                    buffer.append(cancel_msg)
                    log_fp.write(cancel_msg + "\n")
                    return
                
                # 对于去畸变阶段，即使程序异常退出（如 SIGSEGV），如果输出文件已生成，也视为成功
                # 注意：COLMAP image_undistorter 在处理完成后，退出阶段存在已知的 SIGSEGV 问题
                if stage == "undistort":
                    try:
                        async with AsyncSessionLocal() as db:
                            result = await db.execute(select(Block).where(Block.id == block_id))
                            block = result.scalar_one_or_none()
                            
                            if block and block.recon_output_path:
                                dense_dir = os.path.join(block.recon_output_path, "dense")
                                
                                # 验证去畸变输出是否已生成
                                # 检查 images 目录和 cameras 文件
                                images_dir = os.path.join(dense_dir, "images")
                                cameras_bin_candidates = [
                                    os.path.join(dense_dir, "cameras.bin"),
                                    os.path.join(dense_dir, "cameras.txt"),
                                    os.path.join(dense_dir, "sparse", "cameras.bin"),
                                    os.path.join(dense_dir, "sparse", "cameras.txt"),
                                ]
                                
                                # 检查是否有图像文件
                                has_images = False
                                if os.path.isdir(images_dir):
                                    image_files = [
                                        f for f in os.listdir(images_dir)
                                        if f.lower().endswith(('.jpg', '.jpeg', '.png'))
                                    ]
                                    has_images = len(image_files) > 0
                                
                                # 检查是否有 cameras 文件
                                has_cameras = any(
                                    os.path.exists(p) and os.path.getsize(p) > 0 
                                    for p in cameras_bin_candidates
                                )
                                
                                # 如果输出文件已生成，视为成功
                                if has_images and has_cameras:
                                    success_msg = (
                                        f"[SUCCESS] Undistort stage completed successfully "
                                        f"despite non-zero exit code {process.returncode}. "
                                        f"Output files validated at {dense_dir}"
                                    )
                                    buffer.append(success_msg)
                                    log_fp.write(success_msg + "\n")
                                    return
                    except Exception as e:
                        # 验证逻辑失败时不要中断主流程，只记录告警并继续按错误处理
                        warning_msg = f"[WARNING] Failed to validate undistort output after non-zero exit: {e}"
                        buffer.append(warning_msg)
                        log_fp.write(warning_msg + "\n")
                
                recent_logs = buffer[-30:]
                raise OpenMVSProcessError(stage, process.returncode, recent_logs)

    async def cancel_reconstruction(self, block_id: str) -> None:
        """Request cancellation of a running reconstruction task."""
        # Mark as cancelled so running _run_process loops can terminate gracefully
        self._cancelled[block_id] = True

        proc = self._processes.get(block_id)
        if proc and proc.returncode is None:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                proc.kill()

        # Update Block status using a fresh DB session
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Block).where(Block.id == block_id))
            block = result.scalar_one_or_none()
            if not block:
                return
            block.recon_status = "CANCELLED"
            block.recon_current_stage = "cancelled"
            # Do not reset recon_progress – keep whatever was last persisted
            await db.commit()

    async def recover_orphaned_reconstructions(self) -> None:
        """Recover reconstruction tasks that were running when backend was killed.
        
        This checks the database for tasks with recon_status=RUNNING and:
        1. Checks if their processes still exist
        2. Checks if output files exist (to determine if completed)
        3. If not, marks them as FAILED with appropriate error message
        """
        if self._recovery_done:
            return
        
        self._recovery_done = True
        
        try:
            import psutil
            
            async with AsyncSessionLocal() as db:
                # Find all blocks with RUNNING reconstruction status
                result = await db.execute(
                    select(Block).where(Block.recon_status == "RUNNING")
                )
                running_blocks = result.scalars().all()
                
                if not running_blocks:
                    return
                
                print(f"Found {len(running_blocks)} reconstruction tasks in RUNNING state, checking for orphaned processes...")
                
                # Get all running OpenMVS/COLMAP processes
                running_pids = set()
                for proc in psutil.process_iter(['pid', 'cmdline']):
                    try:
                        cmdline = proc.info.get('cmdline', [])
                        if cmdline and any(
                            'InterfaceCOLMAP' in str(arg) or 
                            'DensifyPointCloud' in str(arg) or
                            'ReconstructMesh' in str(arg) or
                            'RefineMesh' in str(arg) or
                            'TextureMesh' in str(arg) or
                            'image_undistorter' in str(arg).lower()
                            for arg in cmdline
                        ):
                            running_pids.add(proc.info['pid'])
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                
                print(f"Found {len(running_pids)} active OpenMVS/COLMAP processes")
                
                # Check each RUNNING reconstruction
                for block in running_blocks:
                    if not block.recon_output_path:
                        # No output path, mark as failed
                        block.recon_status = "FAILED"
                        block.recon_error_message = "Reconstruction lost during backend restart (no output path)"
                        block.recon_current_stage = "failed"
                        print(f"Marked reconstruction without output as FAILED: {block.name} ({block.id})")
                        continue
                    
                    recon_dir = Path(block.recon_output_path)
                    log_file = recon_dir / "run_recon.log"
                    
                    # Check if reconstruction has completed by looking for final output files
                    # Check for texture output (final stage)
                    texture_dir = recon_dir / "texture"
                    has_texture = texture_dir.exists() and any(
                        f.name.endswith('.obj') for f in texture_dir.iterdir() if f.is_file()
                    )
                    
                    # Check for refine output (before texture)
                    refine_dir = recon_dir / "refine"
                    has_refine = refine_dir.exists() and any(
                        f.name.endswith('.ply') for f in refine_dir.iterdir() if f.is_file()
                    )
                    
                    # Check for mesh output
                    mesh_dir = recon_dir / "mesh"
                    has_mesh = mesh_dir.exists() and any(
                        f.name.endswith('.ply') for f in mesh_dir.iterdir() if f.is_file()
                    )
                    
                    # Check for dense output
                    dense_dir = recon_dir / "dense"
                    has_dense = dense_dir.exists() and any(
                        f.name.endswith('.ply') for f in dense_dir.iterdir() if f.is_file()
                    )
                    
                    # If we have texture output, reconstruction is completed
                    if has_texture:
                        block.recon_status = "COMPLETED"
                        block.recon_current_stage = "completed"
                        block.recon_progress = 100.0
                        print(f"Recovered completed reconstruction: {block.name} ({block.id})")
                    # If we have refine/mesh/dense but no texture, it might be in progress
                    # Check log file modification time to see if it's still updating
                    elif log_file.exists():
                        import time
                        log_mtime = log_file.stat().st_mtime
                        time_since_update = time.time() - log_mtime
                        
                        # If log hasn't been updated in 30 minutes, consider it orphaned
                        if time_since_update > 1800:  # 30 minutes
                            block.recon_status = "FAILED"
                            block.recon_error_message = f"Reconstruction process lost during backend restart (log not updated for {int(time_since_update/60)} minutes)"
                            block.recon_current_stage = "failed"
                            print(f"Marked orphaned reconstruction as FAILED: {block.name} ({block.id}) - log not updated for {int(time_since_update/60)} minutes")
                        else:
                            # Log was recently updated, might still be running
                            # Check if process exists
                            # For now, we'll leave it as RUNNING if log is recent
                            print(f"Reconstruction {block.name} ({block.id}) log was updated {int(time_since_update/60)} minutes ago, keeping as RUNNING")
                    else:
                        # No log file and no output, definitely failed
                        block.recon_status = "FAILED"
                        block.recon_error_message = "Reconstruction process lost during backend restart (no log file found)"
                        block.recon_current_stage = "failed"
                        print(f"Marked reconstruction without log as FAILED: {block.name} ({block.id})")
                
                await db.commit()
                print("Reconstruction recovery completed")
                
        except Exception as e:
            print(f"Error during reconstruction recovery: {e}")
            import traceback
            traceback.print_exc()
    
    def get_log_tail(self, block_id: str, lines: int = 200) -> Optional[List[str]]:
        """Get the last N lines of reconstruction log for a block."""
        # Prefer in-memory buffer when running
        if block_id in self._log_buffers:
            buf = self._log_buffers[block_id]
            return list(buf)[-lines:]

        # Fallback to persisted run_recon.log on disk
        # We infer path from typical layout: <output>/recon/run_recon.log
        base_outputs_dir = "/root/work/aerotri-web/data/outputs"
        recon_log = Path(base_outputs_dir) / block_id / "recon" / "run_recon.log"
        if not recon_log.is_file():
            return None

        dq: Deque[str] = deque(maxlen=lines)
        try:
            with open(recon_log, "r", encoding="utf-8", errors="replace") as fp:
                for line in fp:
                    dq.append(line.rstrip("\n"))
        except Exception:
            return None

        return list(dq)


# Singleton runner
openmvs_runner = OpenMVSRunner()


