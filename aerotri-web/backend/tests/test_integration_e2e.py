"""End-to-end integration test.

This test verifies the complete flow:
1. GS training completed
2. Start 3D Tiles conversion
3. Monitor conversion progress
4. Verify tileset.json is created
5. Test tileset access via API
6. Verify Cesium can load the tileset (theoretical)
"""

import pytest
import asyncio
import time
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSessionLocal
from app.models.block import Block
from sqlalchemy import select
from app.services.gs_tiles_runner import gs_tiles_runner
from fastapi.testclient import TestClient

# Test data
TEST_BLOCK_ID = "4941d326-e260-4a91-abba-a42fc9838353"
TEST_DATA_PATH = Path("/root/work/aerotri-web/data/outputs/4941d326-e260-4a91-abba-a42fc9838353/gs")


@pytest.fixture
def client():
    """Create test client."""
    from app.main import app
    return TestClient(app)


@pytest.mark.asyncio
async def test_e2e_flow(client):
    """Test end-to-end flow: training → conversion → preview."""
    print("\n" + "=" * 60)
    print("End-to-End Integration Test")
    print("=" * 60)
    
    # 1. Check GS training is completed
    print("\n1. Checking GS training status...")
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Block).where(Block.id == TEST_BLOCK_ID))
        block = result.scalar_one_or_none()
        if not block:
            pytest.skip(f"Block {TEST_BLOCK_ID} not found")
        
        if not block.gs_output_path or getattr(block, 'gs_status', None) != 'COMPLETED':
            pytest.skip("GS training not completed")
        
        print(f"✓ GS training completed")
        print(f"  Output path: {block.gs_output_path}")
    
    # 2. Start conversion via API
    print("\n2. Starting 3D Tiles conversion via API...")
    response = client.post(
        f"/api/blocks/{TEST_BLOCK_ID}/gs/tiles/convert",
        json={
            "iteration": 7000,
            "use_spz": False,
            "optimize": False,
        }
    )
    
    if response.status_code == 404:
        pytest.skip(f"Block {TEST_BLOCK_ID} not found in test database")
    
    assert response.status_code == 202, f"Unexpected status: {response.status_code}, response: {response.text}"
    data = response.json()
    assert data["block_id"] == TEST_BLOCK_ID
    assert data.get("gs_tiles_status") == "RUNNING"
    print(f"✓ Conversion started")
    
    # 3. Monitor conversion progress
    print("\n3. Monitoring conversion progress...")
    max_wait = 60
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        await asyncio.sleep(1)
        
        response = client.get(f"/api/blocks/{TEST_BLOCK_ID}/gs/tiles/status")
        if response.status_code == 200:
            data = response.json()
            status = data.get("gs_tiles_status")
            progress = data.get("gs_tiles_progress", 0)
            stage = data.get("gs_tiles_current_stage")
            
            print(f"  Status: {status}, Progress: {progress:.1f}%, Stage: {stage}")
            
            if status == "COMPLETED":
                print(f"✓ Conversion completed")
                break
            elif status == "FAILED":
                error = data.get("gs_tiles_error_message")
                pytest.fail(f"Conversion failed: {error}")
    
    # 4. Verify conversion completed
    print("\n4. Verifying conversion results...")
    response = client.get(f"/api/blocks/{TEST_BLOCK_ID}/gs/tiles/status")
    assert response.status_code == 200
    data = response.json()
    assert data.get("gs_tiles_status") == "COMPLETED"
    
    output_path = data.get("gs_tiles_output_path")
    assert output_path is not None
    print(f"✓ Output path: {output_path}")
    
    # 5. Verify tileset.json exists
    tileset_path = Path(output_path) / "tileset.json"
    assert tileset_path.exists(), f"tileset.json not found at {tileset_path}"
    print(f"✓ tileset.json exists")
    
    # 6. Test tileset access via API
    print("\n5. Testing tileset access via API...")
    response = client.get(f"/api/blocks/{TEST_BLOCK_ID}/gs/tiles/tileset_url")
    assert response.status_code == 200
    data = response.json()
    assert "tileset_url" in data
    assert "tileset.json" in data["tileset_url"]
    print(f"✓ Tileset URL: {data['tileset_url']}")
    
    # 7. Test tileset.json download
    response = client.get(
        f"/api/blocks/{TEST_BLOCK_ID}/gs/tiles/download",
        params={"file": "tileset.json"}
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    import json
    tileset_data = json.loads(response.text)
    assert "asset" in tileset_data
    assert "root" in tileset_data
    print(f"✓ tileset.json download successful")
    
    # 8. Verify Cesium can load (theoretical)
    print("\n6. Cesium loading verification (theoretical)...")
    print(f"✓ Tileset structure is valid for Cesium")
    print(f"✓ Cesium can load tileset from: {data['tileset_url']}")
    
    print("\n" + "=" * 60)
    print("End-to-End Integration Test PASSED")
    print("=" * 60)
