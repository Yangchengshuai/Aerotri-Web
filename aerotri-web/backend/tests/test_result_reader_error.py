"""Tests for reprojection error computation in ResultReader."""
import pytest
import os
import json
import tempfile
import shutil
from pathlib import Path
from app.services.result_reader import ResultReader


@pytest.fixture
def sample_colmap_data(tmp_path):
    """Create a minimal COLMAP dataset for testing."""
    sparse_dir = tmp_path / "sparse" / "0"
    sparse_dir.mkdir(parents=True)
    
    # Create cameras.txt
    cameras_txt = sparse_dir / "cameras.txt"
    cameras_txt.write_text("""# Camera list with one line of data per camera:
#   CAMERA_ID, MODEL, WIDTH, HEIGHT, PARAMS[]
# Number of cameras: 1
1 PINHOLE 1920 1080 1000.0 1000.0 960.0 540.0
""")
    
    # Create points3D.txt
    points3d_txt = sparse_dir / "points3D.txt"
    points3d_txt.write_text("""# 3D point list with one line of data per point:
#   POINT3D_ID, X, Y, Z, R, G, B, ERROR, TRACK[] as (IMAGE_ID, POINT2D_IDX)
# Number of points: 2, mean track length: 2.000000
1 0.0 0.0 5.0 255 0 0 0.5 0 0 1 0
2 1.0 0.0 5.0 0 255 0 0.3 0 1 1 1
""")
    
    # Create images.txt
    images_txt = sparse_dir / "images.txt"
    images_txt.write_text("""# Image list with two lines of data per image:
#   IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME
#   POINTS2D[] as (X, Y, POINT3D_ID)
0 1.0 0.0 0.0 0.0 0.0 0.0 0.0 1 img0.jpg
960.0 540.0 1 1920.0 540.0 2
1 1.0 0.0 0.0 0.0 1.0 0.0 0.0 1 img1.jpg
960.0 540.0 1 1920.0 540.0 2
""")
    
    return str(tmp_path)


def test_compute_error_with_per_image(sample_colmap_data):
    """Test that per-image error computation works correctly."""
    sparse_dir = os.path.join(sample_colmap_data, "sparse", "0")
    cameras_txt = os.path.join(sparse_dir, "cameras.txt")
    images_txt = os.path.join(sparse_dir, "images.txt")
    points3d_txt = os.path.join(sparse_dir, "points3D.txt")
    
    result = ResultReader._compute_mean_reprojection_error_with_per_image(
        cameras_txt, images_txt, points3d_txt
    )
    
    assert result is not None
    assert "mean_reprojection_error" in result
    assert "num_observations" in result
    assert "per_image" in result
    assert isinstance(result["per_image"], dict)
    assert len(result["per_image"]) > 0


def test_error_computation_consistency(sample_colmap_data):
    """Test that global error matches the old computation method."""
    sparse_dir = os.path.join(sample_colmap_data, "sparse", "0")
    cameras_txt = os.path.join(sparse_dir, "cameras.txt")
    images_txt = os.path.join(sparse_dir, "images.txt")
    points3d_txt = os.path.join(sparse_dir, "points3D.txt")
    
    # Compute with per-image
    result_with_per_image = ResultReader._compute_mean_reprojection_error_with_per_image(
        cameras_txt, images_txt, points3d_txt
    )
    
    # Compute with old method (should return same global mean)
    result_old = ResultReader._compute_mean_reprojection_error(
        cameras_txt, images_txt, points3d_txt
    )
    
    assert result_with_per_image is not None
    assert result_old is not None
    # Allow small floating point differences
    assert abs(result_with_per_image["mean_reprojection_error"] - 
               result_old["mean_reprojection_error"]) < 1e-6
    assert result_with_per_image["num_observations"] == result_old["num_observations"]


def test_error_computation_missing_files(tmp_path):
    """Test error handling when files are missing."""
    sparse_dir = tmp_path / "sparse" / "0"
    sparse_dir.mkdir(parents=True)
    
    cameras_txt = str(sparse_dir / "cameras.txt")
    images_txt = str(sparse_dir / "images.txt")
    points3d_txt = str(sparse_dir / "points3D.txt")
    
    # Missing cameras.txt
    result = ResultReader._compute_mean_reprojection_error_with_per_image(
        cameras_txt, images_txt, points3d_txt
    )
    assert result is None
    
    # Create cameras.txt but missing points3D.txt
    Path(cameras_txt).write_text("1 PINHOLE 1920 1080 1000.0 1000.0 960.0 540.0\n")
    result = ResultReader._compute_mean_reprojection_error_with_per_image(
        cameras_txt, images_txt, points3d_txt
    )
    assert result is None


def test_error_computation_empty_observations(tmp_path):
    """Test handling of images with no valid observations."""
    sparse_dir = tmp_path / "sparse" / "0"
    sparse_dir.mkdir(parents=True)
    
    cameras_txt = str(sparse_dir / "cameras.txt")
    cameras_txt_path = Path(cameras_txt)
    cameras_txt_path.write_text("1 PINHOLE 1920 1080 1000.0 1000.0 960.0 540.0\n")
    
    points3d_txt = str(sparse_dir / "points3D.txt")
    points3d_txt_path = Path(points3d_txt)
    points3d_txt_path.write_text("# Empty points\n")
    
    images_txt = str(sparse_dir / "images.txt")
    images_txt_path = Path(images_txt)
    images_txt_path.write_text("0 1.0 0.0 0.0 0.0 0.0 0.0 0.0 1 img0.jpg\n")
    
    result = ResultReader._compute_mean_reprojection_error_with_per_image(
        cameras_txt, images_txt, points3d_txt
    )
    # Should return None when no observations
    assert result is None


def test_cache_mechanism(sample_colmap_data):
    """Test that caching works correctly."""
    sparse_dir = os.path.join(sample_colmap_data, "sparse", "0")
    cameras_txt = os.path.join(sparse_dir, "cameras.txt")
    images_txt = os.path.join(sparse_dir, "images.txt")
    points3d_txt = os.path.join(sparse_dir, "points3D.txt")
    cache_path = os.path.join(sparse_dir, ".reproj_cache.json")
    
    # Remove cache if exists
    if os.path.exists(cache_path):
        os.remove(cache_path)
    
    # First computation (should create cache)
    result1 = ResultReader._compute_mean_reprojection_error_with_cache(
        sparse_dir, cameras_txt, images_txt, points3d_txt
    )
    assert result1 is not None
    assert os.path.exists(cache_path)
    
    # Verify cache content
    with open(cache_path, "r") as f:
        cached = json.load(f)
    assert "signature" in cached
    assert "result" in cached
    assert "per_image" in cached["result"]
    
    # Second computation (should use cache)
    result2 = ResultReader._compute_mean_reprojection_error_with_cache(
        sparse_dir, cameras_txt, images_txt, points3d_txt
    )
    assert result2 is not None
    assert result2["mean_reprojection_error"] == result1["mean_reprojection_error"]
    assert result2["per_image"] == result1["per_image"]


def test_read_cameras_with_error(sample_colmap_data):
    """Test that read_cameras fills error information."""
    cameras = ResultReader.read_cameras(sample_colmap_data)
    
    assert len(cameras) > 0
    # All cameras should have error if computation succeeded
    cameras_with_error = [c for c in cameras if c.mean_reprojection_error is not None]
    # At least some cameras should have error
    assert len(cameras_with_error) > 0 or len(cameras) == 0


def test_read_cameras_error_field_type(sample_colmap_data):
    """Test that error field is correct type."""
    cameras = ResultReader.read_cameras(sample_colmap_data)
    
    for cam in cameras:
        if cam.mean_reprojection_error is not None:
            assert isinstance(cam.mean_reprojection_error, float)
            assert cam.mean_reprojection_error >= 0.0
