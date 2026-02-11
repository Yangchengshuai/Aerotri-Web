"""3D Tiles conversion related API endpoints."""

import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Block, BlockStatus, get_db
from ..models.recon_version import ReconVersion
from ..schemas import (
    TilesConvertRequest,
    TilesFilesResponse,
    TilesFileInfo,
    TilesStatusResponse,
    TilesLogResponse,
    TilesetUrlResponse,
)
from ..services.tiles_runner import tiles_runner


router = APIRouter()


@router.post(
    "/blocks/{block_id}/tiles/convert",
    response_model=TilesStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_tiles_conversion(
    block_id: str,
    payload: TilesConvertRequest,
    db: AsyncSession = Depends(get_db),
):
    """Trigger 3D Tiles conversion for a completed reconstruction."""
    result = await db.execute(select(Block).where(Block.id == block_id))
    block = result.scalar_one_or_none()
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block not found: {block_id}",
        )

    # Check if reconstruction is completed
    if not block.recon_output_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reconstruction must be completed before converting to 3D Tiles.",
        )

    # Check if texture stage is completed
    texture_dir = Path(block.recon_output_path) / "texture"
    if not texture_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Texture stage not completed. Please complete reconstruction first.",
        )

    if block.tiles_status == "RUNNING":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="3D Tiles conversion is already running for this block.",
        )

    convert_params = {
        "keep_glb": payload.keep_glb or False,
        "optimize": payload.optimize or False,
    }

    await tiles_runner.start_conversion(
        block=block,
        db=db,
        convert_params=convert_params,
    )

    return TilesStatusResponse(
        block_id=block.id,
        tiles_status=block.tiles_status,
        tiles_progress=block.tiles_progress,
        tiles_current_stage=block.tiles_current_stage,
        tiles_output_path=block.tiles_output_path,
        tiles_error_message=block.tiles_error_message,
        tiles_statistics=block.tiles_statistics,
    )


@router.post(
    "/blocks/{block_id}/tiles/cancel",
    response_model=TilesStatusResponse,
)
async def cancel_tiles_conversion(
    block_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Cancel a running 3D Tiles conversion task."""
    result = await db.execute(select(Block).where(Block.id == block_id))
    block = result.scalar_one_or_none()
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block not found: {block_id}",
        )

    if block.tiles_status != "RUNNING":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="3D Tiles conversion is not running for this block.",
        )

    await tiles_runner.cancel_conversion(block_id)

    # Refresh block state after cancellation
    await db.refresh(block)

    return TilesStatusResponse(
        block_id=block.id,
        tiles_status=block.tiles_status,
        tiles_progress=block.tiles_progress,
        tiles_current_stage=block.tiles_current_stage,
        tiles_output_path=block.tiles_output_path,
        tiles_error_message=block.tiles_error_message,
        tiles_statistics=block.tiles_statistics,
    )


@router.get(
    "/blocks/{block_id}/tiles/status",
    response_model=TilesStatusResponse,
)
async def get_tiles_status(
    block_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get 3D Tiles conversion status for a block."""
    result = await db.execute(select(Block).where(Block.id == block_id))
    block = result.scalar_one_or_none()
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block not found: {block_id}",
        )

    return TilesStatusResponse(
        block_id=block.id,
        tiles_status=block.tiles_status,
        tiles_progress=block.tiles_progress,
        tiles_current_stage=block.tiles_current_stage,
        tiles_output_path=block.tiles_output_path,
        tiles_error_message=block.tiles_error_message,
        tiles_statistics=block.tiles_statistics,
    )


def _collect_tiles_files(root: Path) -> List[TilesFileInfo]:
    """Collect 3D Tiles output files."""
    files: List[TilesFileInfo] = []
    if not root.exists():
        return files

    # Look for tileset.json
    tileset_path = root / "tileset.json"
    if tileset_path.exists() and tileset_path.is_file():
        stat = tileset_path.stat()
        files.append(
            TilesFileInfo(
                name="tileset.json",
                type="tileset",
                size_bytes=stat.st_size,
                mtime=datetime.fromtimestamp(stat.st_mtime),
                preview_supported=True,
                download_url=f"/api/blocks/{{block_id}}/tiles/download?file=tileset.json",
            )
        )

    # Look for b3dm files
    for b3dm_path in root.glob("*.b3dm"):
        stat = b3dm_path.stat()
        files.append(
            TilesFileInfo(
                name=b3dm_path.name,
                type="tile",
                size_bytes=stat.st_size,
                mtime=datetime.fromtimestamp(stat.st_mtime),
                preview_supported=False,
                download_url=f"/api/blocks/{{block_id}}/tiles/download?file={b3dm_path.name}",
            )
        )

    # Look for GLB file (if kept)
    glb_path = root / "model.glb"
    if glb_path.exists() and glb_path.is_file():
        stat = glb_path.stat()
        files.append(
            TilesFileInfo(
                name="model.glb",
                type="glb",
                size_bytes=stat.st_size,
                mtime=datetime.fromtimestamp(stat.st_mtime),
                preview_supported=False,
                download_url=f"/api/blocks/{{block_id}}/tiles/download?file=model.glb",
            )
        )

    return files


@router.get(
    "/blocks/{block_id}/tiles/files",
    response_model=TilesFilesResponse,
)
async def list_tiles_files(
    block_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List 3D Tiles output files for a block."""
    result = await db.execute(select(Block).where(Block.id == block_id))
    block = result.scalar_one_or_none()
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block not found: {block_id}",
        )

    if not block.tiles_output_path:
        return TilesFilesResponse(files=[])

    root = Path(block.tiles_output_path)
    files = _collect_tiles_files(root)
    # Fix download_url now that we know the concrete block_id
    for f in files:
        f.download_url = f"/api/blocks/{block_id}/tiles/download?file={f.name}"
    return TilesFilesResponse(files=files)


@router.get("/blocks/{block_id}/tiles/download")
@router.options("/blocks/{block_id}/tiles/download")
async def download_tiles_file(
    block_id: str,
    request: Request,
    file: str = Query(..., description="Relative path under tiles output root"),
    db: AsyncSession = Depends(get_db),
):
    """Download a 3D Tiles output file."""
    
    result = await db.execute(select(Block).where(Block.id == block_id))
    block = result.scalar_one_or_none()
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block not found: {block_id}",
        )

    if not block.tiles_output_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="3D Tiles output not found for this block.",
        )

    root = Path(block.tiles_output_path).resolve()
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
    # This fixes the issue where Cesium cannot resolve relative paths when
    # tileset.json is loaded via query parameter URL
    if file == "tileset.json":
        import json
        with open(requested, "r", encoding="utf-8") as f:
            tileset_data = json.load(f)
        
        # Modify relative URIs in tileset.json to absolute API paths
        # This ensures Cesium can load the resources correctly
        def fix_uri(uri: str) -> str:
            if not uri:
                return uri
            # If it's already an absolute URL with localhost:8000, convert to API path
            if uri.startswith("http://localhost:8000") or uri.startswith("https://localhost:8000"):
                # Extract the path part (everything after the domain)
                if "/api/" in uri:
                    return "/api/" + uri.split("/api/", 1)[1]
                return uri
            # If it's already a relative path starting with /, keep it
            if uri.startswith("/"):
                return uri
            # Convert relative filename (e.g., "./model.glb" or "model.glb") to API path
            # Strip leading ./ if present
            clean_uri = uri.lstrip('./')
            return f"/api/blocks/{block_id}/tiles/download?file={clean_uri}"
        
        def fix_uris_in_content(content: dict) -> None:
            if isinstance(content, dict) and "uri" in content:
                original_uri = content["uri"]
                fixed_uri = fix_uri(original_uri)
                content["uri"] = fixed_uri
                if original_uri != fixed_uri:
                    print(f"Fixed URI: {original_uri} -> {fixed_uri}")
            if isinstance(content, dict) and "children" in content:
                for child in content["children"]:
                    if isinstance(child, dict) and "content" in child:
                        fix_uris_in_content(child["content"])
        
        # Fix root content URI
        if "root" in tileset_data and "content" in tileset_data["root"]:
            # Directly fix the URI in root content
            root_content = tileset_data["root"]["content"]
            if "uri" in root_content:
                original_uri = root_content["uri"]
                fixed_uri = fix_uri(original_uri)
                root_content["uri"] = fixed_uri
                print(f"Fixed root URI: {original_uri} -> {fixed_uri}")
            # Also call fix_uris_in_content for nested structures
            fix_uris_in_content(root_content)
        
        # Fix children URIs if any
        if "root" in tileset_data and "children" in tileset_data["root"]:
            for child in tileset_data["root"]["children"]:
                if "content" in child:
                    fix_uris_in_content(child["content"])
        
        # Return modified JSON with CORS headers
        response = JSONResponse(content=tileset_data, media_type="application/json")
        response.headers["Access-Control-Allow-Origin"] = "http://localhost:3000"
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        return response

    # Return file with CORS headers
    # Determine content type based on file extension
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
    "/blocks/{block_id}/tiles/log_tail",
    response_model=TilesLogResponse,
)
async def get_tiles_log_tail(
    block_id: str,
    lines: int = Query(200, ge=1, le=2000),
    db: AsyncSession = Depends(get_db),
):
    """Get the last N lines of 3D Tiles conversion logs for a block."""
    result = await db.execute(select(Block).where(Block.id == block_id))
    block = result.scalar_one_or_none()
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block not found: {block_id}",
        )

    log_lines = tiles_runner.get_log_tail(block_id, lines) or []
    return TilesLogResponse(block_id=block_id, lines=log_lines)


@router.get(
    "/blocks/{block_id}/tiles/tileset_url",
    response_model=TilesetUrlResponse,
)
async def get_tileset_url(
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

    if not block.tiles_output_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="3D Tiles output not found for this block.",
        )

    tileset_path = Path(block.tiles_output_path) / "tileset.json"
    if not tileset_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="tileset.json not found. Conversion may not be completed.",
        )

    # Return full URL (assuming API is served at root)
    # In production, you might want to use request.base_url
    tileset_url = f"/api/blocks/{block_id}/tiles/download?file=tileset.json"
    return TilesetUrlResponse(tileset_url=tileset_url)


# ==================== Version-based 3D Tiles API ====================

@router.post(
    "/blocks/{block_id}/recon-versions/{version_id}/tiles/convert",
    response_model=TilesStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_version_tiles_conversion(
    block_id: str,
    version_id: str,
    payload: TilesConvertRequest,
    db: AsyncSession = Depends(get_db),
):
    """Trigger 3D Tiles conversion for a specific reconstruction version."""
    # Verify block exists
    result = await db.execute(select(Block).where(Block.id == block_id))
    block = result.scalar_one_or_none()
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block not found: {block_id}",
        )
    
    # Verify version exists
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
    
    # Check if reconstruction is completed
    if version.status != "COMPLETED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reconstruction must be completed before converting to 3D Tiles.",
        )
    
    if not version.output_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Version output path not found.",
        )
    
    # Check if texture stage is completed
    texture_dir = Path(version.output_path) / "texture"
    if not texture_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Texture stage not completed. Please complete reconstruction first.",
        )
    
    if version.tiles_status == "RUNNING":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="3D Tiles conversion is already running for this version.",
        )
    
    convert_params = {
        "keep_glb": payload.keep_glb or False,
        "optimize": payload.optimize or False,
    }
    
    # Start conversion for version
    await tiles_runner.start_version_conversion(
        block=block,
        version=version,
        db=db,
        convert_params=convert_params,
    )
    
    return TilesStatusResponse(
        block_id=block.id,
        tiles_status=version.tiles_status,
        tiles_progress=version.tiles_progress,
        tiles_current_stage=version.tiles_current_stage,
        tiles_output_path=version.tiles_output_path,
        tiles_error_message=version.tiles_error_message,
        tiles_statistics=version.tiles_statistics,
    )


@router.get(
    "/blocks/{block_id}/recon-versions/{version_id}/tiles/status",
    response_model=TilesStatusResponse,
)
async def get_version_tiles_status(
    block_id: str,
    version_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get 3D Tiles conversion status for a specific version."""
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
    
    return TilesStatusResponse(
        block_id=block_id,
        tiles_status=version.tiles_status,
        tiles_progress=version.tiles_progress,
        tiles_current_stage=version.tiles_current_stage,
        tiles_output_path=version.tiles_output_path,
        tiles_error_message=version.tiles_error_message,
        tiles_statistics=version.tiles_statistics,
    )


@router.get(
    "/blocks/{block_id}/recon-versions/{version_id}/tiles/files",
    response_model=TilesFilesResponse,
)
async def list_version_tiles_files(
    block_id: str,
    version_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List 3D Tiles output files for a specific version."""
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
    
    if not version.tiles_output_path:
        return TilesFilesResponse(files=[])
    
    root = Path(version.tiles_output_path)
    files = _collect_tiles_files(root)
    # Fix download_url for version-based URL
    for f in files:
        f.download_url = f"/api/blocks/{block_id}/recon-versions/{version_id}/tiles/download?file={f.name}"
    return TilesFilesResponse(files=files)


@router.get("/blocks/{block_id}/recon-versions/{version_id}/tiles/download")
async def download_version_tiles_file(
    block_id: str,
    version_id: str,
    request: Request,
    file: str = Query(..., description="Relative path under tiles output root"),
    db: AsyncSession = Depends(get_db),
):
    """Download a 3D Tiles output file for a specific version."""
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
    
    if not version.tiles_output_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="3D Tiles output not found for this version.",
        )
    
    root = Path(version.tiles_output_path).resolve()
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
    
    # Special handling for tileset.json
    if file == "tileset.json":
        import json
        with open(requested, "r", encoding="utf-8") as f:
            tileset_data = json.load(f)
        
        def fix_uri(uri: str) -> str:
            if not uri:
                return uri
            # Handle already-absolute URLs with localhost:8000
            if uri.startswith("http://localhost:8000") or uri.startswith("https://localhost:8000"):
                if "/api/" in uri:
                    return "/api/" + uri.split("/api/", 1)[1]
                return uri
            # Handle absolute paths starting with /
            if uri.startswith("/"):
                return uri
            # Handle relative paths starting with ./ or just filename
            # Convert to absolute API path for Cesium to load correctly
            return f"/api/blocks/{block_id}/recon-versions/{version_id}/tiles/download?file={uri.lstrip('./')}"
        
        def fix_uris_in_content(content: dict) -> None:
            if isinstance(content, dict) and "uri" in content:
                content["uri"] = fix_uri(content["uri"])
            if isinstance(content, dict) and "children" in content:
                for child in content["children"]:
                    if isinstance(child, dict) and "content" in child:
                        fix_uris_in_content(child["content"])
        
        if "root" in tileset_data and "content" in tileset_data["root"]:
            root_content = tileset_data["root"]["content"]
            if "uri" in root_content:
                root_content["uri"] = fix_uri(root_content["uri"])
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
    "/blocks/{block_id}/recon-versions/{version_id}/tiles/tileset_url",
    response_model=TilesetUrlResponse,
)
async def get_version_tileset_url(
    block_id: str,
    version_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get the tileset.json URL for a specific version."""
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
    
    if not version.tiles_output_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="3D Tiles output not found for this version.",
        )
    
    tileset_path = Path(version.tiles_output_path) / "tileset.json"
    if not tileset_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="tileset.json not found. Conversion may not be completed.",
        )

    tileset_url = f"/api/blocks/{block_id}/recon-versions/{version_id}/tiles/download?file=tileset.json"
    return TilesetUrlResponse(tileset_url=tileset_url)


@router.get("/blocks/{block_id}/tiles/georef")
async def get_block_tiles_georef(
    block_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get georeference data for block-level 3D Tiles.

    Returns GPS coordinates if the block has georeference enabled.
    Used by Cesium viewer to position the model at the correct geographic location.
    """
    result = await db.execute(select(Block).where(Block.id == block_id))
    block = result.scalar_one_or_none()
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block not found: {block_id}",
        )

    if not block.output_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Block output path not found.",
        )

    # Check if geo_ref.json exists
    geo_ref_path = Path(block.output_path) / "geo" / "geo_ref.json"
    if not geo_ref_path.exists():
        return {"has_georef": False}

    import json
    try:
        geo = json.loads(geo_ref_path.read_text(encoding="utf-8"))
        return {
            "has_georef": True,
            "lon": geo.get("origin_wgs84", {}).get("lon"),
            "lat": geo.get("origin_wgs84", {}).get("lat"),
            "height": geo.get("origin_wgs84", {}).get("h"),
            "utm_epsg": geo.get("epsg_utm"),
            "utm_easting": geo.get("origin_utm", {}).get("E"),
            "utm_northing": geo.get("origin_utm", {}).get("N"),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read geo_ref.json: {str(e)}",
        )


@router.get("/blocks/{block_id}/recon-versions/{version_id}/tiles/georef")
async def get_version_tiles_georef(
    block_id: str,
    version_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get georeference data for version-level 3D Tiles.

    Returns GPS coordinates if the block has georeference enabled.
    Used by Cesium viewer to position the model at the correct geographic location.
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

    # Get block for geo_ref path
    result = await db.execute(select(Block).where(Block.id == block_id))
    block = result.scalar_one_or_none()
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block not found: {block_id}",
        )

    if not block.output_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Block output path not found.",
        )

    # Check if geo_ref.json exists (georef is at block level, not version level)
    geo_ref_path = Path(block.output_path) / "geo" / "geo_ref.json"
    if not geo_ref_path.exists():
        return {"has_georef": False}

    import json
    try:
        geo = json.loads(geo_ref_path.read_text(encoding="utf-8"))
        return {
            "has_georef": True,
            "lon": geo.get("origin_wgs84", {}).get("lon"),
            "lat": geo.get("origin_wgs84", {}).get("lat"),
            "height": geo.get("origin_wgs84", {}).get("h"),
            "utm_epsg": geo.get("epsg_utm"),
            "utm_easting": geo.get("origin_utm", {}).get("E"),
            "utm_northing": geo.get("origin_utm", {}).get("N"),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read geo_ref.json: {str(e)}",
        )

