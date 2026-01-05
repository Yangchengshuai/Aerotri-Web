#!/usr/bin/env python3
"""测试 Visionary 前端集成

测试内容:
1. Visionary 库文件是否存在
2. viewer.html 页面是否存在
3. 文件路径和 URL 配置正确性

使用方法:
    python3 test_visionary_integration.py
"""

import os
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, os.path.dirname(__file__))


def test_visionary_files():
    """测试 Visionary 文件是否存在"""
    print("\n" + "="*60)
    print("测试 1: Visionary 文件检查")
    print("="*60)
    
    frontend_public = Path("/root/work/aerotri-web/frontend/public/visionary")
    
    required_files = [
        "visionary-core.umd.js",
        "visionary-core.es.js",
        "viewer.html",
    ]
    
    all_exist = True
    for filename in required_files:
        filepath = frontend_public / filename
        if filepath.exists():
            size = filepath.stat().st_size
            print(f"✓ {filename} 存在 ({size / 1024:.1f} KB)")
        else:
            print(f"✗ {filename} 不存在")
            all_exist = False
    
    return all_exist


def test_viewer_html_content():
    """测试 viewer.html 内容"""
    print("\n" + "="*60)
    print("测试 2: viewer.html 内容检查")
    print("="*60)
    
    viewer_html = Path("/root/work/aerotri-web/frontend/public/visionary/viewer.html")
    
    if not viewer_html.exists():
        print("✗ viewer.html 不存在")
        return False
    
    content = viewer_html.read_text(encoding='utf-8')
    
    required_elements = [
        "visionary-core.es.js",
        "ply_url",
        "App",
        "loadSample",
        "canvas",
    ]
    
    all_found = True
    for element in required_elements:
        if element in content:
            print(f"✓ 找到: {element}")
        else:
            print(f"✗ 未找到: {element}")
            all_found = False
    
    return all_found


def test_api_integration():
    """测试 API 集成"""
    print("\n" + "="*60)
    print("测试 3: API 集成检查")
    print("="*60)
    
    # Check if GaussianSplattingPanel uses Visionary
    panel_vue = Path("/root/work/aerotri-web/frontend/src/components/GaussianSplattingPanel.vue")
    
    if not panel_vue.exists():
        print("✗ GaussianSplattingPanel.vue 不存在")
        return False
    
    content = panel_vue.read_text(encoding='utf-8')
    
    if "visionary/viewer.html" in content:
        print("✓ GaussianSplattingPanel 使用 Visionary viewer")
        return True
    else:
        print("✗ GaussianSplattingPanel 未使用 Visionary viewer")
        return False


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("Visionary 前端集成测试")
    print("="*60)
    
    tests = [
        ("Visionary 文件检查", test_visionary_files),
        ("viewer.html 内容检查", test_viewer_html_content),
        ("API 集成检查", test_api_integration),
    ]
    
    results = []
    for name, test_func in tests:
        try:
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
    exit_code = main()
    sys.exit(exit_code)
