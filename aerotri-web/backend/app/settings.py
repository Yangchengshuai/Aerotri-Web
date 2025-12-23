"""Application-level settings for external binaries (COLMAP/OpenMVS, etc.)."""

import os
from pathlib import Path


# Base directories
PROJECT_ROOT = Path("/root/work/aerotri-web")


# ===== OpenMVS configuration =====
OPENMVS_BIN_DIR = Path(
    os.getenv("OPENMVS_BIN_DIR", "/root/work/openMVS/build_cuda/bin")
)

OPENMVS_INTERFACE_COLMAP = Path(
    os.getenv(
        "OPENMVS_INTERFACE_COLMAP_PATH",
        str(OPENMVS_BIN_DIR / "InterfaceCOLMAP"),
    )
)
OPENMVS_DENSIFY = Path(
    os.getenv(
        "OPENMVS_DENSIFY_PATH",
        str(OPENMVS_BIN_DIR / "DensifyPointCloud"),
    )
)
OPENMVS_RECONSTRUCT = Path(
    os.getenv(
        "OPENMVS_RECONSTRUCT_PATH",
        str(OPENMVS_BIN_DIR / "ReconstructMesh"),
    )
)
OPENMVS_REFINE = Path(
    os.getenv(
        "OPENMVS_REFINE_PATH",
        str(OPENMVS_BIN_DIR / "RefineMesh"),
    )
)
OPENMVS_TEXTURE = Path(
    os.getenv(
        "OPENMVS_TEXTURE_PATH",
        str(OPENMVS_BIN_DIR / "TextureMesh"),
    )
)

# ===== 3D Gaussian Splatting (gaussian-splatting) configuration =====
# Path to the gaussian-splatting repository root (contains train.py)
GS_REPO_PATH = Path(os.getenv("GS_REPO_PATH", "/root/work/gaussian-splatting"))
# Python interpreter to run gaussian-splatting (should be a prepared conda/venv with CUDA extensions)
GS_PYTHON = os.getenv("GS_PYTHON", "")


def ensure_executable(path: Path) -> Path:
    """Return path and allow callers to validate existence/executable bit.

    We intentionally do not raise here to keep import side-effects minimal.
    """
    return path



