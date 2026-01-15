"""Lightweight filesystem browsing endpoints for selecting image directories."""

import os
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from ..config import ImageRoot, get_image_root, get_image_roots
from ..services.workspace_service import IMAGE_EXTENSIONS

router = APIRouter()

# Legacy: Restrict browsing to a single configurable root (for backward compatibility)
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
    root_name: Optional[str]  # Name of the root (if from named roots)
    current: str
    parent: Optional[str]
    entries: List[DirectoryEntry]


class ImageRootResponse(BaseModel):
    """Response model for image root configuration."""

    name: str
    path: str


class ImageRootsResponse(BaseModel):
    """Response model for listing all configured image roots."""

    roots: List[ImageRootResponse]


def _resolve_safe_path(
    path_value: Optional[str], allowed_root: Optional[Path] = None
) -> Path:
    """Resolve path and ensure it stays within an allowed root.

    Args:
        path_value: The path to resolve (None returns the root)
        allowed_root: The specific root to check against (None checks all configured roots)

    Returns:
        The resolved, safe Path

    Raises:
        HTTPException: If path is outside allowed roots or doesn't exist
    """
    # Determine the base root to use
    base = allowed_root if allowed_root else IMAGE_ROOT

    if path_value:
        candidate = Path(path_value).expanduser().resolve()
    else:
        candidate = base

    # Check if path is within the allowed root
    if candidate != base and base not in candidate.parents:
        # If not in the specified root, check all configured roots
        image_roots = get_image_roots()
        is_allowed = False
        for root in image_roots:
            try:
                root_path = root.resolve_path()
                if candidate == root_path or root_path in candidate.parents:
                    is_allowed = True
                    base = root_path
                    break
            except ValueError:
                continue

        if not is_allowed:
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
async def list_directories(
    path: str = Query(default=None, description="Absolute path inside allowed root"),
    root: str = Query(default=None, description="Optional: specific root path to browse"),
):
    """List subdirectories under the given path (bounded to allowed image roots).

    Args:
        path: Absolute path to list (must be within configured image roots)
        root: Optional specific root path to restrict browsing to
    """
    # Determine the allowed root if specified
    allowed_root = None
    if root:
        root_config = get_image_root(root)
        if root_config:
            allowed_root = root_config.resolve_path()

    current = _resolve_safe_path(path, allowed_root)
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

    # Determine parent path
    base = allowed_root if allowed_root else IMAGE_ROOT
    parent = str(current.parent) if current != base else None

    # Determine root name
    root_name = None
    image_roots = get_image_roots()
    for image_root in image_roots:
        try:
            if str(current).startswith(str(image_root.resolve_path())):
                root_name = image_root.name
                break
        except ValueError:
            continue

    return DirectoryListResponse(
        root=str(base),
        root_name=root_name,
        current=str(current),
        parent=parent,
        entries=entries,
    )


@router.get("/filesystem/roots", response_model=ImageRootsResponse)
async def list_image_roots():
    """List all configured image root directories.

    Returns the available root paths that users can browse when creating blocks.
    """
    image_roots = get_image_roots()

    roots = [
        ImageRootResponse(name=root.name, path=root.path) for root in image_roots
    ]

    return ImageRootsResponse(roots=roots)

