"""3D Gaussian Splatting (3DGS) related API endpoints."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Block, BlockStatus, get_db
from ..schemas import GSFilesResponse, GSFileInfo, GSLogResponse, GSStatusResponse, GSTrainRequest
from ..services.gs_runner import gs_runner


router = APIRouter()


def _tail_file(path: Path, lines: int) -> List[str]:
    if not path.exists() or not path.is_file():
        return []
    # naive but safe for V1: read last N lines (files are not expected to be huge for tail)
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            data = f.readlines()
        return [x.rstrip("\n") for x in data[-lines:]]
    except Exception:
        return []


@router.post(
    "/blocks/{block_id}/gs/train",
    response_model=GSStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_gs_training(
    block_id: str,
    payload: GSTrainRequest,
    db: AsyncSession = Depends(get_db),
):
    """Trigger 3DGS training for a completed Block."""
    result = await db.execute(select(Block).where(Block.id == block_id))
    block = result.scalar_one_or_none()
    if not block:
        raise HTTPException(status_code=404, detail=f"Block not found: {block_id}")

    if block.status != BlockStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail="3DGS training can only be started when SfM has completed.",
        )

    if block.gs_status == "RUNNING":
        raise HTTPException(status_code=409, detail="3DGS training is already running for this block.")

    await gs_runner.start_training(
        block=block,
        gpu_index=payload.gpu_index,
        train_params=payload.train_params.model_dump(),
    )

    # Re-read state after runner initialization
    await db.refresh(block)
    return GSStatusResponse(
        block_id=block.id,
        gs_status=block.gs_status,
        gs_progress=block.gs_progress,
        gs_current_stage=block.gs_current_stage,
        gs_output_path=block.gs_output_path,
        gs_error_message=block.gs_error_message,
        gs_statistics=block.gs_statistics,
    )


@router.get("/blocks/{block_id}/gs/status", response_model=GSStatusResponse)
async def get_gs_status(block_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Block).where(Block.id == block_id))
    block = result.scalar_one_or_none()
    if not block:
        raise HTTPException(status_code=404, detail=f"Block not found: {block_id}")
    return GSStatusResponse(
        block_id=block.id,
        gs_status=block.gs_status,
        gs_progress=block.gs_progress,
        gs_current_stage=block.gs_current_stage,
        gs_output_path=block.gs_output_path,
        gs_error_message=block.gs_error_message,
        gs_statistics=block.gs_statistics,
    )


@router.post("/blocks/{block_id}/gs/cancel", response_model=GSStatusResponse)
async def cancel_gs_training(block_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Block).where(Block.id == block_id))
    block = result.scalar_one_or_none()
    if not block:
        raise HTTPException(status_code=404, detail=f"Block not found: {block_id}")

    if block.gs_status != "RUNNING":
        raise HTTPException(status_code=409, detail="3DGS training is not running for this block.")

    await gs_runner.cancel_training(block_id)
    await db.refresh(block)
    return GSStatusResponse(
        block_id=block.id,
        gs_status=block.gs_status,
        gs_progress=block.gs_progress,
        gs_current_stage=block.gs_current_stage,
        gs_output_path=block.gs_output_path,
        gs_error_message=block.gs_error_message,
        gs_statistics=block.gs_statistics,
    )


def _collect_gs_files(root: Path) -> List[GSFileInfo]:
    files: List[GSFileInfo] = []
    if not root.exists():
        return files

    # Primary preview file(s): point_cloud/iteration_*/point_cloud.ply
    pc_root = root / "model" / "point_cloud"
    if pc_root.exists():
        for ply in sorted(pc_root.glob("iteration_*/point_cloud.ply")):
            if not ply.is_file():
                continue
            stat = ply.stat()
            rel = ply.relative_to(root).as_posix()
            files.append(
                GSFileInfo(
                    stage="model",
                    type="gaussian",
                    name=rel,
                    size_bytes=stat.st_size,
                    mtime=datetime.fromtimestamp(stat.st_mtime),
                    preview_supported=True,
                    download_url=f"/api/blocks/{{block_id}}/gs/download?file={rel}",
                )
            )

    # Useful metadata files
    meta_candidates = [
        root / "model" / "cfg_args",
        root / "model" / "cameras.json",
        root / "model" / "exposure.json",
    ]
    for p in meta_candidates:
        if p.is_file():
            stat = p.stat()
            rel = p.relative_to(root).as_posix()
            files.append(
                GSFileInfo(
                    stage="model",
                    type="other",
                    name=rel,
                    size_bytes=stat.st_size,
                    mtime=datetime.fromtimestamp(stat.st_mtime),
                    preview_supported=False,
                    download_url=f"/api/blocks/{{block_id}}/gs/download?file={rel}",
                )
            )

    return files


@router.get("/blocks/{block_id}/gs/files", response_model=GSFilesResponse)
async def list_gs_files(block_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Block).where(Block.id == block_id))
    block = result.scalar_one_or_none()
    if not block:
        raise HTTPException(status_code=404, detail=f"Block not found: {block_id}")
    if not block.gs_output_path:
        return GSFilesResponse(files=[])

    root = Path(block.gs_output_path)
    files = _collect_gs_files(root)
    for f in files:
        f.download_url = f"/api/blocks/{block_id}/gs/download?file={f.name}"
    return GSFilesResponse(files=files)


@router.get("/blocks/{block_id}/gs/download")
async def download_gs_file(
    block_id: str,
    file: str = Query(..., description="Relative path under gs root"),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Block).where(Block.id == block_id))
    block = result.scalar_one_or_none()
    if not block:
        raise HTTPException(status_code=404, detail=f"Block not found: {block_id}")
    if not block.gs_output_path:
        raise HTTPException(status_code=404, detail="3DGS output not found for this block.")

    root = Path(block.gs_output_path).resolve()
    requested = (root / file).resolve()

    if not str(requested).startswith(str(root)):
        raise HTTPException(status_code=400, detail="Invalid file path.")
    if not requested.is_file():
        raise HTTPException(status_code=404, detail=f"File not found: {file}")

    return FileResponse(path=str(requested), filename=requested.name)


@router.get("/blocks/{block_id}/gs/log_tail", response_model=GSLogResponse)
async def get_gs_log_tail(
    block_id: str,
    lines: int = Query(200, ge=1, le=2000),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Block).where(Block.id == block_id))
    block = result.scalar_one_or_none()
    if not block:
        raise HTTPException(status_code=404, detail=f"Block not found: {block_id}")

    mem_tail = gs_runner.get_log_tail(block_id, lines)
    if mem_tail:
        return GSLogResponse(block_id=block_id, lines=mem_tail)

    if block.gs_output_path:
        file_tail = _tail_file(Path(block.gs_output_path) / "run_gs.log", lines)
        return GSLogResponse(block_id=block_id, lines=file_tail)

    return GSLogResponse(block_id=block_id, lines=[])


