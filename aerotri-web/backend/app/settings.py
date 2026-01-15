"""Application-level settings for external binaries (COLMAP/OpenMVS, etc.)."""

import os
from pathlib import Path


# Base directories
PROJECT_ROOT = Path("/root/work/aerotri-web")


# ===== OpenMVS configuration =====
OPENMVS_BIN_DIR = Path(
    os.getenv("OPENMVS_BIN_DIR", "/root/work/Aerotri-Web/openMVS/make/bin")
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
GS_REPO_PATH = Path(os.getenv("GS_REPO_PATH", "/root/work/gs_workspace/gaussian-splatting"))
# Python interpreter to run gaussian-splatting (should be a prepared conda/venv with CUDA extensions)
# Default to conda environment gs_env_py310
GS_PYTHON = os.getenv("GS_PYTHON", "/root/miniconda3/envs/gs_env_py310/bin/python")
# TensorBoard executable (should be in the same conda environment)
TENSORBOARD_PATH = os.getenv("TENSORBOARD_PATH", "/root/miniconda3/envs/gs_env_py310/bin/tensorboard")
# TensorBoard port range (start port for dynamic allocation)
TENSORBOARD_PORT_START = int(os.getenv("TENSORBOARD_PORT_START", "6006"))
TENSORBOARD_PORT_END = int(os.getenv("TENSORBOARD_PORT_END", "6100"))
# Network GUI port range (for train.py network_gui)
NETWORK_GUI_PORT_START = int(os.getenv("NETWORK_GUI_PORT_START", "6009"))
NETWORK_GUI_PORT_END = int(os.getenv("NETWORK_GUI_PORT_END", "6109"))
NETWORK_GUI_IP = os.getenv("NETWORK_GUI_IP", "127.0.0.1")

# ===== SPZ (3D Gaussian Splatting compression) configuration =====
# Python interpreter for SPZ operations (should be in conda spz-env with SPZ Python bindings)
SPZ_PYTHON = os.getenv("SPZ_PYTHON", "/root/miniconda3/envs/spz-env/bin/python")


def ensure_executable(path: Path) -> Path:
    """Return path and allow callers to validate existence/executable bit.

    We intentionally do not raise here to keep import side-effects minimal.
    """
    return path



