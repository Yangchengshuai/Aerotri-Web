"""Tests for glTF Gaussian builder."""

import pytest
import json
import numpy as np
from pathlib import Path
from app.services.gltf_gaussian_builder import GLTFGaussianBuilder, build_gltf_gaussian
from app.services.ply_parser import parse_ply_file

# Test data path
TEST_DATA_PATH = Path("/root/work/aerotri-web/data/outputs/4941d326-e260-4a91-abba-a42fc9838353/gs")


def test_gltf_builder_import():
    """Test that glTF builder can be imported."""
    from app.services.gltf_gaussian_builder import GLTFGaussianBuilder
    builder = GLTFGaussianBuilder()
    assert builder is not None


def test_gltf_builder_basic():
    """Test basic glTF building with synthetic data."""
    builder = GLTFGaussianBuilder()
    
    # Create synthetic data
    num_points = 100
    positions = np.random.rand(num_points, 3).astype(np.float32)
    rotations = np.random.rand(num_points, 4).astype(np.float32)
    # Normalize quaternions
    for i in range(num_points):
        norm = np.linalg.norm(rotations[i])
        if norm > 0:
            rotations[i] /= norm
    scales = np.random.rand(num_points, 3).astype(np.float32)
    colors = np.random.rand(num_points, 3).astype(np.float32)
    alphas = np.random.rand(num_points).astype(np.float32)
    
    builder.set_gaussian_data(
        positions=positions,
        rotations=rotations,
        scales=scales,
        colors=colors,
        alphas=alphas,
        sh_degree=0
    )
    
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.gltf', delete=False) as tmp:
        output_path = Path(tmp.name)
    
    try:
        result_path = builder.build_gltf(output_path, use_glb=False)
        assert result_path.exists(), "glTF file was not created"
        
        # Verify JSON structure
        with open(result_path, 'r', encoding='utf-8') as f:
            gltf_data = json.load(f)
        
        assert 'asset' in gltf_data
        assert 'extensionsUsed' in gltf_data
        assert 'KHR_gaussian_splatting' in gltf_data['extensionsUsed']
        assert 'meshes' in gltf_data
        assert len(gltf_data['meshes']) > 0
        assert 'extensions' in gltf_data['meshes'][0]
        assert 'KHR_gaussian_splatting' in gltf_data['meshes'][0]['extensions']
        
        print(f"✓ glTF file created: {result_path}")
        print(f"  Points: {num_points}")
        
    finally:
        if output_path.exists():
            output_path.unlink()
        # Clean up buffers directory if created
        buffers_dir = output_path.parent / f"{output_path.stem}_buffers"
        if buffers_dir.exists():
            import shutil
            shutil.rmtree(buffers_dir)


def test_gltf_builder_with_ply_data():
    """Test glTF building with actual PLY data."""
    ply_file = TEST_DATA_PATH / "model" / "input.ply"
    if not ply_file.exists():
        pytest.skip(f"Test data not found: {ply_file}")
    
    # Parse PLY
    gaussian_data = parse_ply_file(ply_file)
    
    # Build glTF
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.gltf', delete=False) as tmp:
        output_path = Path(tmp.name)
    
    try:
        result_path = build_gltf_gaussian(gaussian_data, output_path, use_glb=False)
        assert result_path.exists(), "glTF file was not created"
        
        # Verify structure
        with open(result_path, 'r', encoding='utf-8') as f:
            gltf_data = json.load(f)
        
        assert 'KHR_gaussian_splatting' in gltf_data['extensionsUsed']
        assert gltf_data['meshes'][0]['extensions']['KHR_gaussian_splatting']['positions'] is not None
        
        print(f"✓ glTF created from PLY: {result_path}")
        print(f"  Points: {gaussian_data['num_points']}")
        
    finally:
        if output_path.exists():
            output_path.unlink()
        buffers_dir = output_path.parent / f"{output_path.stem}_buffers"
        if buffers_dir.exists():
            import shutil
            shutil.rmtree(buffers_dir)


def test_gltf_builder_glb_format():
    """Test GLB format generation."""
    builder = GLTFGaussianBuilder()
    
    num_points = 50
    positions = np.random.rand(num_points, 3).astype(np.float32)
    rotations = np.random.rand(num_points, 4).astype(np.float32)
    for i in range(num_points):
        norm = np.linalg.norm(rotations[i])
        if norm > 0:
            rotations[i] /= norm
    scales = np.random.rand(num_points, 3).astype(np.float32)
    colors = np.random.rand(num_points, 3).astype(np.float32)
    alphas = np.random.rand(num_points).astype(np.float32)
    
    builder.set_gaussian_data(
        positions=positions,
        rotations=rotations,
        scales=scales,
        colors=colors,
        alphas=alphas
    )
    
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.glb', delete=False) as tmp:
        output_path = Path(tmp.name)
    
    try:
        result_path = builder.build_gltf(output_path, use_glb=True)
        assert result_path.exists(), "GLB file was not created"
        
        # Verify GLB magic number
        with open(result_path, 'rb') as f:
            magic = f.read(4)
            assert magic == b'glTF', "Invalid GLB magic number"
        
        print(f"✓ GLB file created: {result_path}")
        
    finally:
        if output_path.exists():
            output_path.unlink()
