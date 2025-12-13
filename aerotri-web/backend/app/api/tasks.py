"""Task execution API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Block, BlockStatus, get_db
from ..schemas import TaskSubmit, TaskStatus
from ..services.task_runner import task_runner

router = APIRouter()


@router.post("/{block_id}/run", response_model=TaskStatus)
async def run_block(
    block_id: str,
    task_submit: TaskSubmit,
    db: AsyncSession = Depends(get_db)
):
    """Submit a block for processing."""
    result = await db.execute(select(Block).where(Block.id == block_id))
    block = result.scalar_one_or_none()
    
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block not found: {block_id}"
        )
    
    if block.status == BlockStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Block is already running"
        )
    
    # Start the task
    await task_runner.start_task(block, task_submit.gpu_index, db)
    
    return TaskStatus(
        block_id=block_id,
        status=block.status,
        current_stage=block.current_stage,
        progress=block.progress or 0.0,
        stage_times=None,
        log_tail=None
    )


@router.get("/{block_id}/status", response_model=TaskStatus)
async def get_task_status(
    block_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get current task status."""
    result = await db.execute(select(Block).where(Block.id == block_id))
    block = result.scalar_one_or_none()
    
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block not found: {block_id}"
        )
    
    # Get log tail
    log_tail = task_runner.get_log_tail(block_id, lines=20)
    
    # Get stage times
    stage_times = task_runner.get_stage_times(block_id)
    
    return TaskStatus(
        block_id=block_id,
        status=block.status,
        current_stage=block.current_stage,
        progress=block.progress or 0.0,
        stage_times=stage_times,
        log_tail=log_tail
    )


@router.post("/{block_id}/stop", response_model=TaskStatus)
async def stop_task(
    block_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Stop a running task."""
    result = await db.execute(select(Block).where(Block.id == block_id))
    block = result.scalar_one_or_none()
    
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block not found: {block_id}"
        )
    
    if block.status != BlockStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Block is not running"
        )
    
    # Stop the task
    await task_runner.stop_task(block_id, db)
    
    return TaskStatus(
        block_id=block_id,
        status=block.status,
        current_stage=block.current_stage,
        progress=block.progress or 0.0,
        stage_times=None,
        log_tail=None
    )
