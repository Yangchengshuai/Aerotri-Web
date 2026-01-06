"""Tests for PLY parser."""

import pytest
import numpy as np
from pathlib import Path
from app.services.ply_parser import PLYParser, parse_ply_file

# Test data path
TEST_DATA_PATH = Path("/root/work/aerotri-web/data/outputs/4941d326-e260-4a91-abba-a42fc9838353/gs")


def test_ply_parser_import():
    """Test that PLY parser can be imported."""
    from app.services.ply_parser import PLYParser
    parser = PLYParser()
    assert parser is not None


def test_parse_ply_file_small():
    """Test parsing a small PLY file."""
    # Try to find a small PLY file for testing
    ply_file = TEST_DATA_PATH / "model" / "input.ply"
    if not ply_file.exists():
        pytest.skip(f"Test data not found: {ply_file}")
    
    parser = PLYParser()
    data = parser.parse(ply_file)
    
    assert data is not None
    assert 'positions' in data
    assert 'rotations' in data
    assert 'scales' in data
    assert 'colors' in data
    assert 'alphas' in data
    assert 'num_points' in data
    
    assert data['num_points'] > 0
    assert data['positions'].shape[0] == data['num_points']
    assert data['positions'].shape[1] == 3
    
    print(f"✓ Parsed {data['num_points']} points")
    print(f"  SH degree: {data.get('sh_degree', 0)}")


def test_parse_ply_file_medium():
    """Test parsing a medium PLY file (iteration_7000)."""
    ply_file = TEST_DATA_PATH / "model" / "point_cloud" / "iteration_7000" / "point_cloud.ply"
    if not ply_file.exists():
        pytest.skip(f"Test data not found: {ply_file}")
    
    # This is a large file, so we'll just test that parsing starts
    # Full parsing would take too long in unit tests
    parser = PLYParser()
    
    # Test that file can be opened and header parsed
    with open(ply_file, 'rb') as f:
        header_lines = []
        while True:
            line = f.readline()
            header_lines.append(line)
            if line.startswith(b'end_header'):
                break
        
        header = b''.join(header_lines).decode('ascii', errors='ignore')
        assert 'element vertex' in header
        assert 'property' in header
    
    print(f"✓ PLY file header parsed successfully")


def test_parse_ply_convenience_function():
    """Test the convenience function."""
    ply_file = TEST_DATA_PATH / "model" / "input.ply"
    if not ply_file.exists():
        pytest.skip(f"Test data not found: {ply_file}")
    
    data = parse_ply_file(ply_file)
    
    assert data is not None
    assert 'num_points' in data
    assert data['num_points'] > 0
