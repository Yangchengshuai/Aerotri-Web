"""Queue management API endpoints."""
import os
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Block, BlockStatus, get_db
from ..schemas import (
    QueueListResponse,
    QueueItemResponse,
    QueueConfigResponse,
    QueueConfigUpdate,
    EnqueueResponse,
    DequeueResponse,
)

router = APIRouter()

# In-memory config (can be moved to database or settings later)
# Default is 1 (historical behavior). Can be overridden by env QUEUE_MAX_CONCURRENT.
def _default_max_concurrent() -> int:
    try:
        v = int(os.environ.get("QUEUE_MAX_CONCURRENT", "1"))
        return max(1, min(10, v))
    except Exception:
        return 1


_queue_config = {"max_concurrent": _default_max_concurrent()}


@router.get("", response_model=QueueListResponse)
async def list_queue(db: AsyncSession = Depends(get_db)):
    """Get all queued tasks ordered by position."""
    # Get queued blocks
    result = await db.execute(
        select(Block)
        .where(Block.status == BlockStatus.QUEUED)
        .order_by(Block.queue_position.asc())
    )
    queued_blocks = result.scalars().all()
    
    # Get running count
    result = await db.execute(
        select(func.count(Block.id))
        .where(Block.status == BlockStatus.RUNNING)
    )
    running_count = result.scalar() or 0
    
    items = [
        QueueItemResponse(
            id=b.id,
            name=b.name,
            algorithm=b.algorithm.value,
            matching_method=b.matching_method.value,
            queue_position=b.queue_position,
            queued_at=b.queued_at,
            image_path=b.image_path,
        )
        for b in queued_blocks
    ]
    
    return QueueListResponse(
        items=items,
        total=len(items),
        running_count=running_count,
        max_concurrent=_queue_config["max_concurrent"],
    )


@router.get("/config", response_model=QueueConfigResponse)
async def get_queue_config():
    """Get queue configuration."""
    return QueueConfigResponse(max_concurrent=_queue_config["max_concurrent"])


@router.put("/config", response_model=QueueConfigResponse)
async def update_queue_config(config: QueueConfigUpdate):
    """Update queue configuration."""
    _queue_config["max_concurrent"] = config.max_concurrent
    return QueueConfigResponse(max_concurrent=_queue_config["max_concurrent"])


@router.post("/blocks/{block_id}/enqueue", response_model=EnqueueResponse)
async def enqueue_block(
    block_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Add a block to the queue."""
    result = await db.execute(select(Block).where(Block.id == block_id))
    block = result.scalar_one_or_none()
    
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block not found: {block_id}"
        )
    
    # Only CREATED blocks can be queued
    if block.status != BlockStatus.CREATED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Block cannot be queued. Current status: {block.status.value}"
        )
    
    # Get max position in queue
    result = await db.execute(
        select(func.max(Block.queue_position))
        .where(Block.status == BlockStatus.QUEUED)
    )
    max_position = result.scalar() or 0
    
    # Assign next position
    new_position = max_position + 1
    now = datetime.utcnow()
    
    block.status = BlockStatus.QUEUED
    block.queue_position = new_position
    block.queued_at = now
    
    await db.commit()
    await db.refresh(block)
    
    return EnqueueResponse(
        block_id=block.id,
        queue_position=new_position,
        queued_at=now,
    )


@router.post("/blocks/{block_id}/dequeue", response_model=DequeueResponse)
async def dequeue_block(
    block_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Remove a block from the queue."""
    result = await db.execute(select(Block).where(Block.id == block_id))
    block = result.scalar_one_or_none()
    
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block not found: {block_id}"
        )
    
    if block.status != BlockStatus.QUEUED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Block is not in queue. Current status: {block.status.value}"
        )
    
    old_position = block.queue_position
    
    # Reset block to CREATED
    block.status = BlockStatus.CREATED
    block.queue_position = None
    block.queued_at = None
    
    # Reorder remaining queued blocks
    result = await db.execute(
        select(Block)
        .where(Block.status == BlockStatus.QUEUED)
        .where(Block.queue_position > old_position)
        .order_by(Block.queue_position.asc())
    )
    blocks_to_shift = result.scalars().all()
    
    for b in blocks_to_shift:
        b.queue_position -= 1
    
    await db.commit()
    await db.refresh(block)
    
    return DequeueResponse(
        block_id=block.id,
        status=block.status,
    )


@router.post("/blocks/{block_id}/queue/top", response_model=EnqueueResponse)
async def move_to_top(
    block_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Move a queued block to the top of the queue (position 1)."""
    result = await db.execute(select(Block).where(Block.id == block_id))
    block = result.scalar_one_or_none()
    
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block not found: {block_id}"
        )
    
    if block.status != BlockStatus.QUEUED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Block is not in queue. Current status: {block.status.value}"
        )
    
    old_position = block.queue_position
    
    if old_position == 1:
        # Already at top
        return EnqueueResponse(
            block_id=block.id,
            queue_position=1,
            queued_at=block.queued_at,
        )
    
    # Shift all blocks with position < old_position up by 1
    result = await db.execute(
        select(Block)
        .where(Block.status == BlockStatus.QUEUED)
        .where(Block.queue_position < old_position)
        .order_by(Block.queue_position.asc())
    )
    blocks_to_shift = result.scalars().all()
    
    for b in blocks_to_shift:
        b.queue_position += 1
    
    # Move target block to position 1
    block.queue_position = 1
    
    await db.commit()
    await db.refresh(block)
    
    return EnqueueResponse(
        block_id=block.id,
        queue_position=1,
        queued_at=block.queued_at,
    )


def get_max_concurrent() -> int:
    """Get the maximum number of concurrent tasks (for use by scheduler)."""
    return _queue_config["max_concurrent"]
