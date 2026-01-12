"""Unified task view service for AeroTri Web.

Provides a unified view of all task types (SfM, OpenMVS, 3DGS, Tiles)
without modifying the existing database schema.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.block import Block, BlockStatus
from ..models.recon_version import ReconVersion, ReconVersionStatus

logger = logging.getLogger(__name__)


# Mapping from internal status to unified status
STATUS_MAPPING = {
    # Block status
    "created": "pending",
    "queued": "waiting",
    "running": "running",
    "completed": "success",
    "failed": "failed",
    "cancelled": "cancelled",
    # Recon/GS/Tiles status (uppercase in DB)
    "NOT_STARTED": "pending",
    "PENDING": "pending",
    "QUEUED": "waiting",
    "RUNNING": "running",
    "COMPLETED": "success",
    "FAILED": "failed",
    "CANCELLED": "cancelled",
}


def _normalize_status(status: Optional[str]) -> str:
    """Normalize status to unified format."""
    if not status:
        return "pending"
    return STATUS_MAPPING.get(status, status.lower())


def _calc_duration(started_at: Optional[datetime], completed_at: Optional[datetime]) -> Optional[float]:
    """Calculate duration in seconds."""
    if not started_at:
        return None
    end_time = completed_at or datetime.utcnow()
    return (end_time - started_at).total_seconds()


class UnifiedTaskView:
    """Unified view of a task."""
    
    def __init__(
        self,
        task_id: str,
        task_type: str,
        block_id: str,
        block_name: str,
        status: str,
        stage: Optional[str] = None,
        progress: float = 0.0,
        error: Optional[str] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        version_id: Optional[str] = None,
        version_name: Optional[str] = None,
    ):
        self.task_id = task_id
        self.task_type = task_type
        self.block_id = block_id
        self.block_name = block_name
        self.version_id = version_id
        self.version_name = version_name
        self.status = status
        self.stage = stage
        self.progress = progress
        self.error = error
        self.started_at = started_at
        self.completed_at = completed_at
        self.duration_seconds = _calc_duration(started_at, completed_at)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "block_id": self.block_id,
            "block_name": self.block_name,
            "version_id": self.version_id,
            "version_name": self.version_name,
            "status": self.status,
            "stage": self.stage,
            "progress": self.progress,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
        }


class TaskViewService:
    """Service for unified task view."""
    
    @staticmethod
    def _extract_sfm_task(block: Block) -> Optional[UnifiedTaskView]:
        """Extract SfM task from Block."""
        # SfM task is represented by the block's main status
        status = _normalize_status(block.status.value if block.status else None)
        
        # Skip if not started (created status with no progress)
        if status == "pending" and block.progress == 0:
            return None
        
        return UnifiedTaskView(
            task_id=f"{block.id}:sfm",
            task_type="sfm",
            block_id=block.id,
            block_name=block.name,
            status=status,
            stage=block.current_stage,
            progress=block.progress or 0.0,
            error=block.error_message,
            started_at=block.started_at,
            completed_at=block.completed_at,
        )
    
    @staticmethod
    def _extract_recon_task(block: Block) -> Optional[UnifiedTaskView]:
        """Extract OpenMVS reconstruction task from Block."""
        status = _normalize_status(block.recon_status)
        
        # Skip if not started
        if status == "pending" and (block.recon_progress or 0) == 0:
            return None
        
        return UnifiedTaskView(
            task_id=f"{block.id}:recon",
            task_type="recon",
            block_id=block.id,
            block_name=block.name,
            status=status,
            stage=block.recon_current_stage,
            progress=block.recon_progress or 0.0,
            error=block.recon_error_message,
            # Note: Block doesn't have recon start/end times, use block times as fallback
            started_at=block.started_at if status == "running" else None,
            completed_at=block.completed_at if status == "success" else None,
        )
    
    @staticmethod
    def _extract_gs_task(block: Block) -> Optional[UnifiedTaskView]:
        """Extract 3DGS training task from Block."""
        status = _normalize_status(block.gs_status)
        
        # Skip if not started
        if status == "pending" and (block.gs_progress or 0) == 0:
            return None
        
        return UnifiedTaskView(
            task_id=f"{block.id}:gs",
            task_type="gs",
            block_id=block.id,
            block_name=block.name,
            status=status,
            stage=block.gs_current_stage,
            progress=block.gs_progress or 0.0,
            error=block.gs_error_message,
        )
    
    @staticmethod
    def _extract_gs_tiles_task(block: Block) -> Optional[UnifiedTaskView]:
        """Extract 3DGS Tiles conversion task from Block."""
        status = _normalize_status(block.gs_tiles_status)
        
        # Skip if not started
        if status == "pending" and (block.gs_tiles_progress or 0) == 0:
            return None
        
        return UnifiedTaskView(
            task_id=f"{block.id}:gs_tiles",
            task_type="gs_tiles",
            block_id=block.id,
            block_name=block.name,
            status=status,
            stage=block.gs_tiles_current_stage,
            progress=block.gs_tiles_progress or 0.0,
            error=block.gs_tiles_error_message,
        )
    
    @staticmethod
    def _extract_tiles_task(block: Block) -> Optional[UnifiedTaskView]:
        """Extract 3D Tiles conversion task from Block."""
        status = _normalize_status(block.tiles_status)
        
        # Skip if not started
        if status == "pending" and (block.tiles_progress or 0) == 0:
            return None
        
        return UnifiedTaskView(
            task_id=f"{block.id}:tiles",
            task_type="tiles",
            block_id=block.id,
            block_name=block.name,
            status=status,
            stage=block.tiles_current_stage,
            progress=block.tiles_progress or 0.0,
            error=block.tiles_error_message,
        )
    
    @staticmethod
    def _extract_recon_version_task(block: Block, version: ReconVersion) -> UnifiedTaskView:
        """Extract ReconVersion task."""
        status = _normalize_status(version.status)
        
        return UnifiedTaskView(
            task_id=f"{block.id}:recon_v:{version.id}",
            task_type="recon_version",
            block_id=block.id,
            block_name=block.name,
            version_id=version.id,
            version_name=version.name,
            status=status,
            stage=version.current_stage,
            progress=version.progress or 0.0,
            error=version.error_message,
            started_at=version.created_at,
            completed_at=version.completed_at,
        )
    
    @classmethod
    async def get_all_tasks(
        cls,
        db: AsyncSession,
        status_filter: Optional[str] = None,
        task_type_filter: Optional[str] = None,
        include_pending: bool = False,
    ) -> List[UnifiedTaskView]:
        """Get all tasks as unified views.
        
        Args:
            db: Database session
            status_filter: Filter by status (waiting/running/success/failed)
            task_type_filter: Filter by task type (sfm/recon/gs/gs_tiles/tiles/recon_version)
            include_pending: Include tasks that haven't started yet
            
        Returns:
            List of UnifiedTaskView objects
        """
        tasks: List[UnifiedTaskView] = []
        
        # Get all blocks
        result = await db.execute(select(Block))
        blocks = result.scalars().all()
        
        # Get all recon versions
        result = await db.execute(select(ReconVersion))
        recon_versions = result.scalars().all()
        
        # Create block lookup for recon versions
        block_map = {b.id: b for b in blocks}
        
        # Extract tasks from blocks
        for block in blocks:
            # SfM task
            if not task_type_filter or task_type_filter == "sfm":
                task = cls._extract_sfm_task(block)
                if task and (include_pending or task.status != "pending"):
                    tasks.append(task)
            
            # OpenMVS recon task (from Block fields)
            if not task_type_filter or task_type_filter == "recon":
                task = cls._extract_recon_task(block)
                if task and (include_pending or task.status != "pending"):
                    tasks.append(task)
            
            # 3DGS task
            if not task_type_filter or task_type_filter == "gs":
                task = cls._extract_gs_task(block)
                if task and (include_pending or task.status != "pending"):
                    tasks.append(task)
            
            # GS Tiles task
            if not task_type_filter or task_type_filter == "gs_tiles":
                task = cls._extract_gs_tiles_task(block)
                if task and (include_pending or task.status != "pending"):
                    tasks.append(task)
            
            # Tiles task
            if not task_type_filter or task_type_filter == "tiles":
                task = cls._extract_tiles_task(block)
                if task and (include_pending or task.status != "pending"):
                    tasks.append(task)
        
        # Extract tasks from ReconVersions
        if not task_type_filter or task_type_filter == "recon_version":
            for version in recon_versions:
                block = block_map.get(version.block_id)
                if block:
                    task = cls._extract_recon_version_task(block, version)
                    if include_pending or task.status != "pending":
                        tasks.append(task)
        
        # Apply status filter
        if status_filter:
            tasks = [t for t in tasks if t.status == status_filter]
        
        # Sort by most recently active (running first, then by started_at)
        def sort_key(t: UnifiedTaskView):
            status_order = {"running": 0, "waiting": 1, "failed": 2, "success": 3, "pending": 4}
            return (
                status_order.get(t.status, 5),
                -(t.started_at.timestamp() if t.started_at else 0),
            )
        
        tasks.sort(key=sort_key)
        
        return tasks
    
    @classmethod
    async def get_task_summary(cls, db: AsyncSession) -> Dict[str, Any]:
        """Get task statistics summary.
        
        Args:
            db: Database session
            
        Returns:
            Summary dict with counts by status and type
        """
        tasks = await cls.get_all_tasks(db, include_pending=True)
        
        # Count by status
        status_counts = {
            "pending": 0,
            "waiting": 0,
            "running": 0,
            "success": 0,
            "failed": 0,
            "cancelled": 0,
        }
        
        # Count by type
        type_counts = {
            "sfm": 0,
            "recon": 0,
            "gs": 0,
            "gs_tiles": 0,
            "tiles": 0,
            "recon_version": 0,
        }
        
        for task in tasks:
            if task.status in status_counts:
                status_counts[task.status] += 1
            if task.task_type in type_counts:
                type_counts[task.task_type] += 1
        
        return {
            "total": len(tasks),
            "by_status": status_counts,
            "by_type": type_counts,
            "running": status_counts["running"],
            "waiting": status_counts["waiting"],
            "failed": status_counts["failed"],
            "timestamp": datetime.utcnow().isoformat(),
        }


# Global instance
task_view_service = TaskViewService()
