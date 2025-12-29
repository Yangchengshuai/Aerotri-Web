#!/usr/bin/env python3
"""手动测试合并功能的脚本"""
import os
import sys
import asyncio
from pathlib import Path

# 添加backend目录到路径
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.services.sfm_merge_service import SFMMergeService


class SimpleTaskContext:
    """简单的任务上下文，用于记录日志"""
    def __init__(self):
        self.log_lines = []
    
    def write_log_line(self, line: str):
        """写入日志行"""
        print(f"[LOG] {line}")
        self.log_lines.append(line)


class MockBlock:
    """模拟Block对象"""
    def __init__(self, output_path: str):
        self.output_path = output_path
        self.id = "test_block"
        self.name = "Test Block"


class MockPartition:
    """模拟BlockPartition对象"""
    def __init__(self, index: int):
        self.index = index
        self.id = f"partition_{index}"
        self.status = "COMPLETED"


async def test_merge():
    """测试合并功能"""
    # 设置路径
    output_dir = "/root/work/aerotri-web/data/outputs/b156bd90-2725-409d-862a-166c0cb0096a"
    merged_sparse_dir = os.path.join(output_dir, "merged", "sparse", "0")
    
    # 创建mock对象
    block = MockBlock(output_dir)
    
    # 检查分区目录
    partitions_dir = os.path.join(output_dir, "partitions")
    if not os.path.exists(partitions_dir):
        print(f"错误: 分区目录不存在: {partitions_dir}")
        return
    
    # 查找所有分区
    partition_dirs = sorted([d for d in os.listdir(partitions_dir) if d.startswith("partition_")])
    if not partition_dirs:
        print(f"错误: 未找到分区目录")
        return
    
    print(f"找到 {len(partition_dirs)} 个分区: {partition_dirs}")
    
    # 创建分区对象
    partitions = []
    for part_dir in partition_dirs:
        part_index = int(part_dir.split("_")[1])
        partitions.append(MockPartition(part_index))
    
    # 创建任务上下文
    ctx = SimpleTaskContext()
    
    # 设置合并策略
    merge_strategy = "sim3_keep_one"
    
    print(f"\n开始合并 {len(partitions)} 个分区...")
    print(f"输出目录: {merged_sparse_dir}")
    print(f"合并策略: {merge_strategy}\n")
    
    try:
        # 调用合并函数（不需要db参数，因为merge_partitions中db参数实际上没有被使用）
        # 但我们需要传递None作为db参数
        await SFMMergeService.merge_partitions(
            block=block,
            partitions=partitions,
            output_sparse_dir=merged_sparse_dir,
            merge_strategy=merge_strategy,
            ctx=ctx,
            db=None,  # 合并函数中db参数实际上没有被使用
        )
        
        print("\n✅ 合并成功完成!")
        print(f"合并结果保存在: {merged_sparse_dir}")
        
        # 检查输出文件
        expected_files = ["cameras.bin", "images.bin", "points3D.bin", 
                         "cameras.txt", "images.txt", "points3D.txt"]
        print("\n检查输出文件:")
        for filename in expected_files:
            filepath = os.path.join(merged_sparse_dir, filename)
            if os.path.exists(filepath):
                size = os.path.getsize(filepath)
                print(f"  ✓ {filename} ({size:,} bytes)")
            else:
                print(f"  ✗ {filename} (不存在)")
        
    except Exception as e:
        print(f"\n❌ 合并失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(test_merge())
    sys.exit(exit_code)



