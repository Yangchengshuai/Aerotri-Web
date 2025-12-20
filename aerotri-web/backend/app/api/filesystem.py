"""Lightweight filesystem browsing endpoints for selecting image directories."""

import os
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from ..services.workspace_service import IMAGE_EXTENSIONS

router = APIRouter()

# Restrict browsing to a configurable root to avoid arbitrary filesystem access
IMAGE_ROOT = Path(os.getenv("AEROTRI_IMAGE_ROOT", "/mnt/work_odm/chengshuai")).resolve()


class DirectoryEntry(BaseModel):
    """Directory metadata for UI browsing."""

    name: str
    path: str
    has_subdirs: bool
    has_images: bool


class DirectoryListResponse(BaseModel):
    """Response model for directory listing."""

    root: str
    current: str
    parent: Optional[str]
    entries: List[DirectoryEntry]


def _resolve_safe_path(path_value: Optional[str]) -> Path:
    """Resolve path and ensure it stays within IMAGE_ROOT."""
    base = IMAGE_ROOT
    if path_value:
        candidate = Path(path_value).expanduser().resolve()
    else:
        candidate = base

    # Prevent escaping the allowed root
    if candidate != base and base not in candidate.parents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Path not allowed: {candidate}",
        )

    if not candidate.exists() or not candidate.is_dir():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Directory not found: {candidate}",
        )

    return candidate


@router.get("/filesystem/dirs", response_model=DirectoryListResponse)
async def list_directories(path: str = Query(default=None, description="Absolute path inside allowed root")):
    """List subdirectories under the given path (bounded to IMAGE_ROOT)."""
    current = _resolve_safe_path(path)
    entries: List[DirectoryEntry] = []

    try:
        children = list(current.iterdir())
    except PermissionError as exc:  # pragma: no cover - unlikely in default root
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"No permission to read: {current}",
        ) from exc

    for child in sorted(children, key=lambda p: p.name.lower()):
        if not child.is_dir() or child.name.startswith("."):
            continue

        has_subdirs = False
        has_images = False

        # Peek into directory to determine flags without heavy traversal
        try:
            for grandchild in child.iterdir():
                if grandchild.is_dir():
                    has_subdirs = True
                elif grandchild.is_file() and grandchild.suffix.lower() in IMAGE_EXTENSIONS:
                    has_images = True
                if has_subdirs and has_images:
                    break
        except PermissionError:
            # Skip directories that cannot be read
            continue

        entries.append(
            DirectoryEntry(
                name=child.name,
                path=str(child),
                has_subdirs=has_subdirs,
                has_images=has_images,
            )
        )

    parent = str(current.parent) if current != IMAGE_ROOT else None

    return DirectoryListResponse(
        root=str(IMAGE_ROOT),
        current=str(current),
        parent=parent,
        entries=entries,
    )

