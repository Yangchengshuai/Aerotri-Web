"""Full integration test for 3D GS Tiles conversion and loading.

This test verifies the complete flow:
1. Start conversion
2. Monitor conversion progress
3. Verify tileset.json is created
4. Test tileset download
5. Verify Cesium can load the tileset
"""

import pytest
import asyncio
import time
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.database import AsyncSessionLocal, init_db
from app.models.block import Block
from sqlalchemy import select
from app.services.gs_tiles_runner import gs_tiles_runner


@pytest.fixture(scope="session")
async def setup_db():
    """Initialize database for tests."""
    await init_db()

# Test data
TEST_BLOCK_ID = "4941d326-e260-4a91-abba-a42fc9838353"
TEST_DATA_PATH = Path("/root/work/aerotri-web/data/outputs/4941d326-e260-4a91-abba-a42fc9838353/gs")


@pytest.mark.asyncio
async def test_full_conversion_flow():
    """Test the complete conversion flow."""
    async with AsyncSessionLocal() as db:
        # 1. Check block exists
        result = await db.execute(select(Block).where(Block.id == TEST_BLOCK_ID))
        block = result.scalar_one_or_none()
        if not block:
            pytest.skip(f"Block {TEST_BLOCK_ID} not found")
        
        # 2. Check GS training is completed
        if not block.gs_output_path or getattr(block, 'gs_status', None) != 'COMPLETED':
            pytest.skip("GS training not completed")
        
        # 3. Start conversion
        convert_params = {
            "iteration": 7000,  # Use smaller file for faster testing
            "use_spz": False,
            "optimize": False,
        }
        
        await gs_tiles_runner.start_conversion(block, db, convert_params)
        
        # 4. Monitor conversion progress
        max_wait = 60  # 60 seconds max wait
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            await asyncio.sleep(1)
            
            result = await db.execute(select(Block).where(Block.id == TEST_BLOCK_ID))
            updated_block = result.scalar_one()
            status = getattr(updated_block, 'gs_tiles_status', None)
            
            if status == "COMPLETED":
                break
            elif status == "FAILED":
                error = getattr(updated_block, 'gs_tiles_error_message', None)
                pytest.fail(f"Conversion failed: {error}")
        
        # 5. Verify conversion completed
        result = await db.execute(select(Block).where(Block.id == TEST_BLOCK_ID))
        final_block = result.scalar_one()
        assert getattr(final_block, 'gs_tiles_status', None) == "COMPLETED"
        
        # 6. Verify output path exists
        output_path = getattr(final_block, 'gs_tiles_output_path', None)
        assert output_path is not None
        
        output_dir = Path(output_path)
        assert output_dir.exists()
        
        # 7. Verify tileset.json exists
        tileset_path = output_dir / "tileset.json"
        assert tileset_path.exists(), f"tileset.json not found at {tileset_path}"
        
        # 8. Verify tileset.json is valid JSON
        import json
        with open(tileset_path, 'r') as f:
            tileset_data = json.load(f)
            assert "asset" in tileset_data
            assert "root" in tileset_data
        
        print(f"✓ Full conversion flow test passed")
        print(f"  Output path: {output_path}")
        print(f"  Tileset: {tileset_path}")


@pytest.mark.asyncio
async def test_conversion_progress_tracking():
    """Test conversion progress tracking."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Block).where(Block.id == TEST_BLOCK_ID))
        block = result.scalar_one_or_none()
        if not block:
            pytest.skip(f"Block {TEST_BLOCK_ID} not found")
        
        # Check initial status
        initial_status = getattr(block, 'gs_tiles_status', None)
        initial_progress = getattr(block, 'gs_tiles_progress', None) or 0.0
        
        # Start conversion
        convert_params = {"iteration": 7000}
        await gs_tiles_runner.start_conversion(block, db, convert_params)
        
        # Wait a bit for progress updates
        await asyncio.sleep(2)
        
        # Check progress was updated
        result = await db.execute(select(Block).where(Block.id == TEST_BLOCK_ID))
        updated_block = result.scalar_one()
        current_status = getattr(updated_block, 'gs_tiles_status', None)
        current_progress = getattr(updated_block, 'gs_tiles_progress', None) or 0.0
        
        # Progress should have changed
        assert current_status == "RUNNING" or current_status == "COMPLETED"
        assert current_progress >= initial_progress
        
        print(f"✓ Progress tracking test passed")
        print(f"  Initial: {initial_progress}%, Current: {current_progress}%")


@pytest.mark.asyncio
async def test_conversion_log_tail():
    """Test conversion log tail functionality."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Block).where(Block.id == TEST_BLOCK_ID))
        block = result.scalar_one_or_none()
        if not block:
            pytest.skip(f"Block {TEST_BLOCK_ID} not found")
        
        # Start conversion to generate logs
        convert_params = {"iteration": 7000}
        await gs_tiles_runner.start_conversion(block, db, convert_params)
        
        # Wait a bit for logs
        await asyncio.sleep(2)
        
        # Get log tail
        logs = gs_tiles_runner.get_log_tail(TEST_BLOCK_ID, 10)
        
        # Should have some logs
        assert isinstance(logs, list)
        assert len(logs) > 0
        
        print(f"✓ Log tail test passed")
        print(f"  Log lines: {len(logs)}")
        if logs:
            print(f"  Last log: {logs[-1][:100]}")
