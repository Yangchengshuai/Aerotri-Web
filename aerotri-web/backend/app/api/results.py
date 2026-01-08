"""Reconstruction results API endpoints."""
import os
import struct
import tempfile
from typing import List
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import FileResponse
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
    
    # For partitioned blocks, allow access if partitions are completed (even if not merged)
    if block.partition_enabled:
        if block.current_stage not in ("partitions_completed", "merging", "completed"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Partitions not completed yet"
            )
    elif block.status != BlockStatus.COMPLETED:
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
        # Prioritize block.output_colmap_path if set (e.g. for openMVG)
        if block.output_colmap_path and os.path.isdir(block.output_colmap_path):
            cameras = ResultReader.read_cameras(block.output_colmap_path)
            return cameras
        
        # For partitioned blocks without merged result, return empty list
        # (user should use partition-specific API instead)
        if block.partition_enabled and block.current_stage == "partitions_completed":
            # Check if merged result exists
            merged_sparse = os.path.join(block.output_path, "merged", "sparse", "0")
            if not os.path.exists(merged_sparse):
                # No merged result, return empty (user should use partition API)
                return []
        
        cameras = ResultReader.read_cameras(block.output_path)
        return cameras
    except FileNotFoundError:
        # If no merged result and partitioned, return empty
        if block.partition_enabled:
            return []
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No reconstruction found"
        )
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
    
    # For partitioned blocks, allow access if partitions are completed (even if not merged)
    if block.partition_enabled:
        if block.current_stage not in ("partitions_completed", "merging", "completed"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Partitions not completed yet"
            )
    elif block.status != BlockStatus.COMPLETED:
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
        # Prioritize block.output_colmap_path if set (e.g. for openMVG)
        if block.output_colmap_path and os.path.isdir(block.output_colmap_path):
            points, total = ResultReader.read_points3d(block.output_colmap_path, limit=limit)
            return {"points": points, "total": total}
        
        # For partitioned blocks without merged result, return empty
        # (user should use partition-specific API instead)
        if block.partition_enabled and block.current_stage == "partitions_completed":
            # Check if merged result exists
            merged_sparse = os.path.join(block.output_path, "merged", "sparse", "0")
            if not os.path.exists(merged_sparse):
                # No merged result, return empty (user should use partition API)
                return {"points": [], "total": 0}
        
        points, total = ResultReader.read_points3d(block.output_path, limit=limit)
        return {"points": points, "total": total}
    except FileNotFoundError:
        # If no merged result and partitioned, return empty
        if block.partition_enabled:
            return {"points": [], "total": 0}
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No reconstruction found"
        )
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
    
    # For partitioned blocks, allow access if partitions are completed (even if not merged)
    if block.partition_enabled:
        if block.current_stage not in ("partitions_completed", "merging", "completed"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Partitions not completed yet"
            )
    elif block.status != BlockStatus.COMPLETED:
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
    # For partitioned blocks that are not merged yet, try to aggregate partition stats
    recon_stats = {}
    if block.partition_enabled and block.current_stage == "partitions_completed":
        # Aggregate statistics from all partitions
        try:
            from ..services.partition_service import PartitionService
            partitions = await PartitionService.get_partitions(block.id, db)
            
            total_registered_sum = 0
            registered_unique_names = set()
            total_points = 0
            total_observations = 0
            total_error = 0.0
            total_track_length = 0
            partition_count = 0
            
            for partition in partitions:
                if partition.status == "COMPLETED":
                    try:
                        part_stats = ResultReader.read_partition_stats(block.output_path, partition.index)
                        if part_stats:
                            total_registered_sum += part_stats.get("num_registered_images", 0)
                            total_points += part_stats.get("num_points3d", 0)
                            total_observations += part_stats.get("num_observations", 0)
                            total_error += part_stats.get("mean_reprojection_error", 0.0) * part_stats.get("num_points3d", 0)
                            total_track_length += part_stats.get("mean_track_length", 0.0) * part_stats.get("num_points3d", 0)
                            partition_count += 1
                        # Also compute unique registered images by names (avoid overlap double counting)
                        try:
                            cams = ResultReader.read_partition_cameras(block.output_path, partition.index)
                            for c in cams:
                                registered_unique_names.add(c.image_name)
                        except Exception:
                            pass
                    except Exception:
                        pass
            
            if partition_count > 0:
                total_registered_unique = len(registered_unique_names) if registered_unique_names else 0
                recon_stats = {
                    # Default num_registered_images uses unique semantics (more intuitive)
                    "num_registered_images": total_registered_unique or total_registered_sum,
                    "num_registered_images_unique": total_registered_unique,
                    "num_registered_images_sum": total_registered_sum,
                    "num_points3d": total_points,
                    "num_observations": total_observations,
                    "mean_reprojection_error": (total_error / total_points) if total_points > 0 else 0.0,
                    "mean_track_length": (total_track_length / total_points) if total_points > 0 else 0.0,
                }
        except Exception:
            pass
    
    if not recon_stats:
        try:
            # Prioritize block.output_colmap_path if set (e.g. for openMVG)
            if block.output_colmap_path and os.path.isdir(block.output_colmap_path):
                recon_stats = ResultReader.get_stats(block.output_colmap_path)
            else:
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
        "num_registered_images_unique": recon_stats.get("num_registered_images_unique", recon_stats.get("num_registered_images", 0)),
        "num_registered_images_sum": recon_stats.get("num_registered_images_sum", recon_stats.get("num_registered_images", 0)),
        "num_points3d": recon_stats.get("num_points3d", 0),
        "num_observations": recon_stats.get("num_observations", 0),
        "mean_reprojection_error": recon_stats.get("mean_reprojection_error", 0.0),
        "mean_track_length": recon_stats.get("mean_track_length", 0.0),
        "stage_times": block_stats.get("stage_times", {}),
        "algorithm_params": block_stats.get("algorithm_params", {}),
    }
    
    return ReconstructionStats(**merged)


@router.get("/{block_id}/result/points3d/ply")
async def download_points3d_ply(
    block_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Download points3D.ply file for the block.
    
    First tries to find existing points3D.ply file.
    If not found, generates it from points3D.bin.
    """
    result = await db.execute(select(Block).where(Block.id == block_id))
    block = result.scalar_one_or_none()
    
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block not found: {block_id}"
        )
    
    # For partitioned blocks, allow access if partitions are completed (even if not merged)
    if block.partition_enabled:
        if block.current_stage not in ("partitions_completed", "merging", "completed"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Partitions not completed yet"
            )
    elif block.status != BlockStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reconstruction not completed"
        )
    
    if not block.output_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No output path available"
        )
    
    # Find sparse directory
    # Prioritize block.output_colmap_path if set (e.g. for openMVG)
    if block.output_colmap_path and os.path.isdir(block.output_colmap_path):
        sparse_dir = block.output_colmap_path
    else:
        sparse_dir = ResultReader._find_sparse_dir(block.output_path)
    
    if not sparse_dir:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No sparse reconstruction found"
        )
    
    # First, try to find existing points3D.ply
    ply_path = os.path.join(sparse_dir, "points3D.ply")
    if os.path.exists(ply_path):
        return FileResponse(
            path=ply_path,
            filename="points3D.ply",
            media_type="application/octet-stream"
        )
    
    # If not found, generate from points3D.bin
    points_bin = os.path.join(sparse_dir, "points3D.bin")
    if not os.path.exists(points_bin):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="points3D.bin not found"
        )
    
    # Read all points from binary file and convert to PLY
    try:
        # Create temporary PLY file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ply', delete=False) as ply_file:
            ply_temp_path = ply_file.name
            
            # Read points from binary file
            points_data = []
            with open(points_bin, "rb") as f:
                num_points = struct.unpack("<Q", f.read(8))[0]
                
                for _ in range(num_points):
                    point_id = struct.unpack("<Q", f.read(8))[0]
                    x, y, z = struct.unpack("<3d", f.read(24))
                    r, g, b = struct.unpack("<3B", f.read(3))
                    error = struct.unpack("<d", f.read(8))[0]
                    track_length = struct.unpack("<Q", f.read(8))[0]
                    f.read(track_length * 8)  # Skip track data
                    
                    points_data.append((x, y, z, r, g, b))
            
            # Write PLY header
            ply_file.write("ply\n")
            ply_file.write("format ascii 1.0\n")
            ply_file.write(f"element vertex {len(points_data)}\n")
            ply_file.write("property float x\n")
            ply_file.write("property float y\n")
            ply_file.write("property float z\n")
            ply_file.write("property uchar red\n")
            ply_file.write("property uchar green\n")
            ply_file.write("property uchar blue\n")
            ply_file.write("end_header\n")
            
            # Write point data
            for x, y, z, r, g, b in points_data:
                ply_file.write(f"{x} {y} {z} {r} {g} {b}\n")
        
        # Return the temporary file
        # Note: We'll keep the temp file and let the OS clean it up later
        # For production, consider caching generated PLY files
        return FileResponse(
            path=ply_temp_path,
            filename="points3D.ply",
            media_type="application/octet-stream"
        )
        
    except Exception as e:
        # Clean up temp file on error
        if 'ply_temp_path' in locals() and os.path.exists(ply_temp_path):
            try:
                os.unlink(ply_temp_path)
            except:
                pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate PLY file: {str(e)}"
        )
