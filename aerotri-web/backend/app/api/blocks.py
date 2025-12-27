"""Block management API endpoints."""
import os
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Block, BlockStatus, get_db
from ..schemas import BlockCreate, BlockUpdate, BlockResponse, BlockListResponse
from ..services.workspace_service import WorkspaceService

router = APIRouter()


@router.post("", response_model=BlockResponse, status_code=status.HTTP_201_CREATED)
async def create_block(
    block_data: BlockCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new block."""
    # Validate image path exists
    if not os.path.isdir(block_data.image_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image path does not exist: {block_data.image_path}"
        )
    
    block_id = str(uuid.uuid4())
    # Create per-block working dir (safe to delete inside)
    working_dir = WorkspaceService.populate_working_dir(block_id, block_data.image_path)

    # Create block (store original path as source, use working_dir for processing & preview)
    block = Block(
        id=block_id,
        name=block_data.name,
        image_path=block_data.image_path,
        source_image_path=block_data.image_path,
        working_image_path=working_dir,
        algorithm=block_data.algorithm,
        matching_method=block_data.matching_method,
        feature_params=block_data.feature_params.model_dump() if block_data.feature_params else None,
        matching_params=block_data.matching_params.model_dump() if block_data.matching_params else None,
        mapper_params=block_data.mapper_params,
    )
    
    db.add(block)
    await db.commit()
    await db.refresh(block)
    
    return block


@router.get("", response_model=BlockListResponse)
async def list_blocks(
    db: AsyncSession = Depends(get_db)
):
    """List all blocks."""
    result = await db.execute(select(Block).order_by(Block.created_at.desc()))
    blocks = result.scalars().all()
    
    return BlockListResponse(
        blocks=[BlockResponse.model_validate(b) for b in blocks],
        total=len(blocks)
    )


@router.get("/{block_id}", response_model=BlockResponse)
async def get_block(
    block_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific block by ID."""
    result = await db.execute(select(Block).where(Block.id == block_id))
    block = result.scalar_one_or_none()
    
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block not found: {block_id}"
        )
    
    return block


@router.patch("/{block_id}", response_model=BlockResponse)
async def update_block(
    block_id: str,
    block_data: BlockUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a block."""
    result = await db.execute(select(Block).where(Block.id == block_id))
    block = result.scalar_one_or_none()
    
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block not found: {block_id}"
        )
    
    # Cannot update if running
    if block.status == BlockStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update a running block"
        )
    
    # Update fields
    update_data = block_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            # Handle Pydantic models (convert to dict)
            if hasattr(value, 'model_dump'):
                value = value.model_dump(exclude_unset=True)
            setattr(block, field, value)
    
    await db.commit()
    await db.refresh(block)
    
    return block


@router.delete("/{block_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_block(
    block_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete a block."""
    result = await db.execute(select(Block).where(Block.id == block_id))
    block = result.scalar_one_or_none()
    
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block not found: {block_id}"
        )
    
    # Cannot delete if running
    if block.status == BlockStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a running block"
        )
    
    await db.delete(block)
    await db.commit()
