"""Reconstruction (OpenMVS) related API endpoints."""

import os
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Block, BlockStatus, get_db
from ..schemas import (
    ReconstructRequest,
    ReconstructionFilesResponse,
    ReconstructionFileInfo,
    ReconstructionStatusResponse,
    ReconstructionLogResponse,
)
from ..services.openmvs_runner import openmvs_runner


router = APIRouter()


@router.post(
    "/blocks/{block_id}/reconstruct",
    response_model=ReconstructionStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_reconstruct(
    block_id: str,
    payload: ReconstructRequest,
    db: AsyncSession = Depends(get_db),
):
    """Trigger reconstruction (OpenMVS) for a completed Block."""
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

    if block.recon_status == "RUNNING":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Reconstruction is already running for this block.",
        )

    # Default to CUDA device 7 for OpenMVS reconstruction; can be extended to reuse SfM GPU config.
    gpu_index = 7

    await openmvs_runner.start_reconstruction(
        block=block,
        gpu_index=gpu_index,
        db=db,
        quality_preset=payload.quality_preset,
    )

    return ReconstructionStatusResponse(
        block_id=block.id,
        recon_status=block.recon_status,
        recon_progress=block.recon_progress,
        recon_current_stage=block.recon_current_stage,
        recon_output_path=block.recon_output_path,
        recon_error_message=block.recon_error_message,
        recon_statistics=block.recon_statistics,
    )


@router.post(
    "/blocks/{block_id}/reconstruction/cancel",
    response_model=ReconstructionStatusResponse,
)
async def cancel_reconstruction(
    block_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Cancel a running reconstruction task."""
    result = await db.execute(select(Block).where(Block.id == block_id))
    block = result.scalar_one_or_none()
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block not found: {block_id}",
        )

    if block.recon_status != "RUNNING":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Reconstruction is not running for this block.",
        )

    await openmvs_runner.cancel_reconstruction(block_id)

    # Refresh block state after cancellation
    await db.refresh(block)

    return ReconstructionStatusResponse(
        block_id=block.id,
        recon_status=block.recon_status,
        recon_progress=block.recon_progress,
        recon_current_stage=block.recon_current_stage,
        recon_output_path=block.recon_output_path,
        recon_error_message=block.recon_error_message,
        recon_statistics=block.recon_statistics,
    )


@router.get(
    "/blocks/{block_id}/reconstruction/status",
    response_model=ReconstructionStatusResponse,
)
async def get_reconstruction_status(
    block_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get reconstruction status for a block."""
    result = await db.execute(select(Block).where(Block.id == block_id))
    block = result.scalar_one_or_none()
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block not found: {block_id}",
        )

    return ReconstructionStatusResponse(
        block_id=block.id,
        recon_status=block.recon_status,
        recon_progress=block.recon_progress,
        recon_current_stage=block.recon_current_stage,
        recon_output_path=block.recon_output_path,
        recon_error_message=block.recon_error_message,
        recon_statistics=block.recon_statistics,
    )


def _collect_recon_files(root: Path) -> List[ReconstructionFileInfo]:
    """Collect reconstruction output files, matching expected filenames per stage.
    
    Expected files:
    - dense: scene_dense.ply (in dense/ directory)
    - mesh: scene_dense_mesh.ply (in mesh/ directory)
    - refine: scene_dense_mesh_refine.ply (in refine/ directory)
    - texture: scene_dense_texture.obj + .mtl + .png (in texture/ directory)
    
    Note: We match the primary output file for each stage (the one that should be
    displayed and downloadable). For texture stage, we also include .mtl and texture images.
    """
    files: List[ReconstructionFileInfo] = []
    if not root.exists():
        return files

    # Define expected primary output files per stage
    # These are the main files that should be shown in the UI
    # For texture, OpenMVS may output scene_dense_texture.obj or scene_dense_mesh_refine_texture.obj
    # We'll check for both patterns
    primary_files = {
        "dense": ["scene_dense.ply"],
        "mesh": ["scene_dense_mesh.ply"],
        "refine": ["scene_dense_refine.ply", "scene_dense_mesh_refine.ply"],  # 支持两种命名
        "texture": ["scene_dense_texture.obj", "scene_dense_mesh_refine_texture.obj"],
    }

    for stage_dir in ["dense", "mesh", "refine", "texture"]:
        dir_path = root / stage_dir
        if not dir_path.exists() or not dir_path.is_dir():
            continue

        primary_names = primary_files.get(stage_dir, [])
        if not primary_names:
            continue

        # Look for the primary file (try all possible names)
        primary_path = None
        primary_name = None
        for name in primary_names:
            candidate = dir_path / name
            if candidate.is_file():
                primary_path = candidate
                primary_name = name
                break

        if primary_path and primary_path.is_file():
            suffix = primary_path.suffix.lower()
            if stage_dir == "dense":
                ftype = "point_cloud"
            elif stage_dir in ["mesh", "refine"]:
                ftype = "mesh"
            else:  # texture
                ftype = "texture"

            preview_supported = suffix in {".ply", ".obj"}
            stat = primary_path.stat()
            files.append(
                ReconstructionFileInfo(
                    stage=stage_dir,
                    type=ftype,
                    name=primary_name,
                    size_bytes=stat.st_size,
                    mtime=datetime.fromtimestamp(stat.st_mtime),
                    preview_supported=preview_supported,
                    download_url=f"/api/blocks/{{block_id}}/reconstruction/download?file={stage_dir}/{primary_name}",
                )
            )

        # For texture stage, also collect .mtl and texture image files (for completeness,
        # though they won't be shown as separate cards in the UI)
        if stage_dir == "texture":
            for entry in dir_path.iterdir():
                if not entry.is_file() or entry.name == primary_name:
                    continue
                name_lower = entry.name.lower()
                # Include .mtl and texture material images (match both naming patterns)
                if (
                    name_lower in ["scene_dense_texture.mtl", "scene_dense_mesh_refine_texture.mtl"]
                    or (
                        (
                            name_lower.startswith("scene_dense_texture_material_")
                            or name_lower.startswith("scene_dense_mesh_refine_texture_material_")
                        )
                        and name_lower.endswith((".png", ".jpg", ".jpeg"))
                    )
                ):
                    # These are auxiliary files, we can include them but they won't be
                    # the primary file shown in the stage card
                    suffix = entry.suffix.lower()
                    ftype = "texture"
                    preview_supported = False  # Only .obj is previewable
                    stat = entry.stat()
                    files.append(
                        ReconstructionFileInfo(
                            stage="texture",
                            type=ftype,
                            name=entry.name,
                            size_bytes=stat.st_size,
                            mtime=datetime.fromtimestamp(stat.st_mtime),
                            preview_supported=preview_supported,
                            download_url=f"/api/blocks/{{block_id}}/reconstruction/download?file={stage_dir}/{entry.name}",
                        )
                    )

    return files


@router.get(
    "/blocks/{block_id}/reconstruction/files",
    response_model=ReconstructionFilesResponse,
)
async def list_reconstruction_files(
    block_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List reconstruction output files for a block."""
    result = await db.execute(select(Block).where(Block.id == block_id))
    block = result.scalar_one_or_none()
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block not found: {block_id}",
        )

    if not block.recon_output_path:
        return ReconstructionFilesResponse(files=[])

    root = Path(block.recon_output_path)
    files = _collect_recon_files(root)
    # Fix download_url now that we know the concrete block_id
    for f in files:
        f.download_url = f"/api/blocks/{block_id}/reconstruction/download?file={f.stage}/{f.name}"
    return ReconstructionFilesResponse(files=files)


@router.get("/blocks/{block_id}/reconstruction/download")
async def download_reconstruction_file(
    block_id: str,
    file: str = Query(..., description="Relative path under reconstruction root"),
    db: AsyncSession = Depends(get_db),
):
    """Download a reconstruction output file."""
    result = await db.execute(select(Block).where(Block.id == block_id))
    block = result.scalar_one_or_none()
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block not found: {block_id}",
        )

    if not block.recon_output_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reconstruction output not found for this block.",
        )

    root = Path(block.recon_output_path).resolve()
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
    "/blocks/{block_id}/reconstruction/log_tail",
    response_model=ReconstructionLogResponse,
)
async def get_reconstruction_log_tail(
    block_id: str,
    lines: int = Query(200, ge=1, le=2000),
    db: AsyncSession = Depends(get_db),
):
    """Get the last N lines of reconstruction logs for a block."""
    result = await db.execute(select(Block).where(Block.id == block_id))
    block = result.scalar_one_or_none()
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block not found: {block_id}",
        )

    log_lines = openmvs_runner.get_log_tail(block_id, lines) or []
    return ReconstructionLogResponse(block_id=block_id, lines=log_lines)


