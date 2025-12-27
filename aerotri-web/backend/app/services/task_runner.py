"""Task runner for COLMAP/GLOMAP execution."""
import os
import asyncio
import time
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from collections import deque
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.block import Block, BlockStatus, AlgorithmType, MatchingMethod, GlomapMode
from ..models.database import AsyncSessionLocal
from .log_parser import LogParser
from .workspace_service import WorkspaceService
from .instantsfm_visualizer_proxy import (
    InstantSfMVisualizerProxy,
    register_visualizer_proxy,
    unregister_visualizer_proxy,
    get_visualizer_proxy,
)


# COLMAP/GLOMAP executable paths
COLMAP_PATH = os.environ.get(
    "COLMAP_PATH", 
    # "/root/work/colmap/build_cuda/src/colmap/exe/colmap"
    "/usr/local/bin/colmap"
    # "/root/work/colmap3.11/colmap/build/src/colmap/exe/colmap" # 新编译 3.11 版本
)
GLOMAP_PATH = os.environ.get(
    "GLOMAP_PATH",
    # "/root/work/colmap/build_cuda/src/glomap/glomap"
    "/usr/local/bin/glomap"
    # "/root/work/glomap/build/glomap/glomap" # 新编译 glomap 版本
)
INSTANTSFM_PATH = os.environ.get(
    "INSTANTSFM_PATH",
    "ins-sfm"  # Use conda environment's ins-sfm command
)

# Library paths for runtime dependencies
# Note: CERES_LIB_PATH contains all required libraries including absl
CERES_LIB_PATH = "/root/opt/ceres-2.3-cuda/lib"


class TaskContext:
    """Context for a running task."""
    
    def __init__(self, block_id: str):
        self.block_id = block_id
        self.process: Optional[asyncio.subprocess.Process] = None
        self.log_parser = LogParser()
        self.log_buffer: deque = deque(maxlen=1000)
        self.log_file_path: Optional[str] = None
        self._log_fp = None
        self._global_log_fp = None  # Additional log file for partitioned mode
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
            if self._global_log_fp:
                self._global_log_fp.flush()
                self._global_log_fp.close()
        except Exception:
            pass
        finally:
            self._log_fp = None
            self._global_log_fp = None

    def write_log_line(self, line: str):
        try:
            if self._log_fp:
                self._log_fp.write(line + "\n")
            if self._global_log_fp:
                self._global_log_fp.write(line + "\n")
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
        
        # Check if partitioned SfM mode
        if block.partition_enabled and block.sfm_pipeline_mode == "global_feat_match":
            # Start partitioned SfM task
            asyncio.create_task(self._run_partitioned_sfm(block.id, gpu_index, ctx))
        else:
            # Start regular task in background
            asyncio.create_task(self._run_task(block.id, gpu_index, ctx))
    
    async def start_merge_task(
        self,
        block: Block,
        db: AsyncSession
    ):
        """Start a merge task for completed partitions.
        
        Args:
            block: Block to merge
            db: Database session
        """
        if block.id in self.running_tasks:
            raise RuntimeError("Task already running")
        
        if not block.partition_enabled:
            raise RuntimeError("Block is not in partitioned mode")
        
        if block.current_stage != "partitions_completed":
            raise RuntimeError(f"Block is not ready for merge. Current stage: {block.current_stage}")
        
        if not block.output_path:
            raise RuntimeError("Block has no output path")
        
        # Create task context
        ctx = TaskContext(block.id)
        ctx.started_at = datetime.now()
        merge_log_path = os.path.join(block.output_path, "run_merge.log")
        ctx.open_log_file(os.path.dirname(merge_log_path))
        ctx.log_file_path = merge_log_path
        # Reopen with correct path
        try:
            os.makedirs(os.path.dirname(merge_log_path), exist_ok=True)
            ctx._log_fp = open(merge_log_path, "a", buffering=1, encoding="utf-8", errors="replace")
        except Exception:
            ctx._log_fp = None
        
        self.running_tasks[block.id] = ctx
        
        # Start merge task in background
        asyncio.create_task(self._run_merge_only(block.id, ctx))
    
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

                    # Special pipeline: GLOMAP mapper_resume only (no feature/matching stages)
                    if getattr(block, "glomap_mode", None) == GlomapMode.MAPPER_RESUME:
                        await self._run_glomap_resume_pipeline(block, gpu_index, ctx, db)
                        return

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
    
    async def _run_global_feature_and_matching(
        self,
        block: Block,
        database_path: str,
        image_dir: str,
        feature_params: dict,
        matching_params: dict,
        gpu_index: int,
        ctx: TaskContext,
        db: AsyncSession,
        log_file_path: Optional[str] = None,
    ):
        """Run global feature extraction and matching for partitioned SfM.
        
        This is used when partition_enabled=True and sfm_pipeline_mode="global_feat_match".
        All partitions share the same database.db with global features and matches.
        
        Args:
            block: Block instance
            database_path: Path to database.db
            image_dir: Image directory
            feature_params: Feature extraction parameters
            matching_params: Matching parameters
            gpu_index: GPU index
            ctx: Task context
            db: Database session
            log_file_path: Optional log file path (defaults to run_global.log)
        """
        if log_file_path:
            # For partitioned mode, we want to write to both the main log and the global log
            # Keep the main log file open for frontend compatibility
            # Also write to global log for detailed tracking
            try:
                os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
                # Open global log file in addition to main log
                # The main log file (_log_fp) remains open, we'll write to both
                ctx._global_log_fp = open(log_file_path, "a", buffering=1, encoding="utf-8", errors="replace")
            except Exception:
                ctx._global_log_fp = None
        else:
            ctx._global_log_fp = None
        
        # Stage 1: Feature extraction
        # Use frontend-recognizable stage names: "feature_extraction" instead of "global_feature"
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
            block.id,
            coarse_stage="feature_extraction",  # Use standard stage name for frontend compatibility
        )
        if ctx.cancelled:
            return
        
        # Stage 2: Feature matching
        # Use frontend-recognizable stage names: "matching" instead of "global_matching"
        ctx.current_stage = "matching"
        block.current_stage = "matching"
        block.current_detail = None
        block.progress = 50.0
        await db.commit()
        
        await self._run_matching(
            database_path,
            matching_params,
            gpu_index,
            ctx,
            db,
            block.id,
            coarse_stage="matching",  # Use standard stage name for frontend compatibility
        )
        if ctx.cancelled:
            return
        
        block.current_stage = "matching"  # Keep as "matching" until partition mapping starts
        block.progress = 100.0
        await db.commit()
    
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
            "--ImageReader.single_camera", str(params.get("single_camera", 0)),
            "--ImageReader.camera_model", params.get("camera_model", "OPENCV"),
            "--SiftExtraction.use_gpu", str(params.get("use_gpu", 1)),
            "--SiftExtraction.gpu_index", str(gpu_index),
            "--SiftExtraction.max_image_size", str(params.get("max_image_size", 2640)),
            "--SiftExtraction.max_num_features", str(params.get("max_num_features", 15000)),
        ]
        
        try:
            await self._run_process(cmd, ctx, db, block_id, coarse_stage=coarse_stage)
        except RuntimeError as e:
            # Check if feature extraction actually completed despite SIGSEGV on exit
            if "exited with code" in str(e) and os.path.exists(database_path):
                import sqlite3
                try:
                    conn = sqlite3.connect(database_path)
                    cursor = conn.execute("SELECT COUNT(*) FROM images")
                    image_count = cursor.fetchone()[0]
                    cursor = conn.execute("SELECT COUNT(*) FROM keypoints")
                    keypoint_count = cursor.fetchone()[0]
                    conn.close()
                    
                    if image_count > 0 and keypoint_count > 0:
                        ctx.write_log_line(f"Feature extraction completed despite exit error. Found {image_count} images, {keypoint_count} keypoints.")
                        # Continue execution - output is valid
                        return
                except Exception:
                    pass
            # Re-raise if output validation failed
            raise
    
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
                "--SequentialMatching.overlap", str(params.get("overlap", 10)),
                "--SiftMatching.use_gpu", str(params.get("use_gpu", 1)),
                "--SiftMatching.gpu_index", str(gpu_index),
            ]
        elif method == "exhaustive":
            cmd = [
                COLMAP_PATH, "exhaustive_matcher",
                "--database_path", database_path,
                "--SiftMatching.use_gpu", str(params.get("use_gpu", 1)),
                "--SiftMatching.gpu_index", str(gpu_index),
            ]
        elif method == "spatial":
            # Spatial matching based on image GPS/pose priors
            # Note: COLMAP automatically detects GPS vs Cartesian coordinates from database
            spatial_max_num_neighbors = params.get("spatial_max_num_neighbors", 50)
            spatial_ignore_z = params.get("spatial_ignore_z", False)
            cmd = [
                COLMAP_PATH, "spatial_matcher",
                "--database_path", database_path,
                "--SpatialMatching.max_num_neighbors", str(spatial_max_num_neighbors),
                "--SpatialMatching.ignore_z", "1" if spatial_ignore_z else "0",
                "--SiftMatching.use_gpu", str(params.get("use_gpu", 1)),
                "--SiftMatching.gpu_index", str(gpu_index),
            ]
        elif method == "vocab_tree":
            # Vocabulary tree matching requires a vocab tree file
            vocab_tree_path = params.get("vocab_tree_path") or os.environ.get(
                "COLMAP_VOCAB_TREE_PATH", ""
            )
            if not vocab_tree_path:
                raise RuntimeError(
                    "vocab_tree matching requires 'vocab_tree_path' in matching_params "
                    "or environment variable COLMAP_VOCAB_TREE_PATH"
                )
            cmd = [
                COLMAP_PATH, "vocab_tree_matcher",
                "--database_path", database_path,
                "--VocabTreeMatching.vocab_tree_path", vocab_tree_path,
                "--SiftMatching.use_gpu", str(params.get("use_gpu", 1)),
                "--SiftMatching.gpu_index", str(gpu_index),
            ]
        else:
            raise RuntimeError(f"Unknown matching method: {method}")
        
        try:
            await self._run_process(cmd, ctx, db, block_id, coarse_stage=coarse_stage)
        except RuntimeError as e:
            # Check if matching actually completed despite SIGSEGV on exit
            if "exited with code" in str(e) and os.path.exists(database_path):
                import sqlite3
                try:
                    conn = sqlite3.connect(database_path)
                    cursor = conn.execute("SELECT COUNT(*) FROM matches")
                    match_count = cursor.fetchone()[0]
                    conn.close()
                    
                    if match_count > 0:
                        ctx.write_log_line(f"Matching completed despite exit error. Found {match_count} matches.")
                        # Continue execution - output is valid
                        return
                except Exception:
                    pass
            # Re-raise if output validation failed
            raise
    
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
        def _b(v, default: int = 0) -> int:
            if v is None:
                return default
            if isinstance(v, bool):
                return 1 if v else 0
            return 1 if int(v) != 0 else 0

        use_pose_prior = _b(params.get("use_pose_prior", 0), 0) == 1
        subcmd = "pose_prior_mapper" if use_pose_prior else "mapper"
        cmd = [
            COLMAP_PATH, subcmd,
            "--database_path", database_path,
            "--image_path", image_path,
            "--output_path", output_path,
            "--Mapper.ba_use_gpu", str(_b(params.get("ba_use_gpu", 1), 1)),
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
        def _b(v, default: int = 0) -> int:
            if v is None:
                return default
            if isinstance(v, bool):
                return 1 if v else 0
            return 1 if int(v) != 0 else 0

        def _add_param_if_set(cmd_list, param_key, glomap_flag, param_type=str):
            """Add parameter to command if it exists and is not None."""
            if param_key in params and params[param_key] is not None:
                if param_type == bool:
                    cmd_list.extend([glomap_flag, str(_b(params[param_key]))])
                elif param_type == int:
                    cmd_list.extend([glomap_flag, str(int(params[param_key]))])
                elif param_type == float:
                    cmd_list.extend([glomap_flag, str(float(params[param_key]))])
                else:
                    cmd_list.extend([glomap_flag, str(params[param_key])])

        cmd = [
            GLOMAP_PATH, "mapper",
            "--database_path", database_path,
            "--image_path", image_path,
            "--output_path", output_path,
            "--output_format", "bin",
            "--GlobalPositioning.use_gpu", str(_b(params.get("global_positioning_use_gpu", 1), 1)),
            "--GlobalPositioning.gpu_index", str(gpu_index),
            "--BundleAdjustment.use_gpu", str(_b(params.get("bundle_adjustment_use_gpu", 1), 1)),
            "--BundleAdjustment.gpu_index", str(gpu_index),
        ]
        
        # Iteration parameters (only add if explicitly set, otherwise GLOMAP uses defaults)
        _add_param_if_set(cmd, "ba_iteration_num", "--ba_iteration_num", int)
        _add_param_if_set(cmd, "retriangulation_iteration_num", "--retriangulation_iteration_num", int)
        
        # Track Establishment parameters
        _add_param_if_set(cmd, "track_establishment_min_num_tracks_per_view", "--TrackEstablishment.min_num_tracks_per_view", int)
        _add_param_if_set(cmd, "track_establishment_min_num_view_per_track", "--TrackEstablishment.min_num_view_per_track", int)
        _add_param_if_set(cmd, "track_establishment_max_num_view_per_track", "--TrackEstablishment.max_num_view_per_track", int)
        _add_param_if_set(cmd, "track_establishment_max_num_tracks", "--TrackEstablishment.max_num_tracks", int)
        
        # Global Positioning parameters
        _add_param_if_set(cmd, "global_positioning_optimize_positions", "--GlobalPositioning.optimize_positions", bool)
        _add_param_if_set(cmd, "global_positioning_optimize_points", "--GlobalPositioning.optimize_points", bool)
        _add_param_if_set(cmd, "global_positioning_optimize_scales", "--GlobalPositioning.optimize_scales", bool)
        _add_param_if_set(cmd, "global_positioning_thres_loss_function", "--GlobalPositioning.thres_loss_function", float)
        _add_param_if_set(cmd, "global_positioning_max_num_iterations", "--GlobalPositioning.max_num_iterations", int)
        
        # Bundle Adjustment parameters
        _add_param_if_set(cmd, "bundle_adjustment_optimize_rotations", "--BundleAdjustment.optimize_rotations", bool)
        _add_param_if_set(cmd, "bundle_adjustment_optimize_translation", "--BundleAdjustment.optimize_translation", bool)
        _add_param_if_set(cmd, "bundle_adjustment_optimize_intrinsics", "--BundleAdjustment.optimize_intrinsics", bool)
        _add_param_if_set(cmd, "bundle_adjustment_optimize_principal_point", "--BundleAdjustment.optimize_principal_point", bool)
        _add_param_if_set(cmd, "bundle_adjustment_optimize_points", "--BundleAdjustment.optimize_points", bool)
        _add_param_if_set(cmd, "bundle_adjustment_thres_loss_function", "--BundleAdjustment.thres_loss_function", float)
        _add_param_if_set(cmd, "bundle_adjustment_max_num_iterations", "--BundleAdjustment.max_num_iterations", int)
        
        # Triangulation parameters
        _add_param_if_set(cmd, "triangulation_complete_max_reproj_error", "--Triangulation.complete_max_reproj_error", float)
        _add_param_if_set(cmd, "triangulation_merge_max_reproj_error", "--Triangulation.merge_max_reproj_error", float)
        _add_param_if_set(cmd, "triangulation_min_angle", "--Triangulation.min_angle", float)
        _add_param_if_set(cmd, "triangulation_min_num_matches", "--Triangulation.min_num_matches", int)
        
        # Inlier Thresholds parameters
        _add_param_if_set(cmd, "thresholds_max_angle_error", "--Thresholds.max_angle_error", float)
        _add_param_if_set(cmd, "thresholds_max_reprojection_error", "--Thresholds.max_reprojection_error", float)
        _add_param_if_set(cmd, "thresholds_min_triangulation_angle", "--Thresholds.min_triangulation_angle", float)
        _add_param_if_set(cmd, "thresholds_max_epipolar_error_E", "--Thresholds.max_epipolar_error_E", float)
        _add_param_if_set(cmd, "thresholds_max_epipolar_error_F", "--Thresholds.max_epipolar_error_F", float)
        _add_param_if_set(cmd, "thresholds_max_epipolar_error_H", "--Thresholds.max_epipolar_error_H", float)
        _add_param_if_set(cmd, "thresholds_min_inlier_num", "--Thresholds.min_inlier_num", float)
        _add_param_if_set(cmd, "thresholds_min_inlier_ratio", "--Thresholds.min_inlier_ratio", float)
        _add_param_if_set(cmd, "thresholds_max_rotation_error", "--Thresholds.max_rotation_error", float)
        
        await self._run_process(cmd, ctx, db, block_id, coarse_stage=coarse_stage)
    
    async def _run_glomap_mapper_resume(
        self,
        input_path: str,
        output_path: str,
        params: dict,
        gpu_index: int,
        ctx: TaskContext,
        db: AsyncSession,
        block_id: str,
        coarse_stage: str,
    ):
        """Run GLOMAP mapper_resume on existing COLMAP reconstruction."""
        def _b(v, default: int = 0) -> int:
            if v is None:
                return default
            if isinstance(v, bool):
                return 1 if v else 0
            return 1 if int(v) != 0 else 0

        def _add_param_if_set(cmd_list, param_key, glomap_flag, param_type=str, source_params=None):
            """Add parameter to command if it exists and is not None."""
            params_to_check = source_params if source_params is not None else params
            if param_key in params_to_check and params_to_check[param_key] is not None:
                if param_type == bool:
                    cmd_list.extend([glomap_flag, str(_b(params_to_check[param_key]))])
                elif param_type == int:
                    cmd_list.extend([glomap_flag, str(int(params_to_check[param_key]))])
                elif param_type == float:
                    cmd_list.extend([glomap_flag, str(float(params_to_check[param_key]))])
                else:
                    cmd_list.extend([glomap_flag, str(params_to_check[param_key])])

        cmd = [
            GLOMAP_PATH,
            "mapper_resume",
            "--input_path",
            input_path,
            "--output_path",
            output_path,
            "--output_format",
            "bin",
        ]

        # Filter out unsupported skip flags for mapper_resume mode
        # mapper_resume only supports: skip_global_positioning, skip_bundle_adjustment, skip_pruning
        # Other skip flags are forced to true and not registered as options
        unsupported_skip_flags = {
            "skip_preprocessing",
            "skip_view_graph_calibration",
            "skip_relative_pose_estimation",
            "skip_rotation_averaging",
            "skip_track_establishment",
            "skip_retriangulation",
        }
        # Create a filtered params dict excluding unsupported skip flags
        filtered_params = {k: v for k, v in params.items() if k not in unsupported_skip_flags} if params else {}

        # Optional GPU-related parameters (if supported by current GLOMAP build)
        if filtered_params:
            if "global_positioning_use_gpu" in filtered_params:
                cmd += [
                    "--GlobalPositioning.use_gpu",
                    str(_b(filtered_params.get("global_positioning_use_gpu", 1), 1)),
                ]
            if "bundle_adjustment_use_gpu" in filtered_params:
                cmd += [
                    "--BundleAdjustment.use_gpu",
                    str(_b(filtered_params.get("bundle_adjustment_use_gpu", 1), 1)),
                ]
        elif params:
            # Fallback to original params if filtered_params is empty but params exists
            if "global_positioning_use_gpu" in params:
                cmd += [
                    "--GlobalPositioning.use_gpu",
                    str(_b(params.get("global_positioning_use_gpu", 1), 1)),
                ]
            if "bundle_adjustment_use_gpu" in params:
                cmd += [
                    "--BundleAdjustment.use_gpu",
                    str(_b(params.get("bundle_adjustment_use_gpu", 1), 1)),
                ]
        
        # Process parameters using filtered_params to exclude unsupported skip flags
        params_to_use = filtered_params if filtered_params else params
        if params_to_use:
            
            # Iteration parameters
            _add_param_if_set(cmd, "ba_iteration_num", "--ba_iteration_num", int, params_to_use)
            _add_param_if_set(cmd, "retriangulation_iteration_num", "--retriangulation_iteration_num", int, params_to_use)

            # Skip-stage flags for mapper_resume mode
            # Note: mapper_resume mode only supports these skip flags (see AddGlobalMapperResumeOptions):
            # - skip_global_positioning
            # - skip_bundle_adjustment
            # - skip_pruning
            # Other skip flags (preprocessing, view_graph_calibration, etc.) are forced to true
            # and are not registered as options, so we should not pass them
            skip_flags_mapper_resume = [
                ("skip_global_positioning", "--skip_global_positioning"),
                ("skip_bundle_adjustment", "--skip_bundle_adjustment"),
                ("skip_pruning", "--skip_pruning"),
            ]
            for key, flag in skip_flags_mapper_resume:
                v = params_to_use.get(key)
                if v is True or (isinstance(v, int) and v != 0):
                    # GLOMAP requires boolean options to have explicit values: on/off, yes/no, 1/0, true/false
                    cmd.extend([flag, "1"])
                elif v is False or (isinstance(v, int) and v == 0):
                    # Explicitly set to false
                    cmd.extend([flag, "0"])
            
            # Global Positioning parameters
            _add_param_if_set(cmd, "global_positioning_optimize_positions", "--GlobalPositioning.optimize_positions", bool, params_to_use)
            _add_param_if_set(cmd, "global_positioning_optimize_points", "--GlobalPositioning.optimize_points", bool, params_to_use)
            _add_param_if_set(cmd, "global_positioning_optimize_scales", "--GlobalPositioning.optimize_scales", bool, params_to_use)
            _add_param_if_set(cmd, "global_positioning_thres_loss_function", "--GlobalPositioning.thres_loss_function", float, params_to_use)
            _add_param_if_set(cmd, "global_positioning_max_num_iterations", "--GlobalPositioning.max_num_iterations", int, params_to_use)
            
            # Bundle Adjustment parameters
            _add_param_if_set(cmd, "bundle_adjustment_optimize_rotations", "--BundleAdjustment.optimize_rotations", bool, params_to_use)
            _add_param_if_set(cmd, "bundle_adjustment_optimize_translation", "--BundleAdjustment.optimize_translation", bool, params_to_use)
            _add_param_if_set(cmd, "bundle_adjustment_optimize_intrinsics", "--BundleAdjustment.optimize_intrinsics", bool, params_to_use)
            _add_param_if_set(cmd, "bundle_adjustment_optimize_principal_point", "--BundleAdjustment.optimize_principal_point", bool, params_to_use)
            _add_param_if_set(cmd, "bundle_adjustment_optimize_points", "--BundleAdjustment.optimize_points", bool, params_to_use)
            _add_param_if_set(cmd, "bundle_adjustment_thres_loss_function", "--BundleAdjustment.thres_loss_function", float, params_to_use)
            _add_param_if_set(cmd, "bundle_adjustment_max_num_iterations", "--BundleAdjustment.max_num_iterations", int, params_to_use)
            
            # Triangulation parameters
            _add_param_if_set(cmd, "triangulation_complete_max_reproj_error", "--Triangulation.complete_max_reproj_error", float, params_to_use)
            _add_param_if_set(cmd, "triangulation_merge_max_reproj_error", "--Triangulation.merge_max_reproj_error", float, params_to_use)
            _add_param_if_set(cmd, "triangulation_min_angle", "--Triangulation.min_angle", float, params_to_use)
            _add_param_if_set(cmd, "triangulation_min_num_matches", "--Triangulation.min_num_matches", int, params_to_use)
            
            # Inlier Thresholds parameters
            _add_param_if_set(cmd, "thresholds_max_angle_error", "--Thresholds.max_angle_error", float, params_to_use)
            _add_param_if_set(cmd, "thresholds_max_reprojection_error", "--Thresholds.max_reprojection_error", float, params_to_use)
            _add_param_if_set(cmd, "thresholds_min_triangulation_angle", "--Thresholds.min_triangulation_angle", float, params_to_use)
            _add_param_if_set(cmd, "thresholds_max_epipolar_error_E", "--Thresholds.max_epipolar_error_E", float, params_to_use)
            _add_param_if_set(cmd, "thresholds_max_epipolar_error_F", "--Thresholds.max_epipolar_error_F", float, params_to_use)
            _add_param_if_set(cmd, "thresholds_max_epipolar_error_H", "--Thresholds.max_epipolar_error_H", float, params_to_use)
            _add_param_if_set(cmd, "thresholds_min_inlier_num", "--Thresholds.min_inlier_num", float, params_to_use)
            _add_param_if_set(cmd, "thresholds_min_inlier_ratio", "--Thresholds.min_inlier_ratio", float, params_to_use)
            _add_param_if_set(cmd, "thresholds_max_rotation_error", "--Thresholds.max_rotation_error", float, params_to_use)

        ctx.write_log_line(f"Executing command: {' '.join(cmd)}")
        await self._run_process(cmd, ctx, db, block_id, coarse_stage=coarse_stage)

    async def _run_glomap_resume_pipeline(
        self,
        block: Block,
        gpu_index: int,
        ctx: TaskContext,
        db: AsyncSession,
    ):
        """Pipeline for pure GLOMAP mapper_resume optimization."""
        from sqlalchemy import select as _select  # local import to avoid circular hints

        # Write initial log message
        ctx.write_log_line("=" * 80)
        ctx.write_log_line(f"Starting GLOMAP mapper_resume optimization for block {block.id}")
        ctx.write_log_line(f"Input COLMAP path: {getattr(block, 'input_colmap_path', None)}")
        ctx.write_log_line(f"Output path: {block.output_path}")
        ctx.write_log_line("=" * 80)

        # Basic validation
        input_colmap_path = getattr(block, "input_colmap_path", None)
        if not input_colmap_path or not os.path.isdir(input_colmap_path):
            error_msg = f"Invalid COLMAP input path for mapper_resume: {input_colmap_path!r}"
            block.status = BlockStatus.FAILED
            block.error_message = error_msg
            block.current_stage = "failed"
            block.progress = 0.0
            block.completed_at = datetime.utcnow()
            await db.commit()
            ctx.write_log_line(f"ERROR: {error_msg}")
            return

        # Check that essential COLMAP files exist in input path
        ctx.write_log_line(f"Validating COLMAP input files in: {input_colmap_path}")
        required_files = ("cameras", "images", "points3D")
        found_files = []
        for stem in required_files:
            bin_path = os.path.join(input_colmap_path, f"{stem}.bin")
            txt_path = os.path.join(input_colmap_path, f"{stem}.txt")
            if os.path.exists(bin_path):
                found_files.append(f"{stem}.bin")
            elif os.path.exists(txt_path):
                found_files.append(f"{stem}.txt")
        
        if not found_files:
            error_msg = (
                f"mapper_resume input_path does not contain COLMAP cameras/images/points3D files: {input_colmap_path}"
            )
            block.status = BlockStatus.FAILED
            block.error_message = error_msg
            block.current_stage = "failed"
            block.progress = 0.0
            block.completed_at = datetime.utcnow()
            await db.commit()
            ctx.write_log_line(f"ERROR: {error_msg}")
            return
        
        ctx.write_log_line(f"Found COLMAP files: {', '.join(found_files)}")

        # Prepare output sparse directory for optimized result
        output_root = block.output_path or f"/root/work/aerotri-web/data/outputs/{block.id}"
        os.makedirs(output_root, exist_ok=True)
        sparse_path = os.path.join(output_root, "sparse")
        os.makedirs(sparse_path, exist_ok=True)

        ctx.write_log_line(f"Output directory prepared: {sparse_path}")

        # Persist the resolved paths on block for later inspection/statistics
        block.output_path = output_root
        block.output_colmap_path = sparse_path
        await db.commit()

        # Single-stage timing
        stage_times = {}
        stage_start = datetime.now()
        ctx.current_stage = "mapping_resume"
        block.current_stage = "mapping_resume"
        block.current_detail = None
        block.progress = 0.0
        await db.commit()

        # Merge mapper/glomap params (glomap_params has higher priority)
        params = {}
        if block.mapper_params:
            params.update(block.mapper_params)
        if getattr(block, "glomap_params", None):
            params.update(block.glomap_params or {})
        
        ctx.write_log_line(f"GLOMAP parameters: {params}")
        ctx.write_log_line("Starting GLOMAP mapper_resume command...")

        await self._run_glomap_mapper_resume(
            input_colmap_path,
            sparse_path,
            params,
            gpu_index,
            ctx,
            db,
            block.id,
            coarse_stage="mapping_resume",
        )
        if ctx.cancelled:
            return

        stage_times["mapping_resume"] = (datetime.now() - stage_start).total_seconds()

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
                "glomap_mode": getattr(block, "glomap_mode", None).value
                if getattr(block, "glomap_mode", None)
                else None,
                "mapper_params": block.mapper_params,
                "glomap_params": getattr(block, "glomap_params", None),
            },
        }
        await db.commit()

    def _create_partition_database(
        self,
        global_database_path: str,
        partition_database_path: str,
        partition_image_names: List[str],
        ctx: TaskContext,
    ):
        """Create a partition database containing only images in the partition and their matches.
        
        Args:
            global_database_path: Path to global database.db
            partition_database_path: Path to output partition database.db
            partition_image_names: List of image filenames in this partition
            ctx: Task context for logging
        """
        import sqlite3
        
        ctx.write_log_line(f"Creating partition database with {len(partition_image_names)} images...")
        
        # Helper function to batch process IDs to avoid SQLite's "too many SQL variables" limit
        # SQLite default limit is 999, we use 900 to be safe
        MAX_SQL_VARIABLES = 900
        
        def batch_process_ids(id_list, process_func):
            """Process a list of IDs in batches to avoid SQL variable limit.
            
            Args:
                id_list: List of IDs to process
                process_func: Function that takes a batch of IDs and processes them
            """
            id_list = list(id_list)
            for i in range(0, len(id_list), MAX_SQL_VARIABLES):
                batch = id_list[i:i + MAX_SQL_VARIABLES]
                process_func(batch)
        
        # Create a set for fast lookup
        partition_image_set = set(partition_image_names)
        
        # Connect to global database
        global_conn = sqlite3.connect(global_database_path)
        global_conn.row_factory = sqlite3.Row
        
        # Create partition database by copying schema only
        if os.path.exists(partition_database_path):
            os.remove(partition_database_path)
        partition_conn = sqlite3.connect(partition_database_path)
        partition_conn.row_factory = sqlite3.Row
        
        # Copy schema from global database (create tables but no data)
        # Get schema SQL from global database, excluding SQLite system tables
        schema_sql = ""
        for row in global_conn.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND sql IS NOT NULL"):
            table_name = row['name']
            # Skip SQLite system tables (sqlite_sequence, sqlite_stat1, etc.)
            if not table_name.startswith('sqlite_'):
                schema_sql += row['sql'] + ";\n"
        
        # Execute schema in partition database
        if schema_sql:
            partition_conn.executescript(schema_sql)
        
        # Copy indexes (excluding system indexes)
        for row in global_conn.execute("SELECT name, sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL"):
            index_name = row['name']
            # Skip SQLite system indexes
            if not index_name.startswith('sqlite_'):
                try:
                    partition_conn.execute(row['sql'])
                except Exception:
                    pass  # Some indexes may fail if tables are empty
        
        # Get image IDs for partition images
        partition_image_ids = set()
        image_id_to_name = {}
        
        # Convert partition image names to basenames for matching
        # Database may store full/relative paths, but partition names are just filenames
        partition_image_basenames = {os.path.basename(name) for name in partition_image_set}
        
        for row in global_conn.execute("SELECT image_id, name FROM images"):
            # Extract basename from database path (may contain relative path)
            db_basename = os.path.basename(row['name'])
            if db_basename in partition_image_basenames:
                partition_image_ids.add(row['image_id'])
                image_id_to_name[row['image_id']] = row['name']
        
        ctx.write_log_line(f"Found {len(partition_image_ids)} matching images in database")
        
        if not partition_image_ids:
            raise RuntimeError("No matching images found in global database")
        
        # Copy only cameras used by partition images (batch process to avoid SQL variable limit)
        used_camera_ids = set()
        def process_camera_batch(batch):
            placeholders = ','.join('?' * len(batch))
            for row in global_conn.execute(f"SELECT DISTINCT camera_id FROM images WHERE image_id IN ({placeholders})", batch):
                used_camera_ids.add(row['camera_id'])
        
        batch_process_ids(partition_image_ids, process_camera_batch)
        
        if used_camera_ids:
            # Check which columns exist in cameras table
            camera_columns = []
            for row in global_conn.execute("PRAGMA table_info(cameras)"):
                camera_columns.append(row['name'])
            
            # Build SELECT and INSERT statements dynamically
            base_camera_columns = ['camera_id', 'model', 'width', 'height', 'params']
            optional_camera_columns = ['prior_focal_length']
            
            select_camera_columns = base_camera_columns.copy()
            insert_camera_columns = base_camera_columns.copy()
            
            for col in optional_camera_columns:
                if col in camera_columns:
                    select_camera_columns.append(col)
                    insert_camera_columns.append(col)
            
            insert_camera_placeholders = ', '.join(['?'] * len(insert_camera_columns))
            insert_camera_sql = f"INSERT INTO cameras ({', '.join(insert_camera_columns)}) VALUES ({insert_camera_placeholders})"
            
            # Copy cameras (batch process to avoid SQL variable limit, though usually not needed for cameras)
            def process_camera_insert_batch(batch):
                camera_placeholders = ','.join('?' * len(batch))
                select_camera_sql = f"SELECT {', '.join(select_camera_columns)} FROM cameras WHERE camera_id IN ({camera_placeholders})"
                for row in global_conn.execute(select_camera_sql, batch):
                    values = [row[col] for col in insert_camera_columns]
                    partition_conn.execute(insert_camera_sql, values)
            
            batch_process_ids(used_camera_ids, process_camera_insert_batch)
        
        # Check which columns exist in images table
        images_columns = []
        for row in global_conn.execute("PRAGMA table_info(images)"):
            images_columns.append(row['name'])
        
        # Build SELECT and INSERT statements dynamically based on available columns
        base_image_columns = ['image_id', 'name', 'camera_id']
        optional_image_columns = ['prior_qvec', 'prior_tvec']
        
        select_image_columns = base_image_columns.copy()
        insert_image_columns = base_image_columns.copy()
        insert_image_values = []
        
        for col in optional_image_columns:
            if col in images_columns:
                select_image_columns.append(col)
                insert_image_columns.append(col)
        
        insert_image_placeholders = ', '.join(['?'] * len(insert_image_columns))
        insert_image_sql = f"INSERT INTO images ({', '.join(insert_image_columns)}) VALUES ({insert_image_placeholders})"
        
        # Copy only partition images (batch process to avoid SQL variable limit)
        def process_image_batch(batch):
            placeholders = ','.join('?' * len(batch))
            select_image_sql = f"SELECT {', '.join(select_image_columns)} FROM images WHERE image_id IN ({placeholders})"
            for row in global_conn.execute(select_image_sql, batch):
                values = [row[col] for col in insert_image_columns]
                partition_conn.execute(insert_image_sql, values)
        
        batch_process_ids(partition_image_ids, process_image_batch)
        
        # Copy keypoints for partition images (batch process to avoid SQL variable limit)
        def process_keypoints_batch(batch):
            placeholders = ','.join('?' * len(batch))
            for row in global_conn.execute(f"SELECT image_id, rows, cols, data FROM keypoints WHERE image_id IN ({placeholders})", batch):
                partition_conn.execute(
                    "INSERT INTO keypoints (image_id, rows, cols, data) VALUES (?, ?, ?, ?)",
                    (row['image_id'], row['rows'], row['cols'], row['data'])
                )
        
        batch_process_ids(partition_image_ids, process_keypoints_batch)
        
        # Copy descriptors for partition images (batch process to avoid SQL variable limit)
        def process_descriptors_batch(batch):
            placeholders = ','.join('?' * len(batch))
            for row in global_conn.execute(f"SELECT image_id, rows, cols, data FROM descriptors WHERE image_id IN ({placeholders})", batch):
                partition_conn.execute(
                    "INSERT INTO descriptors (image_id, rows, cols, data) VALUES (?, ?, ?, ?)",
                    (row['image_id'], row['rows'], row['cols'], row['data'])
                )
        
        batch_process_ids(partition_image_ids, process_descriptors_batch)
        
        # Get all pair_ids that involve partition images
        # COLMAP pair_id = image_id1 * 2147483647 + image_id2
        valid_pair_ids = set()
        for image_id1 in partition_image_ids:
            for image_id2 in partition_image_ids:
                if image_id1 < image_id2:
                    pair_id = image_id1 * 2147483647 + image_id2
                    valid_pair_ids.add(pair_id)
        
        # Copy matches only for partition image pairs (batch process to avoid SQL variable limit)
        if valid_pair_ids:
            def process_matches_batch(batch):
                pair_placeholders = ','.join('?' * len(batch))
                for row in global_conn.execute(f"SELECT pair_id, rows, cols, data FROM matches WHERE pair_id IN ({pair_placeholders})", batch):
                    partition_conn.execute(
                        "INSERT INTO matches (pair_id, rows, cols, data) VALUES (?, ?, ?, ?)",
                        (row['pair_id'], row['rows'], row['cols'], row['data'])
                    )
            
            batch_process_ids(valid_pair_ids, process_matches_batch)
            
            def process_two_view_geometries_batch(batch):
                pair_placeholders = ','.join('?' * len(batch))
                for row in global_conn.execute(f"SELECT pair_id, rows, cols, data, config, F, E, H FROM two_view_geometries WHERE pair_id IN ({pair_placeholders})", batch):
                    partition_conn.execute(
                        "INSERT INTO two_view_geometries (pair_id, rows, cols, data, config, F, E, H) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (row['pair_id'], row['rows'], row['cols'], row['data'], row['config'], row['F'], row['E'], row['H'])
                    )
            
            batch_process_ids(valid_pair_ids, process_two_view_geometries_batch)
        
        # Copy feature_name if exists
        try:
            feature_name_row = global_conn.execute("SELECT feature_name FROM feature_name").fetchone()
            if feature_name_row:
                partition_conn.execute("INSERT INTO feature_name (feature_name) VALUES (?)", (feature_name_row['feature_name'],))
        except Exception:
            pass  # feature_name table may not exist
        
        partition_conn.commit()
        
        # Get statistics
        num_images = partition_conn.execute("SELECT COUNT(*) FROM images").fetchone()[0]
        num_keypoints = partition_conn.execute("SELECT COUNT(*) FROM keypoints").fetchone()[0]
        num_matches = partition_conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0]
        
        ctx.write_log_line(f"Partition database created: {num_images} images, {num_keypoints} keypoints, {num_matches} matches")
        
        global_conn.close()
        partition_conn.close()
    
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
        partition_image_names: Optional[List[str]] = None,
    ):
        """Run InstantSfM mapper.
        
        Args:
            database_path: Path to database.db (global or partition)
            image_path: Path to image directory
            output_path: Output directory (data_path for InstantSfM)
            params: Mapper parameters
            gpu_index: GPU index
            ctx: Task context
            db: Database session
            block_id: Block ID
            coarse_stage: Coarse stage name
            partition_image_names: Optional list of image names for partition mode
        """
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
        
        # For partition mode, create a partition database
        expected_db_path = os.path.join(data_path, "database.db")
        if partition_image_names:
            # Create partition database
            self._create_partition_database(
                database_path,
                expected_db_path,
                partition_image_names,
                ctx,
            )
        else:
            # Use global database (link or copy)
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
            f"export LD_LIBRARY_PATH={CERES_LIB_PATH}:$LD_LIBRARY_PATH",
            f"export CUDA_VISIBLE_DEVICES={effective_gpu_index}",
            f"{INSTANTSFM_PATH} --data_path {data_path} --manual_config_name {manual_config}"
        ]
        
        # Add optional parameters
        if params.get("export_txt", True):
            base_cmd_parts[-1] += " --export_txt"
        
        if params.get("disable_depths", False):
            base_cmd_parts[-1] += " --disable_depths"
        
        # Add visualization support
        visualizer_proxy = None
        if params.get("enable_visualization", False):
            base_cmd_parts[-1] += " --enable_gui"
            # Set VISER_PORT environment variable for port detection
            # Note: viser uses random port by default, we'll try to capture it from logs
            viser_port = params.get("visualization_port")
            if viser_port:
                base_cmd_parts.insert(-1, f"export VISER_PORT={viser_port}")
            
            # Start visualization proxy (will be started after process starts)
            ctx.write_log_line("Visualization enabled - will start proxy after viser server is ready")
        
        base_cmd = " && ".join(base_cmd_parts)
        cmd = ["bash", "-c", base_cmd]
        
        ctx.write_log_line(f"Running InstantSfM with data_path={data_path}, gpu_index={effective_gpu_index} (from params: {params.get('gpu_index', 'not set')}, fallback: {gpu_index})")
        ctx.write_log_line(f"Command: {' '.join(cmd)}")
        
        # Start visualization proxy if enabled
        # Note: Proxy will wait for viser server to start (viser starts after InstantSfM process begins)
        if params.get("enable_visualization", False):
            viser_port = params.get("visualization_port")
            visualizer_proxy = InstantSfMVisualizerProxy(block_id, viser_port=viser_port)
            register_visualizer_proxy(block_id, visualizer_proxy)
            
            # Start proxy in background (it will wait for viser server)
            await visualizer_proxy.start()
            ctx.write_log_line("Visualization proxy started - waiting for viser server to be ready")
        
        try:
            # Run the process
            await self._run_process(cmd, ctx, db, block_id, coarse_stage=coarse_stage)
        finally:
            # Clean up visualization proxy
            if visualizer_proxy:
                await visualizer_proxy.stop()
                unregister_visualizer_proxy(block_id)
    
    async def _run_process(self, cmd: List[str], ctx: TaskContext, db: AsyncSession, block_id: str, coarse_stage: str):
        """Run a subprocess and capture output.
        
        Args:
            cmd: Command and arguments
            ctx: Task context
        """
        # Prepare environment variables with library paths
        env = os.environ.copy()
        # Add Ceres library path (contains all required libraries including absl)
        current_ld_path = env.get("LD_LIBRARY_PATH", "")
        if CERES_LIB_PATH not in current_ld_path:
            env["LD_LIBRARY_PATH"] = f"{CERES_LIB_PATH}:{current_ld_path}" if current_ld_path else CERES_LIB_PATH
        
        # Increase limit to handle long progress lines (GLOMAP/COLMAP uses \r for progress)
        # Default limit is 64KB, we set it to 10MB to handle very long progress outputs
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            limit=10 * 1024 * 1024,  # 10MB buffer limit
            env=env,  # Pass environment with library paths
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

        # 处理非 0 退出码。
        # 注意：COLMAP / GLOMAP / InstantSfM 在处理完成后，退出阶段存在已知的 SIGSEGV/Abort 问题（returncode 为负数，通常是 -11 或 -6）。
        # 如果确认输出结果是有效的（例如 mapper 阶段已经生成 sparse 结果），则将其视为成功而不是失败，
        # 避免前端把已完成的任务标记为"失败"。
        if process.returncode != 0 and not ctx.cancelled:
            # 记录退出信息
            if process.returncode < 0:
                # Signal received (e.g., SIGSEGV = -11, SIGABRT = -6)
                ctx.write_log_line(f"Warning: Process terminated with signal {abs(process.returncode)}")
            else:
                # Non-zero exit code
                ctx.write_log_line(f"Warning: Process exited with code {process.returncode}")

            # 对 GLOMAP / COLMAP / InstantSfM mapper / mapper_resume 阶段做特殊处理：
            # 如果已经成功导出了 sparse 结果（空三完成），则视为成功。
            if coarse_stage in ("mapping", "mapping_resume"):
                try:
                    async with AsyncSessionLocal() as s:
                        result = await s.execute(select(Block).where(Block.id == block_id))
                        block = result.scalar_one_or_none()

                    if block and block.output_path:
                        # 检查 COLMAP/GLOMAP 标准输出路径：sparse/
                        sparse_path = os.path.join(block.output_path, "sparse")
                        
                        # 检查 InstantSfM 标准输出路径：sparse/0/
                        instantsfm_sparse_path = os.path.join(block.output_path, "sparse", "0")
                        
                        # 验证函数：检查目录是否存在且包含必要的重建文件
                        def validate_sparse_output(sparse_dir):
                            """验证 sparse 输出目录是否包含有效的重建结果"""
                            if not os.path.isdir(sparse_dir):
                                return False
                            
                            # 检查是否包含 COLMAP 重建文件（.bin 或 .txt 格式）
                            required_files = ["cameras", "images", "points3D"]
                            found_files = []
                            for stem in required_files:
                                bin_path = os.path.join(sparse_dir, f"{stem}.bin")
                                txt_path = os.path.join(sparse_dir, f"{stem}.txt")
                                if os.path.exists(bin_path) or os.path.exists(txt_path):
                                    found_files.append(stem)
                            
                            # 至少需要找到 cameras 和 images 文件（points3D 可能为空）
                            return len(found_files) >= 2
                        
                        # 检查标准 sparse 路径（COLMAP/GLOMAP）
                        if validate_sparse_output(sparse_path):
                            ctx.write_log_line(
                                f"Detected valid sparse output at {sparse_path} after non-zero exit; "
                                "treating mapper stage as SUCCESS despite non-zero exit code."
                            )
                            return
                        
                        # 检查 InstantSfM sparse/0/ 路径
                        if validate_sparse_output(instantsfm_sparse_path):
                            ctx.write_log_line(
                                f"Detected valid InstantSfM sparse output at {instantsfm_sparse_path} after non-zero exit; "
                                "treating mapper stage as SUCCESS despite non-zero exit code."
                            )
                            return
                        
                        # 如果 sparse 目录存在但验证失败，记录详细信息
                        if os.path.isdir(sparse_path):
                            ctx.write_log_line(
                                f"Warning: sparse directory exists at {sparse_path} but validation failed. "
                                "Contents may be incomplete."
                            )
                except Exception as e:
                    # 验证逻辑失败时不要中断主流程，只记录告警并继续按错误处理
                    ctx.write_log_line(
                        f"Warning: Failed to validate sparse output after non-zero exit: {e}"
                    )

            # 走到这里说明需要把任务视为失败
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
            data["pipeline"] = "sfm"
        
        if block_id in self.ws_connections:
            for ws in self.ws_connections[block_id]:
                try:
                    await ws.send_json(data)
                except Exception:
                    pass
    
    async def stop_task(self, block_id: str, db: AsyncSession):
        """Stop a running task.
        
        Args:
            block_id: Block ID
            db: Database session
        """
        if block_id not in self.running_tasks:
            return
        
        ctx = self.running_tasks[block_id]
        ctx.cancelled = True
        
        if ctx.process:
            ctx.process.terminate()
            try:
                await asyncio.wait_for(ctx.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                ctx.process.kill()
        
        # Update block status using a fresh session (avoid request-session lifecycle issues)
        async with AsyncSessionLocal() as s:
            result = await s.execute(select(Block).where(Block.id == block_id))
            block = result.scalar_one_or_none()
            if block:
                block.status = BlockStatus.CANCELLED
                block.current_stage = "cancelled"
                block.current_detail = None
                block.completed_at = datetime.utcnow()
                await s.commit()
    
    def get_log_tail(self, block_id: str, lines: int = 20) -> Optional[List[str]]:
        """Get last N lines of log.
        
        Args:
            block_id: Block ID
            lines: Number of lines
            
        Returns:
            List of log lines or None
        """
        # If running, use in-memory buffer
        if block_id in self.running_tasks:
            ctx = self.running_tasks[block_id]
            return list(ctx.log_buffer)[-lines:]

        # If completed, try read persisted log file
        log_path = os.path.join("/root/work/aerotri-web/data/outputs", block_id, "run.log")
        if not os.path.exists(log_path):
            return None
        try:
            dq: deque = deque(maxlen=lines)
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                for ln in f:
                    dq.append(ln.rstrip("\n"))
            return list(dq)
        except Exception:
            return None
    
    def get_stage_times(self, block_id: str) -> Optional[Dict[str, float]]:
        """Get stage timing information.
        
        Args:
            block_id: Block ID
            
        Returns:
            Dict of stage times or None
        """
        if block_id not in self.running_tasks:
            return None
        
        ctx = self.running_tasks[block_id]
        return ctx.log_parser.get_stage_times()
    
    def register_websocket(self, block_id: str, ws):
        """Register a WebSocket connection for progress updates.
        
        Args:
            block_id: Block ID
            ws: WebSocket connection
        """
        if block_id not in self.ws_connections:
            self.ws_connections[block_id] = []
        self.ws_connections[block_id].append(ws)
    
    def unregister_websocket(self, block_id: str, ws):
        """Unregister a WebSocket connection.
        
        Args:
            block_id: Block ID
            ws: WebSocket connection
        """
        if block_id in self.ws_connections:
            self.ws_connections[block_id] = [
                w for w in self.ws_connections[block_id] if w != ws
            ]
    
    async def _run_partitioned_sfm(
        self,
        block_id: str,
        gpu_index: int,
        ctx: TaskContext,
    ):
        """Run partitioned SfM pipeline: global feature+match -> partition mappers -> merge.
        
        Args:
            block_id: Block ID
            gpu_index: GPU index
            ctx: Task context
        """
        from .partition_service import PartitionService
        from .sfm_merge_service import SFMMergeService
        
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Block).where(Block.id == block_id))
                block = result.scalar_one_or_none()
                if not block:
                    raise RuntimeError(f"Block not found: {block_id}")
                
                if not block.partition_enabled:
                    raise RuntimeError("Block is not in partitioned mode")
                
                output_path = block.output_path or ""
                database_path = os.path.join(output_path, "database.db")
                image_dir = block.working_image_path or block.image_path
                
                # Get parameters
                feature_params = block.feature_params or {}
                matching_params = dict(block.matching_params or {})
                matching_params.setdefault("method", block.matching_method.value)
                mapper_params = block.mapper_params or {}
                
                stage_times = {}
                
                # Stage 1: Global feature extraction + matching
                # Immediately update stage to "feature_extraction" so frontend shows correct status
                block.current_stage = "feature_extraction"
                block.progress = 0.0
                await db.commit()
                
                stage_start = datetime.now()
                global_log_path = os.path.join(output_path, "run_global.log")
                await self._run_global_feature_and_matching(
                    block,
                    database_path,
                    image_dir,
                    feature_params,
                    matching_params,
                    gpu_index,
                    ctx,
                    db,
                    log_file_path=global_log_path,
                )
                if ctx.cancelled:
                    return
                stage_times["global_feature_matching"] = (datetime.now() - stage_start).total_seconds()
                
                # Stage 2: Partition mappers
                partitions = await PartitionService.get_partitions(block_id, db)
                if not partitions:
                    raise RuntimeError("No partitions found for this block")
                
                block.current_stage = "partition_mapping"
                block.progress = 20.0
                await db.commit()
                
                partition_times = {}
                for i, partition in enumerate(sorted(partitions, key=lambda p: p.index)):
                    if ctx.cancelled:
                        return
                    
                    partition_start = datetime.now()
                    await self._run_partition_mapper(
                        block,
                        partition,
                        database_path,
                        image_dir,
                        mapper_params,
                        gpu_index,
                        ctx,
                        db,
                    )
                    partition_times[f"partition_{partition.index}"] = (datetime.now() - partition_start).total_seconds()
                    
                    # Update overall progress
                    partition_progress = 20.0 + (i + 1) / len(partitions) * 60.0
                    block.progress = min(80.0, partition_progress)
                    await db.commit()
                
                stage_times["partition_mapping"] = sum(partition_times.values())
                stage_times.update(partition_times)
                
                # Mark partitions as completed (but not merged yet)
                # User can now view partition results before merging
                block.status = BlockStatus.COMPLETED
                block.completed_at = datetime.utcnow()
                block.current_stage = "partitions_completed"
                block.current_detail = None
                block.progress = 80.0  # 80% complete (partitions done, merge pending)
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
                        "partition_count": len(partitions),
                        "sfm_pipeline_mode": block.sfm_pipeline_mode,
                        "merge_strategy": block.merge_strategy or "sim3_keep_one",
                    },
                }
                await db.commit()
                
                ctx.write_log_line(f"[Partitions] All {len(partitions)} partitions completed. Ready for merge.")
        except Exception as e:
            try:
                async with AsyncSessionLocal() as db:
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
            if block_id in self.running_tasks:
                ctx.close_log_file()
                del self.running_tasks[block_id]
    
    async def _run_merge_only(
        self,
        block_id: str,
        ctx: TaskContext,
    ):
        """Run merge only for completed partitions.
        
        Args:
            block_id: Block ID
            ctx: Task context
        """
        from .partition_service import PartitionService
        from .sfm_merge_service import SFMMergeService
        
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Block).where(Block.id == block_id))
                block = result.scalar_one_or_none()
                if not block:
                    raise RuntimeError(f"Block not found: {block_id}")
                
                if not block.partition_enabled:
                    raise RuntimeError("Block is not in partitioned mode")
                
                if block.current_stage != "partitions_completed":
                    raise RuntimeError(f"Block is not ready for merge. Current stage: {block.current_stage}")
                
                output_path = block.output_path or ""
                merge_strategy = block.merge_strategy or "sim3_keep_one"
                
                # Get partitions and verify they are all completed
                partitions = await PartitionService.get_partitions(block_id, db)
                if not partitions:
                    raise RuntimeError("No partitions found for this block")
                
                # Verify all partitions are completed
                for partition in partitions:
                    if partition.status != "COMPLETED":
                        raise RuntimeError(f"Partition {partition.index} is not completed (status: {partition.status})")
                
                # Stage: Merge partitions
                block.current_stage = "merging"
                block.progress = 80.0
                block.status = BlockStatus.RUNNING
                await db.commit()
                
                merge_start = datetime.now()
                merged_sparse_dir = os.path.join(output_path, "merged", "sparse", "0")
                os.makedirs(merged_sparse_dir, exist_ok=True)
                
                await SFMMergeService.merge_partitions(
                    block,
                    partitions,
                    merged_sparse_dir,
                    merge_strategy,
                    ctx,
                    db,
                )
                if ctx.cancelled:
                    return
                merge_time = (datetime.now() - merge_start).total_seconds()
                
                # Create symlink from sparse/0 to merged/sparse/0 for compatibility
                sparse_link = os.path.join(output_path, "sparse", "0")
                sparse_link_dir = os.path.dirname(sparse_link)
                os.makedirs(sparse_link_dir, exist_ok=True)
                if os.path.exists(sparse_link) or os.path.islink(sparse_link):
                    if os.path.islink(sparse_link):
                        os.unlink(sparse_link)
                    elif os.path.isdir(sparse_link):
                        # If it's a real directory, we can't symlink over it
                        # In this case, we'll just leave it (shouldn't happen in partitioned mode)
                        pass
                try:
                    os.symlink(os.path.relpath(merged_sparse_dir, sparse_link_dir), sparse_link)
                except Exception:
                    # If symlink fails, that's okay - result_reader will check merged/sparse/0 first
                    pass
                
                # Update statistics with merge time
                existing_stats = block.statistics or {}
                existing_stage_times = existing_stats.get("stage_times", {})
                existing_stage_times["merge"] = merge_time
                existing_stats["stage_times"] = existing_stage_times
                existing_stats["total_time"] = sum(existing_stage_times.values())
                
                # Mark as fully completed
                block.status = BlockStatus.COMPLETED
                block.completed_at = datetime.utcnow()
                block.current_stage = "completed"
                block.current_detail = None
                block.progress = 100.0
                block.statistics = existing_stats
                await db.commit()
                
                ctx.write_log_line(f"[Merge] Merge completed successfully in {merge_time:.2f} seconds")
        except Exception as e:
            try:
                async with AsyncSessionLocal() as db:
                    result = await db.execute(select(Block).where(Block.id == block_id))
                    block = result.scalar_one_or_none()
                    if block:
                        block.status = BlockStatus.FAILED
                        block.error_message = str(e)
                        block.completed_at = datetime.utcnow()
                        block.current_stage = "merge_failed"
                        await db.commit()
            except Exception:
                pass
            raise
        finally:
            # Cleanup task context
            if block_id in self.running_tasks:
                ctx.close_log_file()
                del self.running_tasks[block_id]
    
    async def _run_partition_mapper(
        self,
        block: Block,
        partition,
        database_path: str,
        image_dir: str,
        mapper_params: dict,
        gpu_index: int,
        ctx: TaskContext,
        db: AsyncSession,
    ):
        """Run mapper for a single partition.
        
        Args:
            block: Block instance
            partition: BlockPartition instance
            database_path: Path to shared database.db
            image_dir: Image directory
            mapper_params: Mapper parameters
            gpu_index: GPU index
            ctx: Task context
            db: Database session
        """
        from ..models import BlockPartition
        from .partition_service import PartitionService
        
        # Update partition status
        partition.status = "RUNNING"
        partition.progress = 0.0
        await db.commit()
        
        # Get partition image names
        partition_images = await PartitionService.get_partition_image_names(block, partition)
        if not partition_images:
            raise RuntimeError(f"No images found for partition {partition.index}")
        
        # Create partition output directory
        output_path = block.output_path or ""
        partition_output = os.path.join(output_path, "partitions", f"partition_{partition.index}", "sparse")
        os.makedirs(partition_output, exist_ok=True)
        
        # Create partition log file
        partition_log = os.path.join(output_path, "partitions", f"partition_{partition.index}", f"run_partition_{partition.index}.log")
        os.makedirs(os.path.dirname(partition_log), exist_ok=True)
        
        # Create a temporary context for this partition (or reuse main context)
        # For simplicity, we'll write to both main log and partition log
        partition_log_fp = open(partition_log, "a", buffering=1, encoding="utf-8", errors="replace")
        
        try:
            # Write partition info
            ctx.write_log_line(f"[Partition {partition.index}] Starting mapper for {len(partition_images)} images")
            partition_log_fp.write(f"[Partition {partition.index}] Starting mapper for {len(partition_images)} images\n")
            
            # For COLMAP mapper, we need to filter images
            # COLMAP mapper doesn't directly support --image_names, so we'll use a workaround:
            # Create a temporary image list file or use image_path with filtered images
            # For now, we'll pass all images and let COLMAP handle it (it will only process registered images)
            # In practice, COLMAP mapper will only process images that are in the database
            
            if block.algorithm == AlgorithmType.GLOMAP:
                await self._run_glomap_mapper(
                    database_path,
                    image_dir,
                    partition_output,
                    mapper_params,
                    gpu_index,
                    ctx,
                    db,
                    block.id,
                    coarse_stage="partition_mapping",
                )
            elif block.algorithm == AlgorithmType.INSTANTSFM:
                # For InstantSfM, we need to set up the data_path structure
                # Create partition database to reduce memory usage
                instantsfm_data_path = os.path.join(output_path, "partitions", f"partition_{partition.index}")
                await self._run_instantsfm_mapper(
                    database_path,
                    image_dir,
                    instantsfm_data_path,
                    mapper_params,
                    gpu_index,
                    ctx,
                    db,
                    block.id,
                    coarse_stage="partition_mapping",
                    partition_image_names=partition_images,
                )
            else:
                await self._run_colmap_mapper(
                    database_path,
                    image_dir,
                    partition_output,
                    mapper_params,
                    gpu_index,
                    ctx,
                    db,
                    block.id,
                    coarse_stage="partition_mapping",
                )
            
            # Update partition status
            partition.status = "COMPLETED"
            partition.progress = 100.0
            partition.statistics = {
                "image_count": len(partition_images),
            }
            await db.commit()
            
            ctx.write_log_line(f"[Partition {partition.index}] Completed successfully")
            partition_log_fp.write(f"[Partition {partition.index}] Completed successfully\n")
            
            # Notify progress
            await self._notify_progress(block.id, {
                "pipeline": "sfm",
                "stage": "partition_mapping",
                "progress": 100.0,
                "message": f"Partition {partition.index} completed",
                "partition_index": partition.index,
            })
        except Exception as e:
            partition.status = "FAILED"
            partition.error_message = str(e)
            await db.commit()
            
            ctx.write_log_line(f"[Partition {partition.index}] Failed: {e}")
            partition_log_fp.write(f"[Partition {partition.index}] Failed: {e}\n")
            raise
        finally:
            partition_log_fp.close()


# Singleton TaskRunner instance shared across API and WebSocket.
task_runner = TaskRunner()
