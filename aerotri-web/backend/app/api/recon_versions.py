"""Reconstruction version management API endpoints."""

import os
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Block, BlockStatus, get_db, ReconVersion, ReconVersionStatus
from ..schemas import (
    ReconVersionCreate,
    ReconVersionResponse,
    ReconVersionListResponse,
    ReconVersionFilesResponse,
    ReconstructionFileInfo,
)
from ..services.openmvs_runner import openmvs_runner, QUALITY_PRESETS
from ..conf.settings import get_settings


_settings = get_settings()
router = APIRouter()


def _version_to_response(version: ReconVersion) -> ReconVersionResponse:
    """Convert ReconVersion model to response schema."""
    return ReconVersionResponse(
        id=version.id,
        block_id=version.block_id,
        version_index=version.version_index,
        name=version.name,
        quality_preset=version.quality_preset,
        custom_params=version.custom_params,
        merged_params=version.merged_params,
        status=version.status,
        progress=version.progress,
        current_stage=version.current_stage,
        output_path=version.output_path,
        error_message=version.error_message,
        statistics=version.statistics,
        created_at=version.created_at.isoformat() if version.created_at else None,
        completed_at=version.completed_at.isoformat() if version.completed_at else None,
        # 3D Tiles fields
        tiles_status=version.tiles_status,
        tiles_progress=version.tiles_progress,
        tiles_current_stage=version.tiles_current_stage,
        tiles_output_path=version.tiles_output_path,
        tiles_error_message=version.tiles_error_message,
        tiles_statistics=version.tiles_statistics,
    )


@router.get(
    "/blocks/{block_id}/recon-versions",
    response_model=ReconVersionListResponse,
)
async def list_recon_versions(
    block_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List all reconstruction versions for a block."""
    # Verify block exists
    result = await db.execute(select(Block).where(Block.id == block_id))
    block = result.scalar_one_or_none()
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block not found: {block_id}",
        )
    
    # Get all versions for this block
    result = await db.execute(
        select(ReconVersion)
        .where(ReconVersion.block_id == block_id)
        .order_by(ReconVersion.version_index.desc())
    )
    versions = result.scalars().all()
    
    return ReconVersionListResponse(
        versions=[_version_to_response(v) for v in versions],
        total=len(versions),
    )


@router.post(
    "/blocks/{block_id}/recon-versions",
    response_model=ReconVersionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_recon_version(
    block_id: str,
    payload: ReconVersionCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new reconstruction version and start reconstruction.
    
    This creates a new version with the specified parameters and starts
    the OpenMVS reconstruction pipeline in the background.
    """
    # Verify block exists and is completed
    result = await db.execute(select(Block).where(Block.id == block_id))
    block = result.scalar_one_or_none()
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block not found: {block_id}",
        )
    
    if block.status != BlockStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reconstruction can only be started when SfM has completed.",
        )
    
    # Check if there's already a running reconstruction for this block
    result = await db.execute(
        select(ReconVersion)
        .where(ReconVersion.block_id == block_id)
        .where(ReconVersion.status == ReconVersionStatus.RUNNING.value)
    )
    running_version = result.scalar_one_or_none()
    if running_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A reconstruction is already running (version {running_version.version_index}). Please wait or cancel it first.",
        )
    
    # Get next version index
    result = await db.execute(
        select(func.max(ReconVersion.version_index))
        .where(ReconVersion.block_id == block_id)
    )
    max_index = result.scalar() or 0
    next_index = max_index + 1
    
    # Generate version name if not provided
    preset = payload.quality_preset or "balanced"
    if payload.name:
        version_name = payload.name
    else:
        version_name = f"v{next_index} - {preset}"
    
    # Convert custom_params to dict if provided
    custom_params_dict = None
    if payload.custom_params:
        custom_params_dict = {}
        if payload.custom_params.densify:
            custom_params_dict["densify"] = payload.custom_params.densify.model_dump(exclude_none=True)
        if payload.custom_params.mesh:
            custom_params_dict["mesh"] = payload.custom_params.mesh.model_dump(exclude_none=True)
        if payload.custom_params.refine:
            custom_params_dict["refine"] = payload.custom_params.refine.model_dump(exclude_none=True)
        if payload.custom_params.texture:
            custom_params_dict["texture"] = payload.custom_params.texture.model_dump(exclude_none=True)
    
    # Create version record
    version = ReconVersion(
        block_id=block_id,
        version_index=next_index,
        name=version_name,
        quality_preset=preset,
        custom_params=custom_params_dict,
        status=ReconVersionStatus.PENDING.value,
        progress=0.0,
    )
    db.add(version)
    await db.commit()
    await db.refresh(version)

    # Start reconstruction in background
    # Use configured default GPU device
    gpu_index = _settings.gpu.default_device

    await openmvs_runner.start_reconstruction_version(
        block=block,
        version=version,
        gpu_index=gpu_index,
        db=db,
    )
    
    # Refresh to get updated status
    await db.refresh(version)
    
    return _version_to_response(version)


@router.get(
    "/blocks/{block_id}/recon-versions/{version_id}",
    response_model=ReconVersionResponse,
)
async def get_recon_version(
    block_id: str,
    version_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific reconstruction version."""
    result = await db.execute(
        select(ReconVersion)
        .where(ReconVersion.id == version_id)
        .where(ReconVersion.block_id == block_id)
    )
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version not found: {version_id}",
        )
    
    return _version_to_response(version)


@router.delete(
    "/blocks/{block_id}/recon-versions/{version_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_recon_version(
    block_id: str,
    version_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a reconstruction version.
    
    This will also delete the output files on disk.
    Cannot delete a version that is currently running.
    """
    result = await db.execute(
        select(ReconVersion)
        .where(ReconVersion.id == version_id)
        .where(ReconVersion.block_id == block_id)
    )
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version not found: {version_id}",
        )
    
    if version.status == ReconVersionStatus.RUNNING.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete a running reconstruction. Cancel it first.",
        )
    
    # Delete output directory if it exists
    if version.output_path and os.path.exists(version.output_path):
        import shutil
        try:
            shutil.rmtree(version.output_path)
        except Exception as e:
            # Log but don't fail - DB record deletion is more important
            print(f"Warning: Failed to delete output directory {version.output_path}: {e}")
    
    # Delete from database
    await db.delete(version)
    await db.commit()


@router.post(
    "/blocks/{block_id}/recon-versions/{version_id}/cancel",
    response_model=ReconVersionResponse,
)
async def cancel_recon_version(
    block_id: str,
    version_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Cancel a running reconstruction version."""
    result = await db.execute(
        select(ReconVersion)
        .where(ReconVersion.id == version_id)
        .where(ReconVersion.block_id == block_id)
    )
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version not found: {version_id}",
        )
    
    if version.status != ReconVersionStatus.RUNNING.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Can only cancel a running reconstruction.",
        )
    
    # Cancel via runner
    await openmvs_runner.cancel_reconstruction_version(version.id)
    
    # Refresh to get updated status
    await db.refresh(version)
    
    return _version_to_response(version)


@router.get(
    "/blocks/{block_id}/recon-versions/{version_id}/files",
    response_model=ReconVersionFilesResponse,
)
async def list_recon_version_files(
    block_id: str,
    version_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List output files for a reconstruction version."""
    result = await db.execute(
        select(ReconVersion)
        .where(ReconVersion.id == version_id)
        .where(ReconVersion.block_id == block_id)
    )
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version not found: {version_id}",
        )
    
    files: List[ReconstructionFileInfo] = []
    
    if not version.output_path or not os.path.exists(version.output_path):
        return ReconVersionFilesResponse(version_id=version_id, files=[])
    
    root = Path(version.output_path)
    
    # Define expected primary output files per stage
    primary_files = {
        "dense": ["scene_dense.ply"],
        "mesh": ["scene_dense_mesh.ply"],
        "refine": ["scene_dense_refine.ply", "scene_dense_mesh_refine.ply"],
        "texture": ["scene_dense_texture.obj", "scene_dense_mesh_refine_texture.obj"],
    }
    
    for stage_dir in ["dense", "mesh", "refine", "texture"]:
        dir_path = root / stage_dir
        if not dir_path.exists() or not dir_path.is_dir():
            continue
        
        primary_names = primary_files.get(stage_dir, [])
        if not primary_names:
            continue
        
        # Look for the primary file
        for name in primary_names:
            candidate = dir_path / name
            if candidate.is_file():
                suffix = candidate.suffix.lower()
                if stage_dir == "dense":
                    ftype = "point_cloud"
                elif stage_dir in ["mesh", "refine"]:
                    ftype = "mesh"
                else:
                    ftype = "texture"
                
                preview_supported = suffix in {".ply", ".obj"}
                stat = candidate.stat()
                files.append(
                    ReconstructionFileInfo(
                        stage=stage_dir,
                        type=ftype,
                        name=name,
                        size_bytes=stat.st_size,
                        mtime=datetime.fromtimestamp(stat.st_mtime),
                        preview_supported=preview_supported,
                        download_url=f"/api/blocks/{block_id}/recon-versions/{version_id}/download?file={stage_dir}/{name}",
                    )
                )
                break
    
    return ReconVersionFilesResponse(version_id=version_id, files=files)


@router.get("/blocks/{block_id}/recon-versions/{version_id}/download")
async def download_recon_version_file(
    block_id: str,
    version_id: str,
    file: str = Query(..., description="Relative path under version output root"),
    db: AsyncSession = Depends(get_db),
):
    """Download a file from a reconstruction version."""
    result = await db.execute(
        select(ReconVersion)
        .where(ReconVersion.id == version_id)
        .where(ReconVersion.block_id == block_id)
    )
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version not found: {version_id}",
        )
    
    if not version.output_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version has no output path.",
        )
    
    root = Path(version.output_path).resolve()
    requested = (root / file).resolve()
    
    # Prevent directory traversal
    if not str(requested).startswith(str(root)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file path.",
        )
    
    if not requested.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {file}",
        )
    
    return FileResponse(path=str(requested), filename=requested.name)


@router.get(
    "/blocks/{block_id}/recon-versions/{version_id}/log_tail",
)
async def get_recon_version_log_tail(
    block_id: str,
    version_id: str,
    lines: int = Query(200, ge=1, le=2000),
    db: AsyncSession = Depends(get_db),
):
    """Get the last N lines of reconstruction logs for a version."""
    result = await db.execute(
        select(ReconVersion)
        .where(ReconVersion.id == version_id)
        .where(ReconVersion.block_id == block_id)
    )
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version not found: {version_id}",
        )
    
    log_lines = openmvs_runner.get_version_log_tail(version_id, lines) or []
    return {"version_id": version_id, "lines": log_lines}


# ==================== Texture File Static Serving ====================
# These endpoints serve texture files directly with path-based URLs,
# enabling Three.js to correctly resolve relative paths for MTL and texture images.


@router.get("/blocks/{block_id}/recon-versions/{version_id}/texture/{filename:path}")
async def serve_texture_file(
    block_id: str,
    version_id: str,
    filename: str,
    db: AsyncSession = Depends(get_db),
):
    """Serve texture files directly with path-based URL.
    
    This endpoint allows Three.js OBJLoader/MTLLoader to correctly resolve
    relative paths for textures. For example:
    - OBJ file: /api/blocks/{id}/recon-versions/{vid}/texture/scene_dense_texture.obj
    - MTL file: /api/blocks/{id}/recon-versions/{vid}/texture/scene_dense_texture.mtl
    - Texture:  /api/blocks/{id}/recon-versions/{vid}/texture/scene_dense_texture_material_00_map_Kd.jpg
    
    MTL files reference textures with relative paths like "scene_dense_texture_material_00_map_Kd.jpg",
    and Three.js will resolve them relative to the MTL file's URL base path.
    """
    result = await db.execute(
        select(ReconVersion)
        .where(ReconVersion.id == version_id)
        .where(ReconVersion.block_id == block_id)
    )
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version not found: {version_id}",
        )
    
    if not version.output_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version has no output path.",
        )
    
    # Build the full path to the texture file
    root = Path(version.output_path).resolve()
    texture_dir = root / "texture"
    requested = (texture_dir / filename).resolve()
    
    # Security: prevent directory traversal
    if not str(requested).startswith(str(texture_dir)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file path.",
        )
    
    if not requested.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Texture file not found: {filename}",
        )
    
    # Determine content type based on file extension
    suffix = requested.suffix.lower()
    content_type_map = {
        ".obj": "text/plain",
        ".mtl": "text/plain",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".tif": "image/tiff",
        ".tiff": "image/tiff",
    }
    content_type = content_type_map.get(suffix, "application/octet-stream")
    
    return FileResponse(
        path=str(requested),
        filename=requested.name,
        media_type=content_type,
    )
