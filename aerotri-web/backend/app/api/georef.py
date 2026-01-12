"""Geo-referencing related endpoints (geo_ref.json download, etc.)."""

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select

from ..models.block import Block
from ..models.database import AsyncSessionLocal

router = APIRouter()


@router.get("/blocks/{block_id}/georef/download")
async def download_geo_ref(block_id: str):
    """Download geo_ref.json for a block if exists.

    The file is generated when mapper_params.georef_enabled is enabled and the
    georef pipeline succeeds.
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Block).where(Block.id == block_id))
        block = result.scalar_one_or_none()
        if not block or not block.output_path:
            raise HTTPException(status_code=404, detail="Block not found or no output_path")

        geo_ref = Path(block.output_path) / "geo" / "geo_ref.json"
        if not geo_ref.is_file():
            raise HTTPException(status_code=404, detail="geo_ref.json not found")

        # Ensure file is under block output path (basic safety)
        try:
            geo_ref_abs = geo_ref.resolve()
            out_abs = Path(block.output_path).resolve()
            if out_abs not in geo_ref_abs.parents and geo_ref_abs != out_abs:
                raise HTTPException(status_code=400, detail="Invalid geo_ref path")
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid geo_ref path")

        return FileResponse(
            path=str(geo_ref),
            media_type="application/json",
            filename="geo_ref.json",
        )

