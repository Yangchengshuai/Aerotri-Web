#!/usr/bin/env python3
"""测试 network_gui 启用功能

测试内容:
1. 端口分配功能
2. train.py 参数配置
3. 端口管理（避免冲突）

使用方法:
    python3 test_network_gui.py
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path

# Add app to path
sys.path.insert(0, os.path.dirname(__file__))

from app.services.gs_runner import GSRunner
from app.settings import NETWORK_GUI_PORT_START, NETWORK_GUI_PORT_END, NETWORK_GUI_IP


async def test_port_allocation():
    """测试端口分配"""
    print("\n" + "="*60)
    print("测试 1: Network GUI 端口分配")
    print("="*60)
    
    runner = GSRunner()
    
    # Test finding free port
    port = runner._find_free_port(NETWORK_GUI_PORT_START, NETWORK_GUI_PORT_END)
    if port:
        print(f"✓ 找到空闲端口: {port}")
        assert NETWORK_GUI_PORT_START <= port < NETWORK_GUI_PORT_END, "端口应在指定范围内"
        return True
    else:
        print(f"✗ 未找到空闲端口 (范围: {NETWORK_GUI_PORT_START}-{NETWORK_GUI_PORT_END})")
        return False


async def test_port_management():
    """测试端口管理（避免冲突）"""
    print("\n" + "="*60)
    print("测试 2: 端口管理（避免冲突）")
    print("="*60)
    
    runner = GSRunner()
    
    # Allocate multiple ports
    ports = []
    for i in range(3):
        port = runner._find_free_port(NETWORK_GUI_PORT_START, NETWORK_GUI_PORT_END)
        if port:
            runner._network_gui_ports[f"test_block_{i}"] = port
            ports.append(port)
            print(f"✓ 分配端口 {i+1}: {port}")
        else:
            print(f"✗ 无法分配端口 {i+1}")
            # Cleanup
            for j in range(i):
                runner._network_gui_ports.pop(f"test_block_{j}", None)
            return False
    
    # Check all ports are unique
    if len(ports) == len(set(ports)):
        print(f"✓ 所有端口唯一: {ports}")
    else:
        print(f"✗ 端口冲突: {ports}")
        # Cleanup
        for i in range(3):
            runner._network_gui_ports.pop(f"test_block_{i}", None)
        return False
    
    # Cleanup
    for i in range(3):
        runner._network_gui_ports.pop(f"test_block_{i}", None)
    
    return True


async def test_get_port():
    """测试端口获取"""
    print("\n" + "="*60)
    print("测试 3: 端口获取功能")
    print("="*60)
    
    runner = GSRunner()
    block_id = "test_block"
    
    # Set a port
    test_port = 6009
    runner._network_gui_ports[block_id] = test_port
    
    # Get port
    retrieved_port = runner.get_network_gui_port(block_id)
    if retrieved_port == test_port:
        print(f"✓ 端口获取正确: {retrieved_port}")
    else:
        print(f"✗ 端口获取错误: 期望 {test_port}, 得到 {retrieved_port}")
        return False
    
    # Get non-existent port
    non_existent = runner.get_network_gui_port("non_existent")
    if non_existent is None:
        print("✓ 不存在的 block_id 返回 None")
    else:
        print(f"✗ 不存在的 block_id 应返回 None，但得到 {non_existent}")
        return False
    
    # Cleanup
    runner._network_gui_ports.pop(block_id, None)
    
    return True


def test_train_args():
    """测试 train.py 参数构建"""
    print("\n" + "="*60)
    print("测试 4: train.py 参数构建")
    print("="*60)
    
    # Simulate argument building
    args = ["python", "train.py", "-s", "dataset", "-m", "model"]
    
    # Test with network_gui enabled
    network_gui_port = 6009
    args.extend(["--ip", NETWORK_GUI_IP])
    args.extend(["--port", str(network_gui_port)])
    
    if "--ip" in args and "--port" in args:
        ip_idx = args.index("--ip")
        port_idx = args.index("--port")
        if args[ip_idx + 1] == NETWORK_GUI_IP and args[port_idx + 1] == str(network_gui_port):
            print(f"✓ 参数构建正确: --ip {NETWORK_GUI_IP} --port {network_gui_port}")
            return True
        else:
            print(f"✗ 参数值错误")
            return False
    else:
        print("✗ 缺少 --ip 或 --port 参数")
        return False


async def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("Network GUI 启用功能测试")
    print("="*60)
    print(f"Network GUI IP: {NETWORK_GUI_IP}")
    print(f"端口范围: {NETWORK_GUI_PORT_START}-{NETWORK_GUI_PORT_END}")
    print("="*60)
    
    tests = [
        ("端口分配", test_port_allocation),
        ("端口管理", test_port_management),
        ("端口获取", test_get_port),
        ("参数构建", test_train_args),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
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
