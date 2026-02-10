"""SPZ file loader for 3D Gaussian Splatting.

This module provides functionality to load SPZ files using SPZ Python bindings
and convert them to the same format as PLY parser output.

Supports two modes:
1. Direct import: If SPZ is available in current Python environment
2. Subprocess mode: Uses conda environment Python via subprocess
"""

import sys
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Optional

import numpy as np

# Import settings for SPZ_PYTHON configuration
from app.conf.settings import get_settings

settings = get_settings()
SPZ_PYTHON = settings.spz.python or "/root/miniconda3/envs/spz-env/bin/python"

# Try to import SPZ module
# If not available (e.g., not in conda environment), will fail gracefully
try:
    import spz
    SPZ_AVAILABLE = True
except ImportError:
    SPZ_AVAILABLE = False
    spz = None


def get_spz_python_path() -> Optional[str]:
    """Get path to Python for SPZ operations.
    
    Returns:
        Path to SPZ Python executable from settings, or None if not found
    """
    spz_python = Path(SPZ_PYTHON)
    if spz_python.exists() and spz_python.is_file():
        return str(spz_python)
    return None


def check_spz_available() -> bool:
    """Check if SPZ Python bindings are available.
    
    Checks both:
    1. Current Python environment (direct import)
    2. Conda environment (via SPZ_PYTHON setting)
    
    Returns:
        True if SPZ is available in current environment or conda environment
    """
    # Check current environment
    if SPZ_AVAILABLE:
        return True
    
    # Check conda environment Python exists
    spz_python = get_spz_python_path()
    if spz_python:
        return True
    
    return False


def _load_spz_direct(spz_file: Path) -> Dict:
    """Load SPZ file using direct import (current environment).
    
    Args:
        spz_file: Path to SPZ file
        
    Returns:
        Dictionary containing Gaussian data
    """
    if not SPZ_AVAILABLE:
        raise ImportError("SPZ module not available in current environment")
    
    if not spz_file.exists():
        raise FileNotFoundError(f"SPZ file not found: {spz_file}")
    
    try:
        # Configure unpack options for coordinate system conversion
        unpack_options = spz.UnpackOptions()
        unpack_options.to_coord = spz.CoordinateSystem.LUF
        
        # Load SPZ file
        cloud = spz.load_spz(str(spz_file), unpack_options)
        
        num_points = cloud.num_points
        sh_degree = cloud.sh_degree
        
        # Extract data as numpy arrays
        positions = cloud.positions.reshape(-1, 3).astype(np.float32)
        rotations = cloud.rotations.reshape(-1, 4).astype(np.float32)
        scales = cloud.scales.reshape(-1, 3).astype(np.float32)
        colors = cloud.colors.reshape(-1, 3).astype(np.float32)
        alphas = cloud.alphas.astype(np.float32)
        
        # Handle spherical harmonics
        # Note: SPZ format stores SH coefficients WITHOUT f_dc (f_dc is in colors)
        # According to SPZ README:
        #   Degree 0: 0 coefficients
        #   Degree 1: 9 coefficients
        #   Degree 2: 24 coefficients
        #   Degree 3: 45 coefficients
        # But for PLY compatibility, we need to include f_dc in sh_coefficients
        # So we combine colors (f_dc) with sh (f_rest) to match PLY format
        sh_coefficients = None
        if sh_degree >= 0 and len(cloud.sh) > 0:
            # SPZ format: SH coefficients per point (excluding f_dc)
            if sh_degree == 0:
                spz_sh_per_point = 0  # No SH coefficients, only f_dc in colors
            elif sh_degree == 1:
                spz_sh_per_point = 9
            elif sh_degree == 2:
                spz_sh_per_point = 24
            elif sh_degree == 3:
                spz_sh_per_point = 45
            else:
                # Calculate from actual data
                spz_sh_per_point = len(cloud.sh) // num_points if num_points > 0 else 0
            
            if spz_sh_per_point > 0:
                # Reshape SPZ SH coefficients (f_rest only)
                sh_rest = cloud.sh.reshape(-1, spz_sh_per_point).astype(np.float32)
                
                # Combine colors (f_dc) with sh_rest to match PLY format
                # PLY format: [f_dc_0, f_dc_1, f_dc_2, f_rest_0, f_rest_1, ...]
                colors_reshaped = colors.reshape(-1, 3)  # (N, 3) - f_dc
                sh_coefficients = np.concatenate([colors_reshaped, sh_rest], axis=1).astype(np.float32)
        elif sh_degree == 0:
            # Degree 0: only f_dc (colors), no f_rest
            sh_coefficients = colors.reshape(-1, 3).astype(np.float32)
        
        return {
            'positions': positions,
            'rotations': rotations,
            'scales': scales,
            'colors': colors,
            'alphas': alphas,
            'sh_coefficients': sh_coefficients,
            'sh_degree': sh_degree,
            'num_points': num_points
        }
        
    except Exception as e:
        raise ValueError(f"Failed to load SPZ file {spz_file}: {str(e)}") from e


def load_spz_file_via_subprocess(spz_file: Path, spz_python: str) -> Dict:
    """Load SPZ file using subprocess to call conda Python.
    
    Args:
        spz_file: Path to SPZ file
        spz_python: Path to Python executable in conda environment
        
    Returns:
        Dictionary containing Gaussian data
        
    Raises:
        FileNotFoundError: If SPZ file or Python executable not found
        subprocess.CalledProcessError: If subprocess call fails
        ValueError: If data cannot be deserialized
    """
    if not spz_file.exists():
        raise FileNotFoundError(f"SPZ file not found: {spz_file}")
    
    python_path = Path(spz_python)
    if not python_path.exists():
        raise FileNotFoundError(f"SPZ Python executable not found: {spz_python}")
    
    # Get path to helper script
    helper_script = Path(__file__).parent / "spz_loader_helper.py"
    if not helper_script.exists():
        raise FileNotFoundError(f"SPZ loader helper script not found: {helper_script}")
    
    try:
        # Call helper script via subprocess
        # Helper script outputs a temporary .npz file path to stdout
        result = subprocess.run(
            [str(spz_python), str(helper_script), str(spz_file)],
            capture_output=True,
            check=True,
            timeout=300,  # 5 minutes timeout for large files
            text=True  # Get text output for file path
        )
        
        # Get output file path from stdout (strip whitespace)
        # Helper script outputs the temporary .npz file path
        output_file = result.stdout.strip()
        if not output_file:
            error_msg = result.stderr if result.stderr else "Helper script did not output file path"
            raise ValueError(f"Failed to get output file from helper script: {error_msg}")
        
        output_path = Path(output_file)
        if not output_path.exists():
            error_msg = result.stderr if result.stderr else f"Output file does not exist: {output_file}"
            raise ValueError(f"Failed to get output file from helper script: {error_msg}")
        
        try:
            # Load data from numpy .npz file (version-independent)
            npz_data = np.load(output_file, allow_pickle=False)
            
            # Extract data with proper types
            data = {
                'positions': npz_data['positions'].astype(np.float32),
                'rotations': npz_data['rotations'].astype(np.float32),
                'scales': npz_data['scales'].astype(np.float32),
                'colors': npz_data['colors'].astype(np.float32),
                'alphas': npz_data['alphas'].astype(np.float32),
                'sh_degree': int(npz_data['sh_degree'][0]),
                'num_points': int(npz_data['num_points'][0]),
            }
            
            # Handle SH coefficients (may be empty or missing)
            has_sh = bool(npz_data['has_sh'][0]) if 'has_sh' in npz_data else True
            if 'sh_coefficients' in npz_data:
                sh_coeffs = npz_data['sh_coefficients']
                # Check if array is non-empty and has valid shape
                if has_sh and sh_coeffs.size > 0 and len(sh_coeffs.shape) > 0:
                    data['sh_coefficients'] = sh_coeffs.astype(np.float32)
                else:
                    data['sh_coefficients'] = None
            else:
                data['sh_coefficients'] = None
            
            return data
            
        finally:
            # Clean up temporary file
            try:
                Path(output_file).unlink()
            except Exception:
                pass  # Ignore cleanup errors
        
    except subprocess.TimeoutExpired:
        raise ValueError(f"SPZ loading timeout after 5 minutes: {spz_file}")
    except subprocess.CalledProcessError as e:
        # Extract error message from stderr (helper script outputs errors to stderr)
        error_msg = e.stderr.decode('utf-8', errors='ignore') if e.stderr else str(e)
        # Remove "ERROR: " prefix if present for cleaner error message
        if error_msg.startswith("ERROR: "):
            error_msg = error_msg[7:]
        raise ValueError(f"Failed to load SPZ file via subprocess: {error_msg.strip()}")
    except Exception as e:
        raise ValueError(f"Unexpected error loading SPZ file: {str(e)}") from e


def load_spz_file(spz_file: Path) -> Dict:
    """Load SPZ file using SPZ Python bindings.
    
    This function loads an SPZ file and converts it to the same format
    as returned by parse_ply_file() for compatibility.
    
    Supports two modes:
    1. Direct import: If SPZ is available in current Python environment
    2. Subprocess: Uses conda environment Python via subprocess
    
    Args:
        spz_file: Path to the SPZ file
        
    Returns:
        Dictionary containing Gaussian data in the same format as parse_ply_file():
        {
            'positions': np.ndarray (N, 3),
            'rotations': np.ndarray (N, 4),  # quaternion (x, y, z, w)
            'scales': np.ndarray (N, 3),
            'colors': np.ndarray (N, 3),  # RGB
            'alphas': np.ndarray (N,),
            'sh_coefficients': np.ndarray (N, M) or None,  # M depends on SH degree
            'sh_degree': int,
            'num_points': int
        }
        
    Raises:
        ImportError: If SPZ module is not available in any environment
        FileNotFoundError: If SPZ file does not exist
        ValueError: If SPZ file cannot be loaded
    """
    # Try direct import first (current environment)
    if SPZ_AVAILABLE:
        return _load_spz_direct(spz_file)
    
    # Fall back to subprocess (conda environment)
    spz_python = get_spz_python_path()
    if spz_python:
        return load_spz_file_via_subprocess(spz_file, spz_python)
    
    # No SPZ available
    raise ImportError(
        "SPZ Python bindings not available. "
        "Please install SPZ in conda environment 'spz-env' or set SPZ_PYTHON environment variable."
    )
