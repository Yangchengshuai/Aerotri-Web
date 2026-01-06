"""Tests for 3D GS Tiles conversion API."""

import pytest
import asyncio
from fastapi.testclient import TestClient
from pathlib import Path
import json

# Test data path
TEST_DATA_PATH = Path("/root/work/aerotri-web/data/outputs/4941d326-e260-4a91-abba-a42fc9838353/gs")


@pytest.fixture(scope="session")
def init_db():
    """Initialize database for tests."""
    from app.models.database import init_db
    asyncio.run(init_db())


@pytest.fixture
def client(init_db):
    """Create test client."""
    from app.main import app
    return TestClient(app)


@pytest.fixture
def test_block_id():
    """Test block ID with GS training completed."""
    return "4941d326-e260-4a91-abba-a42fc9838353"


def test_gs_tiles_status_not_started(client, test_block_id):
    """Test getting GS tiles status when not started."""
    response = client.get(f"/api/blocks/{test_block_id}/gs/tiles/status")
    # Block might not exist in test DB, so 404 is acceptable
    if response.status_code == 404:
        pytest.skip(f"Block {test_block_id} not found in test database")
    assert response.status_code == 200, f"Unexpected status: {response.status_code}, response: {response.text}"
    data = response.json()
    assert data["block_id"] == test_block_id
    assert data.get("gs_tiles_status") in [None, "NOT_STARTED"]


def test_gs_tiles_convert_small_file(client, test_block_id):
    """Test converting small PLY file (iteration_7000)."""
    # Check if test data exists
    ply_file = TEST_DATA_PATH / "model" / "point_cloud" / "iteration_7000" / "point_cloud.ply"
    if not ply_file.exists():
        pytest.skip(f"Test data not found: {ply_file}")
    
    # Start conversion
    response = client.post(
        f"/api/blocks/{test_block_id}/gs/tiles/convert",
        json={
            "iteration": 7000,
            "use_spz": False,
            "optimize": False,
        }
    )
    if response.status_code == 404:
        pytest.skip(f"Block {test_block_id} not found in test database")
    assert response.status_code == 202
    data = response.json()
    assert data["block_id"] == test_block_id
    assert data.get("gs_tiles_status") == "RUNNING"


def test_gs_tiles_convert_large_file(client, test_block_id):
    """Test converting large PLY file (iteration_15000)."""
    # Check if test data exists
    ply_file = TEST_DATA_PATH / "model" / "point_cloud" / "iteration_15000" / "point_cloud.ply"
    if not ply_file.exists():
        pytest.skip(f"Test data not found: {ply_file}")
    
    # Start conversion
    response = client.post(
        f"/api/blocks/{test_block_id}/gs/tiles/convert",
        json={
            "iteration": 15000,
            "use_spz": False,
            "optimize": False,
        }
    )
    if response.status_code == 404:
        pytest.skip(f"Block {test_block_id} not found in test database")
    assert response.status_code == 202
    data = response.json()
    assert data["block_id"] == test_block_id
    assert data.get("gs_tiles_status") == "RUNNING"


def test_gs_tiles_files_list(client, test_block_id):
    """Test listing GS tiles files."""
    response = client.get(f"/api/blocks/{test_block_id}/gs/tiles/files")
    if response.status_code == 404:
        pytest.skip(f"Block {test_block_id} not found in test database")
    assert response.status_code == 200
    data = response.json()
    assert "files" in data
    assert isinstance(data["files"], list)


def test_gs_tiles_tileset_url(client, test_block_id):
    """Test getting tileset URL."""
    # This will fail if conversion not completed, which is expected
    response = client.get(f"/api/blocks/{test_block_id}/gs/tiles/tileset_url")
    # Should return 404 if not converted yet
    if response.status_code == 404:
        assert "not found" in response.json()["detail"].lower()
    else:
        assert response.status_code == 200
        data = response.json()
        assert "tileset_url" in data
        assert "tileset.json" in data["tileset_url"]


def test_gs_tiles_log_tail(client, test_block_id):
    """Test getting conversion log tail."""
    response = client.get(f"/api/blocks/{test_block_id}/gs/tiles/log_tail")
    if response.status_code == 404:
        pytest.skip(f"Block {test_block_id} not found in test database")
    assert response.status_code == 200
    data = response.json()
    assert data["block_id"] == test_block_id
    assert "lines" in data
    assert isinstance(data["lines"], list)


def test_gs_tiles_download_tileset(client, test_block_id):
    """Test downloading tileset.json."""
    # This will fail if conversion not completed, which is expected
    response = client.get(
        f"/api/blocks/{test_block_id}/gs/tiles/download",
        params={"file": "tileset.json"}
    )
    if response.status_code == 404:
        # Expected if not converted yet
        assert "not found" in response.json()["detail"].lower()
    else:
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        data = json.loads(response.text)
        assert "asset" in data
        assert "root" in data
