"""Integration tests for SPZ library.

Tests SPZ compression and decompression using CLI tools.
"""

import pytest
import subprocess
import os
from pathlib import Path

# Test data path
TEST_DATA_PATH = Path("/root/work/aerotri-web/data/outputs/4941d326-e260-4a91-abba-a42fc9838353/gs")
SPZ_BUILD_DIR = Path("/root/work/aerotri-web/backend/third_party/spz/build")


def get_ply_to_spz_path():
    """Get path to ply_to_spz executable."""
    exe = SPZ_BUILD_DIR / "ply_to_spz"
    if exe.exists():
        return str(exe)
    # Try install directory
    install_exe = SPZ_BUILD_DIR / "install" / "bin" / "ply_to_spz"
    if install_exe.exists():
        return str(install_exe)
    return None


def get_spz_to_ply_path():
    """Get path to spz_to_ply executable."""
    exe = SPZ_BUILD_DIR / "spz_to_ply"
    if exe.exists():
        return str(exe)
    # Try install directory
    install_exe = SPZ_BUILD_DIR / "install" / "bin" / "spz_to_ply"
    if install_exe.exists():
        return str(install_exe)
    return None


def test_ply_to_spz_executable_exists():
    """Test that ply_to_spz executable exists."""
    exe_path = get_ply_to_spz_path()
    assert exe_path is not None, "ply_to_spz executable not found"
    assert os.path.exists(exe_path), f"ply_to_spz not found at {exe_path}"
    assert os.access(exe_path, os.X_OK), f"ply_to_spz is not executable"


def test_spz_to_ply_executable_exists():
    """Test that spz_to_ply executable exists."""
    exe_path = get_spz_to_ply_path()
    assert exe_path is not None, "spz_to_ply executable not found"
    assert os.path.exists(exe_path), f"spz_to_ply not found at {exe_path}"


def test_ply_to_spz_conversion():
    """Test PLY to SPZ conversion."""
    # Check if test data exists
    ply_file = TEST_DATA_PATH / "model" / "point_cloud" / "iteration_7000" / "point_cloud.ply"
    if not ply_file.exists():
        pytest.skip(f"Test data not found: {ply_file}")
    
    ply_to_spz = get_ply_to_spz_path()
    if not ply_to_spz:
        pytest.skip("ply_to_spz executable not found")
    
    # Create temporary output file
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.spz', delete=False) as tmp:
        spz_file = tmp.name
    
    try:
        # Run conversion
        result = subprocess.run(
            [ply_to_spz, str(ply_file), spz_file],
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout
        )
        
        assert result.returncode == 0, f"Conversion failed: {result.stderr}"
        assert os.path.exists(spz_file), "SPZ file was not created"
        
        # Check file size (should be smaller)
        ply_size = os.path.getsize(ply_file)
        spz_size = os.path.getsize(spz_file)
        compression_ratio = ply_size / spz_size if spz_size > 0 else 0
        
        print(f"PLY size: {ply_size / (1024*1024):.2f} MB")
        print(f"SPZ size: {spz_size / (1024*1024):.2f} MB")
        print(f"Compression ratio: {compression_ratio:.2f}x")
        
        # SPZ should be significantly smaller (at least 5x compression expected)
        assert compression_ratio > 5, f"Compression ratio too low: {compression_ratio:.2f}x"
        
    finally:
        # Cleanup
        if os.path.exists(spz_file):
            os.unlink(spz_file)


def test_spz_roundtrip():
    """Test SPZ roundtrip conversion (PLY → SPZ → PLY)."""
    # Check if test data exists
    ply_file = TEST_DATA_PATH / "model" / "point_cloud" / "iteration_7000" / "point_cloud.ply"
    if not ply_file.exists():
        pytest.skip(f"Test data not found: {ply_file}")
    
    ply_to_spz = get_ply_to_spz_path()
    spz_to_ply = get_spz_to_ply_path()
    
    if not ply_to_spz or not spz_to_ply:
        pytest.skip("SPZ executables not found")
    
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.spz', delete=False) as tmp1, \
         tempfile.NamedTemporaryFile(suffix='.ply', delete=False) as tmp2:
        spz_file = tmp1.name
        ply_output = tmp2.name
    
    try:
        # PLY → SPZ
        result1 = subprocess.run(
            [ply_to_spz, str(ply_file), spz_file],
            capture_output=True,
            text=True,
            timeout=300
        )
        assert result1.returncode == 0, f"PLY → SPZ failed: {result1.stderr}"
        
        # SPZ → PLY
        result2 = subprocess.run(
            [spz_to_ply, spz_file, ply_output],
            capture_output=True,
            text=True,
            timeout=300
        )
        assert result2.returncode == 0, f"SPZ → PLY failed: {result2.stderr}"
        
        # Verify output file exists
        assert os.path.exists(ply_output), "Roundtrip PLY file was not created"
        
        print(f"✓ Roundtrip conversion successful")
        print(f"  Original: {os.path.getsize(ply_file) / (1024*1024):.2f} MB")
        print(f"  SPZ: {os.path.getsize(spz_file) / (1024*1024):.2f} MB")
        print(f"  Reconstructed: {os.path.getsize(ply_output) / (1024*1024):.2f} MB")
        
    finally:
        # Cleanup
        for f in [spz_file, ply_output]:
            if os.path.exists(f):
                os.unlink(f)
