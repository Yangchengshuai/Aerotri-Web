"""Workspace service for safe per-block image directories."""

import os
from pathlib import Path
from typing import Iterable, List


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}


class WorkspaceService:
    """Create and manage per-block working directories.

    Strategy (minimal & safe):
    - Create a per-block working image directory.
    - Populate it with hardlinks when possible (fast, no extra disk),
      fallback to symlinks.
    - All deletions happen only inside the working directory.
    """

    @staticmethod
    def get_block_root(block_id: str) -> str:
        return f"/root/work/aerotri-web/data/blocks/{block_id}"

    @staticmethod
    def get_working_images_dir(block_id: str) -> str:
        return os.path.join(WorkspaceService.get_block_root(block_id), "images")

    @staticmethod
    def list_source_images(source_dir: str) -> List[Path]:
        p = Path(source_dir)
        if not p.exists() or not p.is_dir():
            return []
        return sorted([f for f in p.iterdir() if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS])

    @staticmethod
    def ensure_working_dir(block_id: str) -> str:
        work_dir = WorkspaceService.get_working_images_dir(block_id)
        os.makedirs(work_dir, exist_ok=True)
        return work_dir

    @staticmethod
    def populate_working_dir(block_id: str, source_dir: str) -> str:
        """Populate working dir with links to source images."""
        work_dir = Path(WorkspaceService.ensure_working_dir(block_id))
        src_images = WorkspaceService.list_source_images(source_dir)

        for src in src_images:
            dst = work_dir / src.name
            if dst.exists():
                continue
            try:
                # Prefer hardlink (fast, safe if same filesystem)
                os.link(src, dst)
            except Exception:
                # Fallback to symlink
                try:
                    os.symlink(str(src), str(dst))
                except Exception:
                    # Last resort: skip (don't copy to keep minimal)
                    # Caller can decide whether to treat as error.
                    pass

        return str(work_dir)

    @staticmethod
    def safe_resolve_child(base_dir: str, child_name: str) -> Path:
        """Resolve a child path safely (prevents path traversal).

        Important:
        - Do NOT call `.resolve()` on the child path, because working dirs may contain
          symlinks/hardlinks to source images outside the working directory.
        - We only validate the *name* and then join it to base_dir.
        """
        if not child_name or "/" in child_name or "\\" in child_name:
            raise ValueError("Invalid file name")

        # Normalize base dir only
        base = Path(base_dir).resolve()

        # Join without following symlinks; later code can use .exists() to validate target.
        child = base / child_name

        # Extra defense: disallow names that try to escape via ".."
        # (Even though we already reject "/" and "\\", keep this for clarity.)
        if child_name in (".", "..") or ".." in Path(child_name).parts:
            raise ValueError("Invalid file name")

        return child

