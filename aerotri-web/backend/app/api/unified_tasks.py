"""Unified task view API endpoints."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import get_db
from ..services.task_view_service import task_view_service

router = APIRouter()


class UnifiedTaskResponse(BaseModel):
    """Response model for a unified task."""
    task_id: str
    task_type: str
    block_id: str
    block_name: str
    version_id: Optional[str] = None
    version_name: Optional[str] = None
    status: str
    stage: Optional[str] = None
    progress: float
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None


class TaskListResponse(BaseModel):
    """Response model for task list."""
    tasks: List[UnifiedTaskResponse]
    total: int


class TaskSummaryResponse(BaseModel):
    """Response model for task summary."""
    total: int
    running: int
    waiting: int
    failed: int
    by_status: Dict[str, int]
    by_type: Dict[str, int]
    timestamp: datetime


@router.get("/tasks", response_model=TaskListResponse)
async def list_all_tasks(
    status: Optional[str] = Query(
        None,
        description="Filter by status (waiting/running/success/failed)"
    ),
    task_type: Optional[str] = Query(
        None,
        description="Filter by task type (sfm/recon/gs/gs_tiles/tiles/recon_version)"
    ),
    include_pending: bool = Query(
        False,
        description="Include tasks that haven't started yet"
    ),
    db: AsyncSession = Depends(get_db),
):
    """Get all tasks as unified views.
    
    Returns a list of all active and completed tasks across all task types
    (SfM, OpenMVS reconstruction, 3DGS training, 3D Tiles conversion).
    
    The tasks are sorted by status (running first) and then by start time.
    """
    tasks = await task_view_service.get_all_tasks(
        db,
        status_filter=status,
        task_type_filter=task_type,
        include_pending=include_pending,
    )
    
    return TaskListResponse(
        tasks=[
            UnifiedTaskResponse(**t.to_dict())
            for t in tasks
        ],
        total=len(tasks),
    )


@router.get("/tasks/summary", response_model=TaskSummaryResponse)
async def get_task_summary(
    db: AsyncSession = Depends(get_db),
):
    """Get task statistics summary.
    
    Returns counts of tasks by status and by type, useful for dashboard displays.
    """
    summary = await task_view_service.get_task_summary(db)
    
    return TaskSummaryResponse(
        total=summary["total"],
        running=summary["running"],
        waiting=summary["waiting"],
        failed=summary["failed"],
        by_status=summary["by_status"],
        by_type=summary["by_type"],
        timestamp=datetime.utcnow(),
    )


@router.get("/tasks/running", response_model=TaskListResponse)
async def list_running_tasks(
    db: AsyncSession = Depends(get_db),
):
    """Get currently running tasks.
    
    Convenience endpoint equivalent to /tasks?status=running.
    """
    tasks = await task_view_service.get_all_tasks(
        db,
        status_filter="running",
    )
    
    return TaskListResponse(
        tasks=[
            UnifiedTaskResponse(**t.to_dict())
            for t in tasks
        ],
        total=len(tasks),
    )


@router.get("/tasks/failed", response_model=TaskListResponse)
async def list_failed_tasks(
    db: AsyncSession = Depends(get_db),
):
    """Get failed tasks.
    
    Convenience endpoint equivalent to /tasks?status=failed.
    """
    tasks = await task_view_service.get_all_tasks(
        db,
        status_filter="failed",
    )
    
    return TaskListResponse(
        tasks=[
            UnifiedTaskResponse(**t.to_dict())
            for t in tasks
        ],
        total=len(tasks),
    )
