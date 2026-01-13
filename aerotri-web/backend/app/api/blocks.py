"""Block management API endpoints."""

import os
import shutil
import uuid
from pathlib import Path
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Block, BlockStatus, get_db
from ..schemas import BlockCreate, BlockUpdate, BlockResponse, BlockListResponse
from ..services.workspace_service import WorkspaceService

router = APIRouter()

# Keep consistent with app/api/images.py
_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}


def _count_images_in_dir(directory: str) -> int:
    """Count images in a directory (non-recursive)."""
    try:
        p = Path(directory)
        if not p.exists() or not p.is_dir():
            return 0
        return sum(
            1
            for f in p.iterdir()
            if f.is_file() and f.suffix.lower() in _IMAGE_EXTENSIONS
        )
    except Exception:
        return 0


def _ensure_num_images(block: Block) -> int:
    """Best-effort compute image count for a block."""
    image_dir = block.working_image_path or block.image_path
    return _count_images_in_dir(image_dir)


@router.post("", response_model=BlockResponse, status_code=status.HTTP_201_CREATED)
async def create_block(block_data: BlockCreate, db: AsyncSession = Depends(get_db)):
    """Create a new block."""
    # Validate image path exists
    if not os.path.isdir(block_data.image_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image path does not exist: {block_data.image_path}",
        )

    block_id = str(uuid.uuid4())
    # Create per-block working dir (safe to delete inside)
    working_dir = WorkspaceService.populate_working_dir(block_id, block_data.image_path)
    num_images = _count_images_in_dir(working_dir)

    # Create block (store original path as source, use working_dir for processing & preview)
    block = Block(
        id=block_id,
        name=block_data.name,
        image_path=block_data.image_path,
        source_image_path=block_data.image_path,
        working_image_path=working_dir,
        algorithm=block_data.algorithm,
        matching_method=block_data.matching_method,
        feature_params=block_data.feature_params.model_dump()
        if block_data.feature_params
        else None,
        matching_params=block_data.matching_params.model_dump()
        if block_data.matching_params
        else None,
        mapper_params=block_data.mapper_params,
        openmvg_params=block_data.openmvg_params,
        statistics={"num_images": num_images},
    )

    db.add(block)
    await db.commit()
    await db.refresh(block)

    return block


@router.get("", response_model=BlockListResponse)
async def list_blocks(db: AsyncSession = Depends(get_db)):
    """List all blocks."""
    result = await db.execute(select(Block).order_by(Block.created_at.desc()))
    blocks = result.scalars().all()

    responses: List[BlockResponse] = []
    for b in blocks:
        resp = BlockResponse.model_validate(b)
        # Backfill num_images for older blocks that don't have it in statistics yet
        stats = dict(resp.statistics or {})
        if "num_images" not in stats:
            stats["num_images"] = _ensure_num_images(b)
            resp.statistics = stats
        responses.append(resp)

    return BlockListResponse(blocks=responses, total=len(responses))


@router.get("/{block_id}", response_model=BlockResponse)
async def get_block(block_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific block by ID."""
    result = await db.execute(select(Block).where(Block.id == block_id))
    block = result.scalar_one_or_none()

    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Block not found: {block_id}"
        )

    resp = BlockResponse.model_validate(block)
    stats = dict(resp.statistics or {})
    if "num_images" not in stats:
        stats["num_images"] = _ensure_num_images(block)
        resp.statistics = stats
    return resp


@router.patch("/{block_id}", response_model=BlockResponse)
async def update_block(
    block_id: str, block_data: BlockUpdate, db: AsyncSession = Depends(get_db)
):
    """Update a block."""
    result = await db.execute(select(Block).where(Block.id == block_id))
    block = result.scalar_one_or_none()

    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Block not found: {block_id}"
        )

    # Cannot update if running
    if block.status == BlockStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update a running block",
        )

    # Update fields
    update_data = block_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            # Handle Pydantic models (convert to dict)
            if hasattr(value, "model_dump"):
                value = value.model_dump(exclude_unset=True)
            # For dict fields (feature_params, matching_params, mapper_params),
            # ensure we store the dict directly (frontend sends complete objects)
            setattr(block, field, value)

    await db.commit()
    await db.refresh(block)

    return block


@router.delete("/{block_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_block(block_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a block and its associated data directories."""
    result = await db.execute(select(Block).where(Block.id == block_id))
    block = result.scalar_one_or_none()

    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Block not found: {block_id}"
        )

    # Cannot delete if running
    if block.status == BlockStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a running block",
        )

    # Delete blocks directory (image data)
    block_dir = WorkspaceService.get_block_root(block_id)
    if os.path.exists(block_dir):
        try:
            shutil.rmtree(block_dir)
        except Exception as e:
            print(f"Warning: Failed to delete block directory {block_dir}: {e}")

    # Delete outputs directory (intermediate files and logs)
    outputs_dir = f"/root/work/aerotri-web/data/outputs/{block_id}"
    if os.path.exists(outputs_dir):
        try:
            shutil.rmtree(outputs_dir)
        except Exception as e:
            print(f"Warning: Failed to delete output directory {outputs_dir}: {e}")

    # Delete from database
    await db.delete(block)
    await db.commit()
