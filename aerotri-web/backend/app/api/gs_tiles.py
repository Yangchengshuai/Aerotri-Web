"""3D GS Tiles conversion related API endpoints."""

import os
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Block, BlockStatus, get_db
from ..schemas import (
    GSTilesConvertRequest,
    GSTilesFilesResponse,
    GSTilesFileInfo,
    GSTilesStatusResponse,
    GSTilesLogResponse,
    GSTilesetUrlResponse,
)
from ..services.gs_tiles_runner import gs_tiles_runner


router = APIRouter()


@router.post(
    "/blocks/{block_id}/gs/tiles/convert",
    response_model=GSTilesStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_gs_tiles_conversion(
    block_id: str,
    payload: GSTilesConvertRequest,
    db: AsyncSession = Depends(get_db),
):
    """Trigger 3D GS PLY to 3D Tiles conversion for a completed 3DGS training."""
    result = await db.execute(select(Block).where(Block.id == block_id))
    block = result.scalar_one_or_none()
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block not found: {block_id}",
        )

    # Check if 3DGS training is completed
    if not block.gs_output_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="3DGS training must be completed before converting to 3D Tiles.",
        )

    # Use getattr for backward compatibility
    current_status = getattr(block, 'gs_tiles_status', None)
    if current_status == "RUNNING":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="3D GS Tiles conversion is already running for this block.",
        )

    convert_params = {
        "iteration": payload.iteration,
        "use_spz": payload.use_spz or False,
        "optimize": payload.optimize or False,
    }

    await gs_tiles_runner.start_conversion(
        block=block,
        db=db,
        convert_params=convert_params,
    )

    return GSTilesStatusResponse(
        block_id=block.id,
        gs_tiles_status=getattr(block, 'gs_tiles_status', None),
        gs_tiles_progress=getattr(block, 'gs_tiles_progress', None),
        gs_tiles_current_stage=getattr(block, 'gs_tiles_current_stage', None),
        gs_tiles_output_path=getattr(block, 'gs_tiles_output_path', None),
        gs_tiles_error_message=getattr(block, 'gs_tiles_error_message', None),
        gs_tiles_statistics=getattr(block, 'gs_tiles_statistics', None),
    )


@router.post(
    "/blocks/{block_id}/gs/tiles/cancel",
    response_model=GSTilesStatusResponse,
)
async def cancel_gs_tiles_conversion(
    block_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Cancel a running 3D GS Tiles conversion task."""
    result = await db.execute(select(Block).where(Block.id == block_id))
    block = result.scalar_one_or_none()
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block not found: {block_id}",
        )

    current_status = getattr(block, 'gs_tiles_status', None)
    if current_status != "RUNNING":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="3D GS Tiles conversion is not running for this block.",
        )

    await gs_tiles_runner.cancel_conversion(block_id)

    # Refresh block state after cancellation
    await db.refresh(block)

    return GSTilesStatusResponse(
        block_id=block.id,
        gs_tiles_status=getattr(block, 'gs_tiles_status', None),
        gs_tiles_progress=getattr(block, 'gs_tiles_progress', None),
        gs_tiles_current_stage=getattr(block, 'gs_tiles_current_stage', None),
        gs_tiles_output_path=getattr(block, 'gs_tiles_output_path', None),
        gs_tiles_error_message=getattr(block, 'gs_tiles_error_message', None),
        gs_tiles_statistics=getattr(block, 'gs_tiles_statistics', None),
    )


@router.get(
    "/blocks/{block_id}/gs/tiles/status",
    response_model=GSTilesStatusResponse,
)
async def get_gs_tiles_status(
    block_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get 3D GS Tiles conversion status for a block."""
    result = await db.execute(select(Block).where(Block.id == block_id))
    block = result.scalar_one_or_none()
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block not found: {block_id}",
        )

    return GSTilesStatusResponse(
        block_id=block.id,
        gs_tiles_status=getattr(block, 'gs_tiles_status', None),
        gs_tiles_progress=getattr(block, 'gs_tiles_progress', None),
        gs_tiles_current_stage=getattr(block, 'gs_tiles_current_stage', None),
        gs_tiles_output_path=getattr(block, 'gs_tiles_output_path', None),
        gs_tiles_error_message=getattr(block, 'gs_tiles_error_message', None),
        gs_tiles_statistics=getattr(block, 'gs_tiles_statistics', None),
    )


def _collect_gs_tiles_files(root: Path) -> List[GSTilesFileInfo]:
    """Collect 3D GS Tiles output files."""
    files: List[GSTilesFileInfo] = []
    if not root.exists():
        return files

    # Look for tileset.json
    tileset_path = root / "tileset.json"
    if tileset_path.exists() and tileset_path.is_file():
        stat = tileset_path.stat()
        files.append(
            GSTilesFileInfo(
                name="tileset.json",
                type="tileset",
                size_bytes=stat.st_size,
                mtime=datetime.fromtimestamp(stat.st_mtime),
                preview_supported=True,
                download_url=f"/api/blocks/{{block_id}}/gs/tiles/download?file=tileset.json",
            )
        )

    # Look for b3dm files
    for b3dm_path in root.glob("*.b3dm"):
        stat = b3dm_path.stat()
        files.append(
            GSTilesFileInfo(
                name=b3dm_path.name,
                type="tile",
                size_bytes=stat.st_size,
                mtime=datetime.fromtimestamp(stat.st_mtime),
                preview_supported=False,
                download_url=f"/api/blocks/{{block_id}}/gs/tiles/download?file={b3dm_path.name}",
            )
        )

    # Look for GLB file (if kept)
    glb_path = root / "model.glb"
    if glb_path.exists() and glb_path.is_file():
        stat = glb_path.stat()
        files.append(
            GSTilesFileInfo(
                name="model.glb",
                type="glb",
                size_bytes=stat.st_size,
                mtime=datetime.fromtimestamp(stat.st_mtime),
                preview_supported=False,
                download_url=f"/api/blocks/{{block_id}}/gs/tiles/download?file=model.glb",
            )
        )

    return files


@router.get(
    "/blocks/{block_id}/gs/tiles/files",
    response_model=GSTilesFilesResponse,
)
async def list_gs_tiles_files(
    block_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List 3D GS Tiles output files for a block."""
    result = await db.execute(select(Block).where(Block.id == block_id))
    block = result.scalar_one_or_none()
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block not found: {block_id}",
        )

    gs_tiles_output_path = getattr(block, 'gs_tiles_output_path', None)
    if not gs_tiles_output_path:
        return GSTilesFilesResponse(files=[])

    root = Path(gs_tiles_output_path)
    files = _collect_gs_tiles_files(root)
    # Fix download_url now that we know the concrete block_id
    for f in files:
        f.download_url = f"/api/blocks/{block_id}/gs/tiles/download?file={f.name}"
    return GSTilesFilesResponse(files=files)


@router.get("/blocks/{block_id}/gs/tiles/download")
@router.options("/blocks/{block_id}/gs/tiles/download")
async def download_gs_tiles_file(
    block_id: str,
    request: Request,
    file: str = Query(..., description="Relative path under gs tiles output root"),
    db: AsyncSession = Depends(get_db),
):
    """Download a 3D GS Tiles output file."""
    
    result = await db.execute(select(Block).where(Block.id == block_id))
    block = result.scalar_one_or_none()
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block not found: {block_id}",
        )

    if not block.gs_tiles_output_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="3D GS Tiles output not found for this block.",
        )

    root = Path(block.gs_tiles_output_path).resolve()
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

    # Special handling for tileset.json: modify relative URIs to absolute URLs
    if file == "tileset.json":
        import json
        with open(requested, "r", encoding="utf-8") as f:
            tileset_data = json.load(f)
        
        def fix_uri(uri: str) -> str:
            if not uri:
                return uri
            if uri.startswith("http://localhost:8000") or uri.startswith("https://localhost:8000"):
                if "/api/" in uri:
                    return "/api/" + uri.split("/api/", 1)[1]
                return uri
            if uri.startswith("/"):
                return uri
            return f"/api/blocks/{block_id}/gs/tiles/download?file={uri}"
        
        def fix_uris_in_content(content: dict) -> None:
            if isinstance(content, dict) and "uri" in content:
                original_uri = content["uri"]
                fixed_uri = fix_uri(original_uri)
                content["uri"] = fixed_uri
            if isinstance(content, dict) and "children" in content:
                for child in content["children"]:
                    if isinstance(child, dict) and "content" in child:
                        fix_uris_in_content(child["content"])
        
        if "root" in tileset_data and "content" in tileset_data["root"]:
            root_content = tileset_data["root"]["content"]
            if "uri" in root_content:
                original_uri = root_content["uri"]
                fixed_uri = fix_uri(original_uri)
                root_content["uri"] = fixed_uri
            fix_uris_in_content(root_content)
        
        if "root" in tileset_data and "children" in tileset_data["root"]:
            for child in tileset_data["root"]["children"]:
                if "content" in child:
                    fix_uris_in_content(child["content"])
        
        response = JSONResponse(content=tileset_data, media_type="application/json")
        response.headers["Access-Control-Allow-Origin"] = "http://localhost:3000"
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        return response

    # Return file with CORS headers
    content_type = "application/octet-stream"
    if file.endswith(".b3dm"):
        content_type = "application/octet-stream"
    elif file.endswith(".json"):
        content_type = "application/json"
    
    response = FileResponse(
        path=str(requested),
        filename=requested.name,
        media_type=content_type,
        headers={
            "Access-Control-Allow-Origin": "http://localhost:3000",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "true",
        }
    )
    return response


@router.get(
    "/blocks/{block_id}/gs/tiles/log_tail",
    response_model=GSTilesLogResponse,
)
async def get_gs_tiles_log_tail(
    block_id: str,
    lines: int = Query(200, ge=1, le=2000),
    db: AsyncSession = Depends(get_db),
):
    """Get the last N lines of 3D GS Tiles conversion logs for a block."""
    result = await db.execute(select(Block).where(Block.id == block_id))
    block = result.scalar_one_or_none()
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block not found: {block_id}",
        )

    log_lines = gs_tiles_runner.get_log_tail(block_id, lines) or []
    return GSTilesLogResponse(block_id=block_id, lines=log_lines)


@router.get(
    "/blocks/{block_id}/gs/tiles/tileset_url",
    response_model=GSTilesetUrlResponse,
)
async def get_gs_tileset_url(
    block_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get the tileset.json URL for CesiumJS loading."""
    result = await db.execute(select(Block).where(Block.id == block_id))
    block = result.scalar_one_or_none()
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block not found: {block_id}",
        )

    gs_tiles_output_path = getattr(block, 'gs_tiles_output_path', None)
    if not gs_tiles_output_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="3D GS Tiles output not found for this block.",
        )

    tileset_path = Path(gs_tiles_output_path) / "tileset.json"
    if not tileset_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="tileset.json not found. Conversion may not be completed.",
        )

    tileset_url = f"/api/blocks/{block_id}/gs/tiles/download?file=tileset.json"
    return GSTilesetUrlResponse(tileset_url=tileset_url)
