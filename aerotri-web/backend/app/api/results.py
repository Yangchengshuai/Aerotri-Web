"""Reconstruction results API endpoints."""
import os
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Block, BlockStatus, get_db
from ..schemas import CameraInfo, Point3D, ReconstructionStats
from ..services.result_reader import ResultReader

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".gif"}

router = APIRouter()


@router.get("/{block_id}/result/cameras", response_model=List[CameraInfo])
async def get_cameras(
    block_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get camera poses from reconstruction."""
    result = await db.execute(select(Block).where(Block.id == block_id))
    block = result.scalar_one_or_none()
    
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block not found: {block_id}"
        )
    
    if block.status != BlockStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reconstruction not completed"
        )
    
    if not block.output_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No output path available"
        )
    
    try:
        cameras = ResultReader.read_cameras(block.output_path)
        return cameras
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read cameras: {str(e)}"
        )


@router.get("/{block_id}/result/points")
async def get_points(
    block_id: str,
    limit: int = Query(100000, ge=1, le=1000000),
    db: AsyncSession = Depends(get_db)
):
    """Get 3D points from reconstruction."""
    result = await db.execute(select(Block).where(Block.id == block_id))
    block = result.scalar_one_or_none()
    
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block not found: {block_id}"
        )
    
    if block.status != BlockStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reconstruction not completed"
        )
    
    if not block.output_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No output path available"
        )
    
    try:
        points = ResultReader.read_points3d(block.output_path, limit=limit)
        return {"points": points, "total": len(points)}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read points: {str(e)}"
        )


@router.get("/{block_id}/result/stats", response_model=ReconstructionStats)
async def get_stats(
    block_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get reconstruction statistics."""
    result = await db.execute(select(Block).where(Block.id == block_id))
    block = result.scalar_one_or_none()
    
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block not found: {block_id}"
        )
    
    if block.status != BlockStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reconstruction not completed"
        )
    
    if not block.output_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No output path available"
        )
    
    # Read actual reconstruction statistics from binary files
    try:
        recon_stats = ResultReader.get_stats(block.output_path)
    except Exception:
        recon_stats = {}
    
    # Count total images from image directory
    num_images = 0
    image_dir = getattr(block, 'working_image_path', None) or block.image_path
    if image_dir and os.path.isdir(image_dir):
        try:
            for f in os.listdir(image_dir):
                if os.path.splitext(f)[1].lower() in IMAGE_EXTENSIONS:
                    num_images += 1
        except Exception:
            pass
    
    # Merge with block.statistics (stage_times, algorithm_params)
    block_stats = block.statistics or {}
    merged = {
        "num_images": num_images,
        "num_registered_images": recon_stats.get("num_registered_images", 0),
        "num_points3d": recon_stats.get("num_points3d", 0),
        "num_observations": recon_stats.get("num_observations", 0),
        "mean_reprojection_error": recon_stats.get("mean_reprojection_error", 0.0),
        "mean_track_length": recon_stats.get("mean_track_length", 0.0),
        "stage_times": block_stats.get("stage_times", {}),
        "algorithm_params": block_stats.get("algorithm_params", {}),
    }
    
    return ReconstructionStats(**merged)
