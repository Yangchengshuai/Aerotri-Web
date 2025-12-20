"""Partition management API endpoints."""
import os
import struct
import tempfile
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Block, BlockPartition, get_db
from ..schemas import (
    PartitionConfigRequest,
    PartitionConfigResponse,
    PartitionPreviewRequest,
    PartitionPreviewResponse,
    PartitionInfo,
)
from ..services.partition_service import PartitionService, PartitionDefinition

router = APIRouter()


@router.get("/{block_id}/partitions/config", response_model=PartitionConfigResponse)
async def get_partition_config(
    block_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get partition configuration for a block."""
    result = await db.execute(select(Block).where(Block.id == block_id))
    block = result.scalar_one_or_none()
    
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block not found: {block_id}"
        )
    
    partitions = await PartitionService.get_partitions(block_id, db)
    
    return PartitionConfigResponse(
        partition_enabled=block.partition_enabled,
        partition_strategy=block.partition_strategy,
        partition_params=block.partition_params,
        sfm_pipeline_mode=block.sfm_pipeline_mode,
        merge_strategy=block.merge_strategy,
        partitions=[
            PartitionInfo(
                id=p.id,
                index=p.index,
                name=p.name or f"P{p.index + 1}",
                image_start_name=p.image_start_name,
                image_end_name=p.image_end_name,
                image_count=p.image_count or 0,
                overlap_with_prev=p.overlap_with_prev or 0,
                overlap_with_next=p.overlap_with_next or 0,
                status=p.status,
                progress=p.progress,
                error_message=p.error_message,
            )
            for p in partitions
        ],
    )


@router.put("/{block_id}/partitions/config", response_model=PartitionConfigResponse)
async def update_partition_config(
    block_id: str,
    config: PartitionConfigRequest,
    db: AsyncSession = Depends(get_db)
):
    """Update partition configuration for a block."""
    result = await db.execute(select(Block).where(Block.id == block_id))
    block = result.scalar_one_or_none()
    
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block not found: {block_id}"
        )
    
    if block.status.value == "running":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update partition config while block is running"
        )
    
    # Update block partition settings
    block.partition_enabled = config.partition_enabled
    block.partition_strategy = config.partition_strategy if config.partition_enabled else None
    block.partition_params = config.partition_params if config.partition_enabled else None
    block.sfm_pipeline_mode = config.sfm_pipeline_mode if config.partition_enabled else None
    block.merge_strategy = config.merge_strategy if config.partition_enabled else None
    
    # If enabling partitions, build and save them
    if config.partition_enabled:
        partition_size = config.partition_params.get("partition_size", 1000)
        overlap = config.partition_params.get("overlap", 150)
        
        image_names = PartitionService.get_image_list(block)
        if not image_names:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No images found for this block"
            )
        
        partition_defs = PartitionService.build_partitions_by_name_with_overlap(
            image_names,
            partition_size=partition_size,
            overlap=overlap,
        )
        
        await PartitionService.save_partitions(
            block_id,
            partition_defs,
            partition_strategy=config.partition_strategy,
            partition_params=config.partition_params,
            sfm_pipeline_mode=config.sfm_pipeline_mode,
            merge_strategy=config.merge_strategy,
        )
    else:
        # Delete existing partitions
        existing = await PartitionService.get_partitions(block_id, db)
        for p in existing:
            await db.delete(p)
    
    await db.commit()
    
    # Return updated config
    partitions = await PartitionService.get_partitions(block_id, db)
    return PartitionConfigResponse(
        partition_enabled=block.partition_enabled,
        partition_strategy=block.partition_strategy,
        partition_params=block.partition_params,
        sfm_pipeline_mode=block.sfm_pipeline_mode,
        merge_strategy=block.merge_strategy,
        partitions=[
            PartitionInfo(
                id=p.id,
                index=p.index,
                name=p.name or f"P{p.index + 1}",
                image_start_name=p.image_start_name,
                image_end_name=p.image_end_name,
                image_count=p.image_count or 0,
                overlap_with_prev=p.overlap_with_prev or 0,
                overlap_with_next=p.overlap_with_next or 0,
                status=p.status,
                progress=p.progress,
                error_message=p.error_message,
            )
            for p in partitions
        ],
    )


@router.post("/{block_id}/partitions/preview", response_model=PartitionPreviewResponse)
async def preview_partitions(
    block_id: str,
    preview: PartitionPreviewRequest,
    db: AsyncSession = Depends(get_db)
):
    """Preview partitions without saving to database."""
    result = await db.execute(select(Block).where(Block.id == block_id))
    block = result.scalar_one_or_none()
    
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block not found: {block_id}"
        )
    
    try:
        partitions = await PartitionService.preview_partitions(
            block_id,
            partition_size=preview.partition_size,
            overlap=preview.overlap,
        )
        
        image_names = PartitionService.get_image_list(block)
        
        return PartitionPreviewResponse(
            partitions=[
                PartitionInfo(**p)
                for p in partitions
            ],
            total_images=len(image_names),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{block_id}/partitions/status", response_model=PartitionConfigResponse)
async def get_partition_status(
    block_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get partition status and statistics for a block."""
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
    
    from ..services.result_reader import ResultReader
    
    partitions = await PartitionService.get_partitions(block_id, db)
    
    # Get statistics for each partition
    partition_info_list = []
    dirty = False
    for p in sorted(partitions, key=lambda x: x.index):
        # A partition can be "available" even if DB status was reset (e.g. config saved again).
        # Use filesystem presence as source of truth for viewer/stats.
        partition_sparse = None
        has_sparse_output = False
        if block.output_path:
            partition_sparse = os.path.join(
                block.output_path,
                "partitions",
                f"partition_{p.index}",
                "sparse",
                "0",
            )
            if partition_sparse and os.path.isdir(partition_sparse):
                has_sparse_output = (
                    os.path.exists(os.path.join(partition_sparse, "images.bin"))
                    or os.path.exists(os.path.join(partition_sparse, "images.txt"))
                )

        partition_info = PartitionInfo(
            id=p.id,
            index=p.index,
            name=p.name or f"P{p.index + 1}",
            image_start_name=p.image_start_name,
            image_end_name=p.image_end_name,
            image_count=p.image_count or 0,
            overlap_with_prev=p.overlap_with_prev or 0,
            overlap_with_next=p.overlap_with_next or 0,
            status=p.status,
            progress=p.progress,
            error_message=p.error_message,
        )

        # If output exists but DB status isn't completed, expose it as completed and optionally fix DB.
        if has_sparse_output and p.status != "COMPLETED":
            partition_info.status = "COMPLETED"
            partition_info.progress = 100.0
            try:
                p.status = "COMPLETED"
                p.progress = 100.0
                dirty = True
            except Exception:
                pass
        
        # Try to read partition statistics if available
        partition_stats = {}
        if block.output_path and has_sparse_output:
            try:
                stats = ResultReader.read_partition_stats(block.output_path, p.index)
                if stats:
                    partition_stats = {
                        "num_registered_images": stats.get("num_registered_images", 0),
                        "num_points3d": stats.get("num_points3d", 0),
                        "num_observations": stats.get("num_observations", 0),
                        "mean_reprojection_error": stats.get("mean_reprojection_error", 0.0),
                        "mean_track_length": stats.get("mean_track_length", 0.0),
                    }
            except Exception:
                pass  # Ignore errors reading stats
        
        # Add statistics to partition info
        if partition_stats:
            partition_info.statistics = partition_stats
        
        partition_info_list.append(partition_info)

    # Persist any recovered statuses (best-effort)
    if dirty:
        try:
            await db.commit()
        except Exception:
            pass
    
    return PartitionConfigResponse(
        partition_enabled=block.partition_enabled,
        partition_strategy=block.partition_strategy,
        partition_params=block.partition_params,
        sfm_pipeline_mode=block.sfm_pipeline_mode,
        merge_strategy=block.merge_strategy,
        partitions=partition_info_list,
    )


@router.get("/{block_id}/partitions/{partition_index}/result/cameras")
async def get_partition_cameras(
    block_id: str,
    partition_index: int,
    db: AsyncSession = Depends(get_db)
):
    """Get camera poses from a specific partition."""
    from ..services.result_reader import ResultReader
    
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
    
    if not block.output_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No output path available"
        )
    
    # Verify partition exists
    partitions = await PartitionService.get_partitions(block_id, db)
    partition = next((p for p in partitions if p.index == partition_index), None)
    if not partition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Partition {partition_index} not found"
        )
    
    try:
        cameras = ResultReader.read_partition_cameras(block.output_path, partition_index)
        return cameras
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read partition cameras: {str(e)}"
        )


@router.get("/{block_id}/partitions/{partition_index}/result/points")
async def get_partition_points(
    block_id: str,
    partition_index: int,
    limit: int = 100000,
    db: AsyncSession = Depends(get_db)
):
    """Get 3D points from a specific partition."""
    from ..services.result_reader import ResultReader
    
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
    
    if not block.output_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No output path available"
        )
    
    # Verify partition exists
    partitions = await PartitionService.get_partitions(block_id, db)
    partition = next((p for p in partitions if p.index == partition_index), None)
    if not partition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Partition {partition_index} not found"
        )
    
    try:
        points, total = ResultReader.read_partition_points3d(block.output_path, partition_index, limit)
        return {"points": points, "total": total}
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read partition points: {str(e)}"
        )


@router.get("/{block_id}/partitions/{partition_index}/result/stats")
async def get_partition_stats(
    block_id: str,
    partition_index: int,
    db: AsyncSession = Depends(get_db)
):
    """Get reconstruction statistics for a specific partition."""
    from ..services.result_reader import ResultReader
    from ..schemas import ReconstructionStats
    
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
    
    if not block.output_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No output path available"
        )
    
    # Verify partition exists
    partitions = await PartitionService.get_partitions(block_id, db)
    partition = next((p for p in partitions if p.index == partition_index), None)
    if not partition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Partition {partition_index} not found"
        )
    
    # Read partition statistics
    try:
        recon_stats = ResultReader.read_partition_stats(block.output_path, partition_index)
    except Exception:
        recon_stats = {}
    
    # Count total images for this partition
    num_images = partition.image_count or 0
    
    # Merge with partition statistics if available
    partition_stats = partition.statistics or {}
    
    merged = {
        "num_images": num_images,
        "num_registered_images": recon_stats.get("num_registered_images", 0),
        "num_registered_images_unique": recon_stats.get("num_registered_images", 0),
        "num_registered_images_sum": recon_stats.get("num_registered_images", 0),
        "num_points3d": recon_stats.get("num_points3d", 0),
        "num_observations": recon_stats.get("num_observations", 0),
        "mean_reprojection_error": recon_stats.get("mean_reprojection_error", 0.0),
        "mean_track_length": recon_stats.get("mean_track_length", 0.0),
        "stage_times": partition_stats.get("stage_times", {}),
        "algorithm_params": partition_stats.get("algorithm_params", {}),
    }
    
    return ReconstructionStats(**merged)


@router.get("/{block_id}/partitions/{partition_index}/result/points3d/ply")
async def download_partition_points3d_ply(
    block_id: str,
    partition_index: int,
    db: AsyncSession = Depends(get_db),
):
    """Download points3D.ply for a specific partition.

    If points3D.ply does not exist, generate it from points3D.bin or points3D.txt.
    """
    from fastapi.responses import FileResponse
    from ..services.result_reader import ResultReader

    result = await db.execute(select(Block).where(Block.id == block_id))
    block = result.scalar_one_or_none()

    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block not found: {block_id}",
        )

    if not block.partition_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Block is not in partitioned mode",
        )

    if not block.output_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No output path available",
        )

    # Verify partition exists
    partitions = await PartitionService.get_partitions(block_id, db)
    partition = next((p for p in partitions if p.index == partition_index), None)
    if not partition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Partition {partition_index} not found",
        )

    partition_sparse = os.path.join(
        block.output_path,
        "partitions",
        f"partition_{partition_index}",
        "sparse",
        "0",
    )
    if not os.path.exists(partition_sparse):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Partition {partition_index} sparse directory not found",
        )

    ply_path = os.path.join(partition_sparse, "points3D.ply")
    if os.path.exists(ply_path):
        return FileResponse(
            path=ply_path,
            filename=f"points3D_partition_{partition_index}.ply",
            media_type="application/octet-stream",
        )

    points_bin = os.path.join(partition_sparse, "points3D.bin")
    points_txt = os.path.join(partition_sparse, "points3D.txt")
    if not os.path.exists(points_bin) and not os.path.exists(points_txt):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="points3D.bin/points3D.txt not found",
        )

    # Generate temporary PLY
    ply_temp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ply", delete=False) as ply_file:
            ply_temp_path = ply_file.name

            if os.path.exists(points_bin):
                # Read points from binary file and convert to PLY
                points_data = []
                with open(points_bin, "rb") as f:
                    num_points = struct.unpack("<Q", f.read(8))[0]
                    for _ in range(num_points):
                        _point_id = struct.unpack("<Q", f.read(8))[0]
                        x, y, z = struct.unpack("<3d", f.read(24))
                        r, g, b = struct.unpack("<3B", f.read(3))
                        _error = struct.unpack("<d", f.read(8))[0]
                        track_length = struct.unpack("<Q", f.read(8))[0]
                        f.read(track_length * 8)
                        points_data.append((x, y, z, r, g, b))
            else:
                # Read points from text file
                points_data = []
                with open(points_txt, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        parts = line.split()
                        if len(parts) < 7:
                            continue
                        try:
                            x = float(parts[1])
                            y = float(parts[2])
                            z = float(parts[3])
                            r = int(parts[4])
                            g = int(parts[5])
                            b = int(parts[6])
                        except Exception:
                            continue
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
            for x, y, z, r, g, b in points_data:
                ply_file.write(f"{x} {y} {z} {r} {g} {b}\n")

        return FileResponse(
            path=ply_temp_path,
            filename=f"points3D_partition_{partition_index}.ply",
            media_type="application/octet-stream",
        )
    except Exception as e:
        if ply_temp_path and os.path.exists(ply_temp_path):
            try:
                os.unlink(ply_temp_path)
            except Exception:
                pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate partition PLY file: {str(e)}",
        )

