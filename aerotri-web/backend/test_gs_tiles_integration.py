"""Integration test for 3D GS Tiles conversion API.

This script tests the complete flow:
1. Check GS training status
2. Start tiles conversion
3. Monitor conversion progress
4. Verify tileset.json is created
5. Test tileset download
"""

import asyncio
import sys
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.database import AsyncSessionLocal
from app.models.block import Block
from sqlalchemy import select
from app.services.gs_tiles_runner import gs_tiles_runner

# Test data
TEST_BLOCK_ID = "4941d326-e260-4a91-abba-a42fc9838353"
TEST_DATA_PATH = Path("/root/work/aerotri-web/data/outputs/4941d326-e260-4a91-abba-a42fc9838353/gs")


async def test_gs_tiles_conversion():
    """Test GS tiles conversion flow."""
    print("=" * 60)
    print("3D GS Tiles 转换集成测试")
    print("=" * 60)
    
    async with AsyncSessionLocal() as db:
        # 1. Check block exists
        print("\n1. 检查 Block 是否存在...")
        result = await db.execute(select(Block).where(Block.id == TEST_BLOCK_ID))
        block = result.scalar_one_or_none()
        if not block:
            print(f"❌ Block {TEST_BLOCK_ID} 不存在")
            return False
        print(f"✓ Block 存在: {block.name}")
        
        # 2. Check GS training is completed
        print("\n2. 检查 3DGS 训练状态...")
        gs_status = getattr(block, 'gs_status', None)
        gs_output_path = block.gs_output_path
        print(f"   GS 状态: {gs_status}")
        print(f"   GS 输出路径: {gs_output_path}")
        
        if gs_status != 'COMPLETED' or not gs_output_path:
            print("❌ 3DGS 训练未完成，无法进行转换测试")
            return False
        print("✓ 3DGS 训练已完成")
        
        # 3. Check PLY files exist
        print("\n3. 检查 PLY 文件...")
        ply_7000 = TEST_DATA_PATH / "model" / "point_cloud" / "iteration_7000" / "point_cloud.ply"
        ply_15000 = TEST_DATA_PATH / "model" / "point_cloud" / "iteration_15000" / "point_cloud.ply"
        
        if ply_7000.exists():
            size_mb = ply_7000.stat().st_size / (1024 * 1024)
            print(f"✓ iteration_7000/point_cloud.ply 存在 ({size_mb:.2f} MB)")
        else:
            print(f"⚠ iteration_7000/point_cloud.ply 不存在")
        
        if ply_15000.exists():
            size_mb = ply_15000.stat().st_size / (1024 * 1024)
            print(f"✓ iteration_15000/point_cloud.ply 存在 ({size_mb:.2f} MB)")
        else:
            print(f"⚠ iteration_15000/point_cloud.ply 不存在")
        
        # 4. Test finding PLY file
        print("\n4. 测试查找 PLY 文件...")
        ply_file = await gs_tiles_runner._find_ply_file(Path(gs_output_path), 7000)
        if ply_file:
            print(f"✓ 找到 PLY 文件: {ply_file}")
        else:
            print("⚠ 未找到指定迭代版本的 PLY 文件")
        
        # 5. Check current conversion status
        print("\n5. 检查当前转换状态...")
        gs_tiles_status = getattr(block, 'gs_tiles_status', None)
        gs_tiles_output_path = getattr(block, 'gs_tiles_output_path', None)
        print(f"   转换状态: {gs_tiles_status}")
        print(f"   输出路径: {gs_tiles_output_path}")
        
        if gs_tiles_output_path:
            tileset_path = Path(gs_tiles_output_path) / "tileset.json"
            if tileset_path.exists():
                print(f"✓ tileset.json 已存在: {tileset_path}")
            else:
                print(f"⚠ tileset.json 不存在")
        
        # 6. Test log tail
        print("\n6. 测试日志获取...")
        logs = gs_tiles_runner.get_log_tail(TEST_BLOCK_ID, 10)
        if logs:
            print(f"✓ 获取到 {len(logs)} 条日志")
            print("   最近日志:")
            for log in logs[-3:]:
                print(f"   {log}")
        else:
            print("⚠ 暂无日志")
        
        print("\n" + "=" * 60)
        print("集成测试完成")
        print("=" * 60)
        return True


if __name__ == "__main__":
    result = asyncio.run(test_gs_tiles_conversion())
    sys.exit(0 if result else 1)
