"""Image management API endpoints."""
import os
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Block, get_db
from ..schemas import ImageInfo, ImageListResponse
from ..services.image_service import ImageService
from ..services.workspace_service import WorkspaceService

router = APIRouter()

# Supported image extensions
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp'}


def get_image_files(directory: str) -> list:
    """Get list of image files in directory."""
    path = Path(directory)
    if not path.exists():
        return []
    
    images = []
    for f in sorted(path.iterdir()):
        if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS:
            images.append(f)
    return images


def _get_block_image_dir(block: Block) -> str:
    # Prefer safe per-block working directory
    return block.working_image_path or block.image_path


@router.get("/{block_id}/images", response_model=ImageListResponse)
async def list_images(
    block_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """List images in a block with pagination."""
    result = await db.execute(select(Block).where(Block.id == block_id))
    block = result.scalar_one_or_none()
    
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block not found: {block_id}"
        )
    
    image_dir = _get_block_image_dir(block)
    # Get all image files
    all_images = get_image_files(image_dir)
    total = len(all_images)
    
    # Paginate
    start = (page - 1) * page_size
    end = start + page_size
    page_images = all_images[start:end]
    
    # Build response
    images = []
    for img_path in page_images:
        stat = img_path.stat()
        images.append(ImageInfo(
            name=img_path.name,
            path=str(img_path),
            size=stat.st_size,
            thumbnail_url=f"/api/blocks/{block_id}/images/{img_path.name}/thumbnail"
        ))
    
    return ImageListResponse(
        images=images,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{block_id}/images/{image_name}/thumbnail")
async def get_image_thumbnail(
    block_id: str,
    image_name: str,
    size: int = Query(200, ge=50, le=500),
    db: AsyncSession = Depends(get_db)
):
    """Get thumbnail of an image."""
    result = await db.execute(select(Block).where(Block.id == block_id))
    block = result.scalar_one_or_none()
    
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block not found: {block_id}"
        )
    
    image_dir = _get_block_image_dir(block)
    try:
        image_path = WorkspaceService.safe_resolve_child(image_dir, image_name)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image name")

    if not image_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image not found: {image_name}"
        )
    
    # Generate or get cached thumbnail
    thumbnail_path = await ImageService.get_thumbnail(str(image_path), size)
    
    return FileResponse(
        thumbnail_path,
        media_type="image/jpeg",
        headers={"Cache-Control": "max-age=3600"}
    )


@router.get("/{block_id}/images/{image_name}")
async def get_image(
    block_id: str,
    image_name: str,
    db: AsyncSession = Depends(get_db)
):
    """Get original image."""
    result = await db.execute(select(Block).where(Block.id == block_id))
    block = result.scalar_one_or_none()
    
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block not found: {block_id}"
        )
    
    image_dir = _get_block_image_dir(block)
    try:
        image_path = WorkspaceService.safe_resolve_child(image_dir, image_name)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image name")

    if not image_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image not found: {image_name}"
        )
    
    # Determine media type
    suffix = image_path.suffix.lower()
    media_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.tif': 'image/tiff',
        '.tiff': 'image/tiff',
        '.bmp': 'image/bmp',
    }
    
    return FileResponse(
        str(image_path),
        media_type=media_types.get(suffix, 'application/octet-stream')
    )


@router.delete("/{block_id}/images/{image_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image(
    block_id: str,
    image_name: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete an image from block."""
    result = await db.execute(select(Block).where(Block.id == block_id))
    block = result.scalar_one_or_none()
    
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block not found: {block_id}"
        )
    
    # Never delete files from the original source directory.
    if not block.working_image_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This block has no working image directory; deletion is disabled for safety."
        )

    try:
        image_path = WorkspaceService.safe_resolve_child(block.working_image_path, image_name)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image name")

    if not image_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image not found: {image_name}"
        )
    
    # Delete the image file
    image_path.unlink()
