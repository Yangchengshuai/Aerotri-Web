"""Unit tests for SPZ loader module.

Tests SPZ file loading using Python bindings.
"""

import pytest
import tempfile
import subprocess
import numpy as np
from pathlib import Path

from app.services.spz_loader import (
    load_spz_file,
    check_spz_available,
    get_spz_python_path
)

# Test data path
TEST_DATA_PATH = Path("/root/work/aerotri-web/data/outputs/4941d326-e260-4a91-abba-a42fc9838353")
TEST_PLY_FILE = TEST_DATA_PATH / "gs/model/point_cloud/iteration_15000/point_cloud.ply"
SPZ_BUILD_DIR = Path("/root/work/aerotri-web/backend/third_party/spz/build")


def get_ply_to_spz_path():
    """Get path to ply_to_spz executable."""
    exe = SPZ_BUILD_DIR / "ply_to_spz"
    if exe.exists():
        return str(exe)
    return None


@pytest.fixture
def test_spz_file():
    """Create a test SPZ file from PLY if available."""
    if not TEST_PLY_FILE.exists():
        pytest.skip(f"Test PLY file not found: {TEST_PLY_FILE}")
    
    ply_to_spz = get_ply_to_spz_path()
    if not ply_to_spz:
        pytest.skip("ply_to_spz executable not found")
    
    # Create temporary SPZ file
    with tempfile.NamedTemporaryFile(suffix='.spz', delete=False) as tmp:
        spz_file = Path(tmp.name)
    
    try:
        # Convert PLY to SPZ
        result = subprocess.run(
            [ply_to_spz, str(TEST_PLY_FILE), str(spz_file)],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            pytest.skip(f"Failed to create test SPZ file: {result.stderr}")
        
        yield spz_file
    finally:
        # Cleanup
        if spz_file.exists():
            spz_file.unlink()


def test_check_spz_available():
    """Test SPZ availability check."""
    available = check_spz_available()
    # This test will pass regardless, but logs the status
    print(f"SPZ Python bindings available: {available}")


def test_get_spz_python_path():
    """Test SPZ Python path detection."""
    python_path = get_spz_python_path()
    if python_path:
        print(f"Found SPZ Python at: {python_path}")
        assert Path(python_path).exists()
    else:
        print("SPZ Python path not found (this is OK if not configured)")


@pytest.mark.skipif(not check_spz_available(), reason="SPZ Python bindings not available")
def test_load_spz_file(test_spz_file):
    """Test loading SPZ file."""
    data = load_spz_file(test_spz_file)
    
    # Verify data structure
    assert 'positions' in data
    assert 'rotations' in data
    assert 'scales' in data
    assert 'colors' in data
    assert 'alphas' in data
    assert 'sh_degree' in data
    assert 'num_points' in data
    
    # Verify data types and shapes
    assert data['positions'].shape[1] == 3
    assert data['rotations'].shape[1] == 4
    assert data['scales'].shape[1] == 3
    assert data['colors'].shape[1] == 3
    assert len(data['alphas'].shape) == 1
    
    # Verify all arrays have same number of points
    num_points = data['num_points']
    assert data['positions'].shape[0] == num_points
    assert data['rotations'].shape[0] == num_points
    assert data['scales'].shape[0] == num_points
    assert data['colors'].shape[0] == num_points
    assert data['alphas'].shape[0] == num_points
    
    print(f"Loaded {num_points} points with SH degree {data['sh_degree']}")


@pytest.mark.skipif(not check_spz_available(), reason="SPZ Python bindings not available")
def test_load_spz_file_nonexistent():
    """Test loading non-existent SPZ file."""
    with pytest.raises(FileNotFoundError):
        load_spz_file(Path("/nonexistent/file.spz"))


@pytest.mark.skipif(not check_spz_available(), reason="SPZ Python bindings not available")
def test_load_spz_file_data_format(test_spz_file):
    """Test that SPZ loader returns data in same format as PLY parser."""
    from app.services.ply_parser import parse_ply_file
    
    # Load using SPZ
    spz_data = load_spz_file(test_spz_file)
    
    # Load using PLY parser (from original PLY)
    ply_data = parse_ply_file(TEST_PLY_FILE)
    
    # Compare structure (not exact values due to compression)
    assert spz_data.keys() == ply_data.keys()
    assert spz_data['num_points'] == ply_data['num_points']
    assert spz_data['sh_degree'] == ply_data['sh_degree']
    
    # Shapes should match
    assert spz_data['positions'].shape == ply_data['positions'].shape
    assert spz_data['rotations'].shape == ply_data['rotations'].shape
    assert spz_data['scales'].shape == ply_data['scales'].shape
    assert spz_data['colors'].shape == ply_data['colors'].shape
    assert spz_data['alphas'].shape == ply_data['alphas'].shape
    
    print("✓ SPZ loader format matches PLY parser format")


@pytest.mark.skipif(not check_spz_available(), reason="SPZ Python bindings not available")
def test_load_spz_coordinate_conversion(test_spz_file):
    """Test coordinate system conversion in SPZ loader."""
    data = load_spz_file(test_spz_file)
    
    # Verify positions are valid (not all zeros)
    positions = data['positions']
    assert positions.max() > 0 or positions.min() < 0, "Positions should not be all zeros"
    
    # Verify rotations are normalized (quaternion length should be ~1.0)
    rotations = data['rotations']
    quat_lengths = np.linalg.norm(rotations, axis=1)
    # Allow some tolerance for floating point errors
    assert np.allclose(quat_lengths, 1.0, atol=0.1), "Rotations should be normalized quaternions"
    
    print("✓ Coordinate conversion validated")
