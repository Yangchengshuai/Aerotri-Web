#!/usr/bin/env python3
"""Helper script to load SPZ file in conda environment.

This script is called via subprocess to load SPZ files when SPZ Python bindings
are not available in the main Python environment. It runs in the conda spz-env
environment and outputs the loaded data using numpy.savez for version compatibility.
"""

import sys
import json
import numpy as np
from pathlib import Path
import tempfile

try:
    import spz
except ImportError:
    print("ERROR: SPZ module not available in this Python environment", file=sys.stderr)
    sys.exit(1)


def load_spz_to_dict(spz_file: Path) -> dict:
    """Load SPZ file and convert to dictionary format.
    
    Args:
        spz_file: Path to SPZ file
        
    Returns:
        Dictionary with Gaussian data
    """
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


def main():
    """Main entry point for subprocess call."""
    if len(sys.argv) != 2:
        print("Usage: spz_loader_helper.py <spz_file>", file=sys.stderr)
        sys.exit(1)
    
    spz_file = Path(sys.argv[1])
    
    if not spz_file.exists():
        print(f"ERROR: SPZ file not found: {spz_file}", file=sys.stderr)
        sys.exit(1)
    
    try:
        # Load SPZ file
        data = load_spz_to_dict(spz_file)
        
        # Use numpy.savez to save data to temporary file (avoids pickle version issues)
        # This method is version-independent and works across numpy 1.x and 2.x
        # Output file path to stdout, then main process will load it
        with tempfile.NamedTemporaryFile(mode='w', suffix='.npz', delete=False) as tmp:
            output_file = tmp.name
        
        # Save numpy arrays using numpy.savez (version-independent)
        # This avoids pickle version compatibility issues between numpy 1.x and 2.x
        save_dict = {
            'positions': data['positions'],
            'rotations': data['rotations'],
            'scales': data['scales'],
            'colors': data['colors'],
            'alphas': data['alphas'],
            'sh_degree': np.array([data['sh_degree']], dtype=np.int32),
            'num_points': np.array([data['num_points']], dtype=np.int32),
            'has_sh': np.array([data['sh_coefficients'] is not None], dtype=bool)
        }
        
        # Only include sh_coefficients if it exists
        if data['sh_coefficients'] is not None:
            save_dict['sh_coefficients'] = data['sh_coefficients']
        else:
            # Save empty array as placeholder (will be ignored based on has_sh flag)
            save_dict['sh_coefficients'] = np.array([], dtype=np.float32)
        
        np.savez_compressed(output_file, **save_dict)
        
        # Output file path to stdout (this is the only output on success)
        print(output_file, file=sys.stdout)
        sys.stdout.flush()
        
    except Exception as e:
        # On error, output to stderr and exit with non-zero code
        error_msg = f"ERROR: Failed to load SPZ file: {str(e)}"
        print(error_msg, file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
