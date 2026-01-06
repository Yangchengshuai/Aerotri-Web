"""Tests for 3D GS Tiles conversion runner."""

import pytest
from pathlib import Path
from app.services.gs_tiles_runner import GSTilesRunner, GSTilesProcessError

# Test data path
TEST_DATA_PATH = Path("/root/work/aerotri-web/data/outputs/4941d326-e260-4a91-abba-a42fc9838353/gs")


def test_find_ply_file_iteration_7000():
    """Test finding PLY file for iteration 7000."""
    runner = GSTilesRunner()
    
    # This is an async function, but we can test the logic
    import asyncio
    result = asyncio.run(runner._find_ply_file(TEST_DATA_PATH, 7000))
    
    if TEST_DATA_PATH.exists():
        expected = TEST_DATA_PATH / "model" / "point_cloud" / "iteration_7000" / "point_cloud.ply"
        if expected.exists():
            assert result == expected
        else:
            assert result is None
    else:
        pytest.skip(f"Test data not found: {TEST_DATA_PATH}")


def test_find_ply_file_iteration_15000():
    """Test finding PLY file for iteration 15000."""
    runner = GSTilesRunner()
    
    import asyncio
    result = asyncio.run(runner._find_ply_file(TEST_DATA_PATH, 15000))
    
    if TEST_DATA_PATH.exists():
        expected = TEST_DATA_PATH / "model" / "point_cloud" / "iteration_15000" / "point_cloud.ply"
        if expected.exists():
            assert result == expected
        else:
            assert result is None
    else:
        pytest.skip(f"Test data not found: {TEST_DATA_PATH}")


def test_find_ply_file_latest():
    """Test finding latest PLY file."""
    runner = GSTilesRunner()
    
    import asyncio
    result = asyncio.run(runner._find_ply_file(TEST_DATA_PATH, None))
    
    if TEST_DATA_PATH.exists():
        # Should find the latest iteration
        assert result is not None
        assert result.exists()
        assert result.name == "point_cloud.ply"
    else:
        pytest.skip(f"Test data not found: {TEST_DATA_PATH}")


def test_log_tail():
    """Test getting log tail."""
    runner = GSTilesRunner()
    block_id = "test_block"
    
    # Add some log messages
    runner._log(block_id, "Test message 1")
    runner._log(block_id, "Test message 2")
    runner._log(block_id, "Test message 3")
    
    # Get log tail
    logs = runner.get_log_tail(block_id, 2)
    assert len(logs) == 2
    assert "Test message 3" in logs[-1]
    assert "Test message 2" in logs[0]
