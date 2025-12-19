"""Task runner for COLMAP/GLOMAP execution."""
import os
import asyncio
import time
from datetime import datetime
from typing import Dict, List, Optional
from collections import deque
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.block import Block, BlockStatus, AlgorithmType, MatchingMethod
from ..models.database import AsyncSessionLocal
from .log_parser import LogParser
from .workspace_service import WorkspaceService


# COLMAP/GLOMAP executable paths
COLMAP_PATH = os.environ.get(
    "COLMAP_PATH", 
    # "/root/work/colmap/build_cuda_ceres23_cudss/src/colmap/exe/colmap"
    "/root/work/colmap/build_cuda/src/colmap/exe/colmap"
)
GLOMAP_PATH = os.environ.get(
    "GLOMAP_PATH",
    "/root/work/colmap/build_cuda_ceres23_cudss/src/glomap/glomap"
)
INSTANTSFM_PATH = os.environ.get(
    "INSTANTSFM_PATH",
    "ins-sfm"  # Use conda environment's ins-sfm command
)


class TaskContext:
    """Context for a running task."""
    
    def __init__(self, block_id: str):
        self.block_id = block_id
        self.process: Optional[asyncio.subprocess.Process] = None
        self.log_parser = LogParser()
        self.log_buffer: deque = deque(maxlen=1000)
        self.log_file_path: Optional[str] = None
        self._log_fp = None
        self.started_at: Optional[datetime] = None
        self.current_stage: Optional[str] = None
        self.progress: float = 0.0
        self.cancelled: bool = False

    def open_log_file(self, output_dir: str):
        """Open per-task log file for persistence."""
        try:
            os.makedirs(output_dir, exist_ok=True)
            self.log_file_path = os.path.join(output_dir, "run.log")
            # line-buffered text mode
            self._log_fp = open(self.log_file_path, "a", buffering=1, encoding="utf-8", errors="replace")
        except Exception:
            self.log_file_path = None
            self._log_fp = None

    def close_log_file(self):
        try:
            if self._log_fp:
                self._log_fp.flush()
                self._log_fp.close()
        except Exception:
            pass
        finally:
            self._log_fp = None

    def write_log_line(self, line: str):
        try:
            if self._log_fp:
                self._log_fp.write(line + "\n")
        except Exception:
            pass


class TaskRunner:
    """Runner for COLMAP/GLOMAP tasks."""
    
    def __init__(self):
        self.running_tasks: Dict[str, TaskContext] = {}
        self.ws_connections: Dict[str, List] = {}  # block_id -> list of websocket connections
        self._recovery_done = False
    
    async def recover_orphaned_tasks(self):
        """Recover tasks that were running when backend was killed.
        
        This checks the database for tasks in RUNNING state and:
        1. Checks if their processes still exist
        2. If not, marks them as FAILED with appropriate error message
        """
        if self._recovery_done:
            return
        
        self._recovery_done = True
        
        try:
            import psutil
            
            async with AsyncSessionLocal() as db:
                # Find all RUNNING tasks
                result = await db.execute(
                    select(Block).where(Block.status == BlockStatus.RUNNING)
                )
                running_blocks = result.scalars().all()
                
                if not running_blocks:
                    return
                
                print(f"Found {len(running_blocks)} tasks in RUNNING state, checking for orphaned processes...")
                
                # Get all running colmap/glomap processes
                running_pids = set()
                for proc in psutil.process_iter(['pid', 'cmdline']):
                    try:
                        cmdline = proc.info.get('cmdline', [])
                        if cmdline and any('colmap' in str(arg).lower() or 'glomap' in str(arg).lower() for arg in cmdline):
                            running_pids.add(proc.info['pid'])
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                
                print(f"Found {len(running_pids)} active COLMAP/GLOMAP processes")
                
                # Check each RUNNING block
                for block in running_blocks:
                    # Check if output exists and is valid
                    if block.output_path:
                        sparse_path = os.path.join(block.output_path, "sparse")
                        # Check if sparse output exists and has files
                        has_output = os.path.exists(sparse_path) and len(os.listdir(sparse_path)) > 0
                        
                        if has_output:
                            # Task appears to have completed but status not updated
                            block.status = BlockStatus.COMPLETED
                            block.completed_at = datetime.utcnow()
                            block.current_stage = "completed"
                            block.progress = 100.0
                            print(f"Recovered completed task: {block.name} ({block.id})")
                        else:
                            # No valid output, mark as failed
                            block.status = BlockStatus.FAILED
                            block.error_message = "Task process lost during backend restart (no valid output found)"
                            block.completed_at = datetime.utcnow()
                            print(f"Marked orphaned task as FAILED: {block.name} ({block.id})")
                    else:
                        # No output path, definitely failed
                        block.status = BlockStatus.FAILED
                        block.error_message = "Task lost during backend restart (no output path)"
                        block.completed_at = datetime.utcnow()
                        print(f"Marked task without output as FAILED: {block.name} ({block.id})")
                
                await db.commit()
                print("Task recovery completed")
                
        except Exception as e:
            print(f"Error during task recovery: {e}")
            import traceback
            traceback.print_exc()
    
    async def start_task(
        self, 
        block: Block, 
        gpu_index: int,
        db: AsyncSession
    ):
        """Start a new task for a block.
        
        Args:
            block: Block to process
            gpu_index: GPU index to use
            db: Database session
        """
        if block.id in self.running_tasks:
            raise RuntimeError("Task already running")
        
        # Ensure working dir exists and is populated (safe)
        if not block.working_image_path:
            try:
                block.working_image_path = WorkspaceService.populate_working_dir(block.id, block.image_path)
            except Exception:
                # Don't block task start; fallback to source dir
                block.working_image_path = None

        # Create output directory
        output_path = f"/root/work/aerotri-web/data/outputs/{block.id}"
        os.makedirs(output_path, exist_ok=True)
        
        # Update block status
        block.status = BlockStatus.RUNNING
        block.started_at = datetime.utcnow()
        block.output_path = output_path
        block.current_stage = "initializing"
        block.progress = 0.0
        block.error_message = None
        await db.commit()
        
        # Create task context
        ctx = TaskContext(block.id)
        ctx.started_at = datetime.now()
        ctx.open_log_file(output_path)
        self.running_tasks[block.id] = ctx
        
        # Start task in background
        asyncio.create_task(self._run_task(block.id, gpu_index, ctx))
    
    async def _run_task(
        self,
        block_id: str,
        gpu_index: int,
        ctx: TaskContext
    ):
        """Run the actual task in background (own DB session)."""
        try:
            async with AsyncSessionLocal() as db:
                try:
                    result = await db.execute(select(Block).where(Block.id == block_id))
                    block = result.scalar_one_or_none()
                    if not block:
                        raise RuntimeError(f"Block not found: {block_id}")

                    database_path = os.path.join(block.output_path or "", "database.db")
                    sparse_path = os.path.join(block.output_path or "", "sparse")
                    os.makedirs(sparse_path, exist_ok=True)

                    # Choose safe working image dir if available
                    image_dir = block.working_image_path or block.image_path

                    # Get parameters with defaults
                    feature_params = block.feature_params or {}
                    matching_params = dict(block.matching_params or {})
                    mapper_params = block.mapper_params or {}

                    # Ensure matching method is consistent (fallback to block.matching_method)
                    matching_params.setdefault("method", block.matching_method.value)

                    stage_times = {}

                    # Stage 1: Feature extraction
                    stage_start = datetime.now()
                    ctx.current_stage = "feature_extraction"
                    block.current_stage = "feature_extraction"
                    block.current_detail = None
                    block.progress = 0.0
                    await db.commit()

                    await self._run_feature_extraction(
                        image_dir,
                        database_path,
                        feature_params,
                        gpu_index,
                        ctx,
                        db,
                        block_id,
                        coarse_stage="feature_extraction",
                    )
                    if ctx.cancelled:
                        return
                    stage_times["feature_extraction"] = (datetime.now() - stage_start).total_seconds()

                    # Stage 2: Feature matching
                    stage_start = datetime.now()
                    ctx.current_stage = "matching"
                    block.current_stage = "matching"
                    block.current_detail = None
                    block.progress = 33.0
                    await db.commit()

                    await self._run_matching(
                        database_path,
                        matching_params,
                        gpu_index,
                        ctx,
                        db,
                        block_id,
                        coarse_stage="matching",
                    )
                    if ctx.cancelled:
                        return
                    stage_times["matching"] = (datetime.now() - stage_start).total_seconds()

                    # Stage 3: Mapping (COLMAP or GLOMAP)
                    stage_start = datetime.now()
                    ctx.current_stage = "mapping"
                    block.current_stage = "mapping"
                    block.current_detail = None
                    block.progress = 66.0
                    await db.commit()

                    if block.algorithm == AlgorithmType.GLOMAP:
                        await self._run_glomap_mapper(
                            database_path,
                            image_dir,
                            sparse_path,
                            mapper_params,
                            gpu_index,
                            ctx,
                            db,
                            block_id,
                            coarse_stage="mapping",
                        )
                    elif block.algorithm == AlgorithmType.INSTANTSFM:
                        # For InstantSfM, data_path should be the parent of sparse_path
                        # because InstantSfM writes output to data_path/sparse/0/
                        instantsfm_data_path = block.output_path or ""
                        await self._run_instantsfm_mapper(
                            database_path,
                            image_dir,
                            instantsfm_data_path,  # Use output_path, not sparse_path
                            mapper_params,
                            gpu_index,
                            ctx,
                            db,
                            block_id,
                            coarse_stage="mapping",
                        )
                    else:
                        await self._run_colmap_mapper(
                            database_path,
                            image_dir,
                            sparse_path,
                            mapper_params,
                            gpu_index,
                            ctx,
                            db,
                            block_id,
                            coarse_stage="mapping",
                        )
                    if ctx.cancelled:
                        return
                    stage_times["mapping"] = (datetime.now() - stage_start).total_seconds()

                    # Mark as completed
                    block.status = BlockStatus.COMPLETED
                    block.completed_at = datetime.utcnow()
                    block.current_stage = "completed"
                    block.current_detail = None
                    block.progress = 100.0
                    block.statistics = {
                        "stage_times": stage_times,
                        "total_time": sum(stage_times.values()),
                        "algorithm_params": {
                            "algorithm": block.algorithm.value,
                            "matching_method": block.matching_method.value,
                            "feature_params": feature_params,
                            "matching_params": matching_params,
                            "mapper_params": mapper_params,
                            "gpu_index": gpu_index,
                        },
                    }
                    await db.commit()
                except Exception as e:
                    try:
                        result = await db.execute(select(Block).where(Block.id == block_id))
                        block = result.scalar_one_or_none()
                        if block:
                            block.status = BlockStatus.FAILED
                            block.error_message = str(e)
                            block.completed_at = datetime.utcnow()
                            await db.commit()
                    except Exception:
                        pass
        finally:
            # Cleanup (always)
            if block_id in self.running_tasks:
                ctx.close_log_file()
                del self.running_tasks[block_id]
    
    async def _run_feature_extraction(
        self,
        image_path: str,
        database_path: str,
        params: dict,
        gpu_index: int,
        ctx: TaskContext,
        db: AsyncSession,
        block_id: str,
        coarse_stage: str,
    ):
        """Run COLMAP feature extraction."""
        cmd = [
            COLMAP_PATH, "feature_extractor",
            "--database_path", database_path,
            "--image_path", image_path,
            "--ImageReader.single_camera", str(params.get("single_camera", 1)),
            "--ImageReader.camera_model", params.get("camera_model", "SIMPLE_RADIAL"),
            "--FeatureExtraction.use_gpu", str(params.get("use_gpu", 1)),
            "--FeatureExtraction.gpu_index", str(gpu_index),
            "--SiftExtraction.max_image_size", str(params.get("max_image_size", 2640)),
            "--SiftExtraction.max_num_features", str(params.get("max_num_features", 12000)),
        ]
        
        await self._run_process(cmd, ctx, db, block_id, coarse_stage=coarse_stage)
    
    async def _run_matching(
        self,
        database_path: str,
        params: dict,
        gpu_index: int,
        ctx: TaskContext,
        db: AsyncSession,
        block_id: str,
        coarse_stage: str,
    ):
        """Run COLMAP feature matching."""
        method = params.get("method", "sequential")
        
        if method == "sequential":
            cmd = [
                COLMAP_PATH, "sequential_matcher",
                "--database_path", database_path,
                "--SequentialMatching.overlap", str(params.get("overlap", 20)),
                "--FeatureMatching.use_gpu", str(params.get("use_gpu", 1)),
                "--FeatureMatching.gpu_index", str(gpu_index),
            ]
        elif method == "exhaustive":
            cmd = [
                COLMAP_PATH, "exhaustive_matcher",
                "--database_path", database_path,
                "--FeatureMatching.use_gpu", str(params.get("use_gpu", 1)),
                "--FeatureMatching.gpu_index", str(gpu_index),
            ]
        else:  # vocab_tree
            cmd = [
                COLMAP_PATH, "vocab_tree_matcher",
                "--database_path", database_path,
                "--FeatureMatching.use_gpu", str(params.get("use_gpu", 1)),
                "--FeatureMatching.gpu_index", str(gpu_index),
            ]
        
        await self._run_process(cmd, ctx, db, block_id, coarse_stage=coarse_stage)
    
    async def _run_colmap_mapper(
        self,
        database_path: str,
        image_path: str,
        output_path: str,
        params: dict,
        gpu_index: int,
        ctx: TaskContext,
        db: AsyncSession,
        block_id: str,
        coarse_stage: str,
    ):
        """Run COLMAP incremental mapper."""
        cmd = [
            COLMAP_PATH, "mapper",
            "--database_path", database_path,
            "--image_path", image_path,
            "--output_path", output_path,
            "--Mapper.ba_use_gpu", str(params.get("ba_use_gpu", 1)),
            "--Mapper.ba_gpu_index", str(gpu_index),
        ]
        
        await self._run_process(cmd, ctx, db, block_id, coarse_stage=coarse_stage)
    
    async def _run_glomap_mapper(
        self,
        database_path: str,
        image_path: str,
        output_path: str,
        params: dict,
        gpu_index: int,
        ctx: TaskContext,
        db: AsyncSession,
        block_id: str,
        coarse_stage: str,
    ):
        """Run GLOMAP global mapper."""
        cmd = [
            GLOMAP_PATH, "mapper",
            "--database_path", database_path,
            "--image_path", image_path,
            "--output_path", output_path,
            "--output_format", "bin",
            "--GlobalPositioning.use_gpu", str(params.get("global_positioning_use_gpu", 1)),
            "--GlobalPositioning.gpu_index", str(gpu_index),
            "--GlobalPositioning.min_num_images_gpu_solver", 
                str(params.get("global_positioning_min_num_images_gpu_solver", 50)),
            "--BundleAdjustment.use_gpu", str(params.get("bundle_adjustment_use_gpu", 1)),
            "--BundleAdjustment.gpu_index", str(gpu_index),
            "--BundleAdjustment.min_num_images_gpu_solver",
                str(params.get("bundle_adjustment_min_num_images_gpu_solver", 50)),
        ]
        
        await self._run_process(cmd, ctx, db, block_id, coarse_stage=coarse_stage)
    
    async def _run_instantsfm_mapper(
        self,
        database_path: str,
        image_path: str,
        output_path: str,
        params: dict,
        gpu_index: int,
        ctx: TaskContext,
        db: AsyncSession,
        block_id: str,
        coarse_stage: str,
    ):
        """Run InstantSfM mapper."""
        # InstantSfM expects data_path to be the parent directory containing images/ and database.db
        # The output will be written to data_path/sparse/0/
        # output_path here is block.output_path (parent of sparse/), not sparse_path
        data_path = output_path  # This is block.output_path, which contains database.db
        
        # Ensure images/ subdirectory exists in data_path (create symlink if needed)
        images_dir_in_data = os.path.join(data_path, "images")
        if not os.path.exists(images_dir_in_data):
            # Create symlink to the actual image directory
            try:
                # Remove if it's a broken symlink or existing file/dir
                if os.path.exists(images_dir_in_data) or os.path.islink(images_dir_in_data):
                    if os.path.islink(images_dir_in_data):
                        os.unlink(images_dir_in_data)
                    elif os.path.isdir(images_dir_in_data):
                        # If it's a real directory, we can't symlink over it
                        ctx.write_log_line(f"Warning: {images_dir_in_data} already exists as a directory")
                    else:
                        os.remove(images_dir_in_data)
                
                # Create absolute path for symlink target
                abs_image_path = os.path.abspath(image_path)
                os.symlink(abs_image_path, images_dir_in_data)
                ctx.write_log_line(f"Created symlink: {images_dir_in_data} -> {abs_image_path}")
            except (OSError, FileExistsError) as e:
                ctx.write_log_line(f"Error creating symlink for images directory: {e}")
                raise RuntimeError(f"Failed to create images symlink: {e}")
        
        # Verify database.db exists in data_path
        expected_db_path = os.path.join(data_path, "database.db")
        if not os.path.exists(expected_db_path):
            # If database is in a different location, copy or link it
            if os.path.exists(database_path) and database_path != expected_db_path:
                try:
                    if os.path.islink(expected_db_path):
                        os.unlink(expected_db_path)
                    os.symlink(os.path.abspath(database_path), expected_db_path)
                    ctx.write_log_line(f"Created database symlink: {expected_db_path} -> {database_path}")
                except Exception as e:
                    ctx.write_log_line(f"Warning: Could not link database: {e}")
            else:
                raise RuntimeError(f"Database file not found at {expected_db_path}")
        
        # Verify database is readable and has images table
        try:
            import sqlite3
            test_conn = sqlite3.connect(expected_db_path)
            cursor = test_conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='images'")
            if not cursor.fetchone():
                raise RuntimeError(f"Database {expected_db_path} does not contain 'images' table")
            test_conn.close()
        except Exception as e:
            ctx.write_log_line(f"Database verification error: {e}")
            raise RuntimeError(f"Database verification failed: {e}")
        
        # Build command with conda environment activation
        # Use bash -c to activate conda environment and set environment variables
        # Use GPU index from params if provided and not None, otherwise use the passed gpu_index
        effective_gpu_index = params.get("gpu_index")
        if effective_gpu_index is None:
            effective_gpu_index = gpu_index
        manual_config = params.get("manual_config_name") or "colmap"
        base_cmd_parts = [
            "source /root/miniconda3/etc/profile.d/conda.sh",
            "conda activate instantsfm",
            f"export LD_LIBRARY_PATH=/opt/ceres-2.3.0-cuda-cudss/lib:$LD_LIBRARY_PATH",
            f"export CUDA_VISIBLE_DEVICES={effective_gpu_index}",
            f"{INSTANTSFM_PATH} --data_path {data_path} --manual_config_name {manual_config}"
        ]
        
        # Add optional parameters
        if params.get("export_txt", True):
            base_cmd_parts[-1] += " --export_txt"
        
        if params.get("disable_depths", False):
            base_cmd_parts[-1] += " --disable_depths"
        
        base_cmd = " && ".join(base_cmd_parts)
        cmd = ["bash", "-c", base_cmd]
        
        ctx.write_log_line(f"Running InstantSfM with data_path={data_path}, gpu_index={effective_gpu_index} (from params: {params.get('gpu_index', 'not set')}, fallback: {gpu_index})")
        ctx.write_log_line(f"Command: {' '.join(cmd)}")
        
        # Run the process
        await self._run_process(cmd, ctx, db, block_id, coarse_stage=coarse_stage)
    
    async def _run_process(self, cmd: List[str], ctx: TaskContext, db: AsyncSession, block_id: str, coarse_stage: str):
        """Run a subprocess and capture output.
        
        Args:
            cmd: Command and arguments
            ctx: Task context
        """
        # Increase limit to handle long progress lines (GLOMAP/COLMAP uses \r for progress)
        # Default limit is 64KB, we set it to 10MB to handle very long progress outputs
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            limit=10 * 1024 * 1024,  # 10MB buffer limit
        )
        ctx.process = process

        last_db_update = 0.0
        last_detail = None
        last_progress = -1.0
        
        # Read output line by line
        while True:
            if ctx.cancelled:
                process.terminate()
                break
            
            line = await process.stdout.readline()
            if not line:
                break
            
            line_str = line.decode('utf-8', errors='replace').strip()
            if line_str:
                ctx.log_buffer.append(line_str)
                ctx.write_log_line(line_str)
                
                # Parse progress
                progress = ctx.log_parser.parse_line(line_str)
                if progress:
                    ctx.current_stage = coarse_stage
                    ctx.progress = progress.progress

                    # Update DB with throttling (every 0.5s or on meaningful change)
                    now = time.time()
                    detail_stage = progress.stage
                    overall = self._coarse_to_overall_progress(coarse_stage, progress.progress)
                    if (now - last_db_update) >= 0.5 or detail_stage != last_detail or abs(progress.progress - last_progress) >= 5:
                        try:
                            result = await db.execute(select(Block).where(Block.id == block_id))
                            block = result.scalar_one_or_none()
                            if block:
                                block.current_stage = coarse_stage
                                block.current_detail = detail_stage
                                block.progress = min(99.0, max(block.progress or 0.0, overall)) if coarse_stage != "completed" else 100.0
                                await db.commit()
                        except Exception:
                            # Don't break processing for DB hiccups
                            pass
                        last_db_update = now
                        last_detail = detail_stage
                        last_progress = progress.progress
                    
                    # Notify WebSocket clients
                    await self._notify_progress(ctx.block_id, {
                        "stage": progress.stage,  # detail stage
                        "progress": progress.progress,  # detail stage progress
                        "message": progress.message,
                    })
        
        await process.wait()
        
        if process.returncode != 0 and not ctx.cancelled:
            raise RuntimeError(f"Process exited with code {process.returncode}")

    @staticmethod
    def _coarse_to_overall_progress(coarse_stage: str, stage_progress: float) -> float:
        """Map stage-local progress (0-100) to pipeline overall (0-100)."""
        p = max(0.0, min(100.0, stage_progress))
        if coarse_stage == "feature_extraction":
            return 0.0 + (p * 0.33)
        if coarse_stage == "matching":
            return 33.0 + (p * 0.33)
        if coarse_stage == "mapping":
            return 66.0 + (p * 0.34)
        if coarse_stage == "completed":
            return 100.0
        return p
    
    async def _notify_progress(self, block_id: str, data: dict):
        """Notify WebSocket clients about progress.
        
        Args:
            block_id: Block ID
            data: Progress data
        """
        # Default pipeline for legacy callers (SfM)
        if "pipeline" not in data:
            data["pip