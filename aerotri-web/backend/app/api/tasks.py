"""Task execution API endpoints."""
import os
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Block, BlockStatus, AlgorithmType, GlomapMode, get_db
from ..schemas import TaskSubmit, TaskStatus, GlomapResumeRequest
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


@router.post("/{block_id}/merge", response_model=TaskStatus)
async def merge_partitions(
    block_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Start merge task for completed partitions."""
    result = await db.execute(select(Block).where(Block.id == block_id))
    block = result.scalar_one_or_none()
    
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block not found: {block_id}"
        )
    
    if not block.partition_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Block is not in partitioned mode"
        )
    
    if block.current_stage != "partitions_completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Block is not ready for merge. Current stage: {block.current_stage}"
        )
    
    if block.status == BlockStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Block is already running"
        )
    
    # Start the merge task
    await task_runner.start_merge_task(block, db)
    
    # Refresh block to get updated status
    await db.refresh(block)
    
    return TaskStatus(
        block_id=block_id,
        status=block.status,
        current_stage=block.current_stage,
        progress=block.progress or 0.0,
        stage_times=None,
        log_tail=None
    )


@router.post("/{block_id}/glomap/mapper_resume", response_model=TaskStatus)
async def glomap_mapper_resume(
    block_id: str,
    payload: GlomapResumeRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create and start a GLOMAP mapper_resume optimization task.

    This endpoint creates a new Block as a child of the given block_id and
    runs GLOMAP's `mapper_resume` on an existing COLMAP reconstruction.
    """
    # Parent block provides default image/output paths
    result = await db.execute(select(Block).where(Block.id == block_id))
    parent = result.scalar_one_or_none()

    if not parent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block not found: {block_id}",
        )

    # Derive COLMAP input path
    input_colmap_path = payload.input_colmap_path
    if not input_colmap_path:
        if not parent.output_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parent block has no output_path; cannot infer COLMAP input.",
            )
        # Default to parent's primary sparse reconstruction directory
        sparse_root = os.path.join(parent.output_path, "sparse", "0")
        input_colmap_path = sparse_root

    # Compute next version index for this parent
    result = await db.execute(
        select(Block).where(
            Block.parent_block_id == parent.id,
        )
    )
    siblings = result.scalars().all()
    max_version = 0
    for b in siblings:
        try:
            if b.version_index is not None:
                max_version = max(max_version, int(b.version_index))
        except Exception:
            continue
    version_index = max_version + 1

    # Create child block for optimization run
    child = Block(
        name=f"{parent.name} [GLOMAP 优化 #{version_index}]",
        image_path=parent.image_path,
        source_image_path=parent.source_image_path,
        working_image_path=None,
        algorithm=AlgorithmType.GLOMAP,
        matching_method=parent.matching_method,
        feature_params=None,
        matching_params=None,
        mapper_params=parent.mapper_params,
        statistics=None,
        glomap_mode=GlomapMode.MAPPER_RESUME,
        parent_block_id=parent.id,
        input_colmap_path=input_colmap_path,
        output_colmap_path=None,
        version_index=version_index,
        glomap_params=payload.glomap_params or {},
    )
    db.add(child)
    await db.commit()
    await db.refresh(child)

    # Start mapper_resume task for the child block
    await task_runner.start_task(child, payload.gpu_index, db)

    return TaskStatus(
        block_id=child.id,
        status=child.status,
        current_stage=child.current_stage,
        progress=child.progress or 0.0,
        stage_times=None,
        log_tail=None,
    )


@router.get("/{block_id}/versions")
async def list_block_versions(
    block_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List all versions (original + GLOMAP optimization runs) for a block."""
    # The given block can be either the root or one of the versions
    result = await db.execute(select(Block).where(Block.id == block_id))
    base = result.scalar_one_or_none()
    if not base:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block not found: {block_id}",
        )

    # Determine root/parent id for version family
    parent_id = base.parent_block_id or base.id

    result = await db.execute(
        select(Block).where(
            (Block.id == parent_id) | (Block.parent_block_id == parent_id)
        )
    )
    blocks = result.scalars().all()

    items = []
    for b in blocks:
        items.append(
            {
                "id": b.id,
                "name": b.name,
                "status": b.status.value,
                "glomap_mode": b.glomap_mode.value if getattr(b, "glomap_mode", None) else None,
                "parent_block_id": b.parent_block_id,
                "version_index": b.version_index,
                "output_path": b.output_path,
                "output_colmap_path": getattr(b, "output_colmap_path", None),
                "created_at": b.created_at.isoformat() if b.created_at else None,
                "completed_at": b.completed_at.isoformat() if b.completed_at else None,
            }
        )

    # Sort by version_index (root/original first)
    def _sort_key(item):
        vi = item.get("version_index")
        return (0 if vi is None else 1, vi or 0)

    items_sorted = sorted(items, key=_sort_key)
    return {"versions": items_sorted}
