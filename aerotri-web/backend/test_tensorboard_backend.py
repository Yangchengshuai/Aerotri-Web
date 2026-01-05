#!/usr/bin/env python3
"""测试 TensorBoard 后端服务集成

测试内容:
1. TensorBoard 服务启动/停止
2. 端口分配和管理（避免冲突）
3. 日志文件自动检测
4. 进程生命周期管理（训练开始/结束）
5. 多训练任务并发支持
6. 错误处理和日志记录

使用方法:
    python3 test_tensorboard_backend.py
"""

import asyncio
import os
import sys
import tempfile
import time
from pathlib import Path

# Add app to path
sys.path.insert(0, os.path.dirname(__file__))

from app.services.gs_runner import GSRunner
from app.settings import TENSORBOARD_PATH, TENSORBOARD_PORT_START, TENSORBOARD_PORT_END


async def test_port_allocation():
    """测试端口分配功能"""
    print("\n" + "="*60)
    print("测试 1: 端口分配功能")
    print("="*60)
    
    runner = GSRunner()
    
    # Test finding free port
    port = runner._find_free_port(TENSORBOARD_PORT_START, TENSORBOARD_PORT_END)
    if port:
        print(f"✓ 找到空闲端口: {port}")
        assert TENSORBOARD_PORT_START <= port < TENSORBOARD_PORT_END, "端口应在指定范围内"
        return True
    else:
        print(f"✗ 未找到空闲端口 (范围: {TENSORBOARD_PORT_START}-{TENSORBOARD_PORT_END})")
        return False


async def test_tensorboard_start_stop():
    """测试 TensorBoard 启动和停止"""
    print("\n" + "="*60)
    print("测试 2: TensorBoard 启动和停止")
    print("="*60)
    
    if not os.path.exists(TENSORBOARD_PATH):
        print(f"⚠️  TensorBoard 未找到: {TENSORBOARD_PATH}")
        print("   跳过此测试")
        return True
    
    runner = GSRunner()
    
    # Create temporary model directory
    with tempfile.TemporaryDirectory() as tmpdir:
        model_dir = os.path.join(tmpdir, "model")
        os.makedirs(model_dir, exist_ok=True)
        
        # Create a dummy event file to make TensorBoard happy
        event_file = os.path.join(model_dir, "events.out.tfevents.test")
        with open(event_file, "w") as f:
            f.write("dummy")
        
        block_id = "test_block_1"
        log_lines = []
        
        def log_func(msg):
            log_lines.append(msg)
            print(f"  [LOG] {msg}")
        
        # Test start
        print(f"\n启动 TensorBoard (模型目录: {model_dir})...")
        port = await runner._start_tensorboard(block_id, model_dir, log_func=log_func)
        
        if port:
            print(f"✓ TensorBoard 启动成功，端口: {port}")
            
            # Check if process is running
            proc = runner._tensorboard_processes.get(block_id)
            if proc and proc.returncode is None:
                print("✓ TensorBoard 进程正在运行")
            else:
                print("✗ TensorBoard 进程未运行或已退出")
                return False
            
            # Wait a bit for TensorBoard to fully start
            await asyncio.sleep(2)
            
            # Test get port
            retrieved_port = runner.get_tensorboard_port(block_id)
            if retrieved_port == port:
                print(f"✓ 端口获取正确: {retrieved_port}")
            else:
                print(f"✗ 端口获取错误: 期望 {port}, 得到 {retrieved_port}")
                return False
            
            # Test stop
            print(f"\n停止 TensorBoard...")
            await runner._stop_tensorboard(block_id, log_func=log_func)
            
            # Wait for process to stop
            await asyncio.sleep(1)
            
            # Check if process is stopped
            proc = runner._tensorboard_processes.get(block_id)
            if proc is None:
                print("✓ TensorBoard 进程已停止")
            else:
                print("✗ TensorBoard 进程仍在运行")
                return False
            
            return True
        else:
            print("✗ TensorBoard 启动失败")
            return False


async def test_multiple_instances():
    """测试多个 TensorBoard 实例（端口管理）"""
    print("\n" + "="*60)
    print("测试 3: 多实例端口管理")
    print("="*60)
    
    if not os.path.exists(TENSORBOARD_PATH):
        print(f"⚠️  TensorBoard 未找到: {TENSORBOARD_PATH}")
        print("   跳过此测试")
        return True
    
    runner = GSRunner()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        instances = []
        
        # Start multiple TensorBoard instances
        for i in range(3):
            model_dir = os.path.join(tmpdir, f"model_{i}")
            os.makedirs(model_dir, exist_ok=True)
            
            # Create dummy event file
            event_file = os.path.join(model_dir, "events.out.tfevents.test")
            with open(event_file, "w") as f:
                f.write("dummy")
            
            block_id = f"test_block_{i}"
            port = await runner._start_tensorboard(block_id, model_dir)
            
            if port:
                instances.append((block_id, port))
                print(f"✓ 实例 {i}: block_id={block_id}, port={port}")
            else:
                print(f"✗ 实例 {i}: 启动失败")
                # Clean up
                for bid, _ in instances:
                    await runner._stop_tensorboard(bid)
                return False
        
        # Check all ports are different
        ports = [p for _, p in instances]
        if len(ports) == len(set(ports)):
            print(f"✓ 所有端口唯一: {ports}")
        else:
            print(f"✗ 端口冲突: {ports}")
            # Clean up
            for bid, _ in instances:
                await runner._stop_tensorboard(bid)
            return False
        
        # Clean up
        print("\n清理所有实例...")
        for block_id, port in instances:
            await runner._stop_tensorboard(block_id)
            print(f"  停止 {block_id} (port {port})")
        
        await asyncio.sleep(1)
        
        # Verify all stopped
        all_stopped = all(
            runner._tensorboard_processes.get(bid) is None
            for bid, _ in instances
        )
        if all_stopped:
            print("✓ 所有实例已停止")
            return True
        else:
            print("✗ 部分实例未停止")
            return False


async def test_error_handling():
    """测试错误处理"""
    print("\n" + "="*60)
    print("测试 4: 错误处理")
    print("="*60)
    
    runner = GSRunner()
    
    # Test with non-existent directory
    block_id = "test_error"
    non_existent_dir = "/tmp/non_existent_tensorboard_test_dir_12345"
    
    log_lines = []
    def log_func(msg):
        log_lines.append(msg)
        print(f"  [LOG] {msg}")
    
    port = await runner._start_tensorboard(block_id, non_existent_dir, log_func=log_func)
    
    if port is None:
        print("✓ 正确处理了不存在的目录（返回 None）")
    else:
        print("✗ 应该返回 None 对于不存在的目录")
        await runner._stop_tensorboard(block_id)
        return False
    
    return True


async def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("TensorBoard 后端服务集成测试")
    print("="*60)
    print(f"TensorBoard 路径: {TENSORBOARD_PATH}")
    print(f"端口范围: {TENSORBOARD_PORT_START}-{TENSORBOARD_PORT_END}")
    print("="*60)
    
    tests = [
        ("端口分配", test_port_allocation),
        ("TensorBoard 启动/停止", test_tensorboard_start_stop),
        ("多实例端口管理", test_multiple_instances),
        ("错误处理", test_error_handling),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ 测试 '{name}' 抛出异常: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Summary
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{status}: {name}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n✓ 所有测试通过！")
        return 0
    else:
        print(f"\n✗ {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
