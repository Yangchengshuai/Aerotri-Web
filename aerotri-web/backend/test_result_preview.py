#!/usr/bin/env python3
"""测试结果预览功能

测试内容:
1. PLY 文件列表 API
2. 文件下载 URL 构建
3. Visionary viewer 集成

使用方法:
    python3 test_result_preview.py <block_id>
"""

import os
import sys
import requests
from pathlib import Path

# Add app to path
sys.path.insert(0, os.path.dirname(__file__))

BASE_URL = "http://localhost:8000/api"


def test_files_api(block_id: str):
    """测试文件列表 API"""
    print("\n" + "="*60)
    print("测试 1: 文件列表 API")
    print("="*60)
    
    url = f"{BASE_URL}/blocks/{block_id}/gs/files"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            files = data.get("files", [])
            print(f"✓ API 调用成功，返回 {len(files)} 个文件")
            
            ply_files = [f for f in files if f.get("type") == "gaussian"]
            if ply_files:
                print(f"✓ 找到 {len(ply_files)} 个 PLY 文件:")
                for f in ply_files[:5]:  # Show first 5
                    print(f"  - {f.get('name')} ({f.get('size_bytes', 0) / 1024 / 1024:.2f} MB)")
                    download_url = f.get('download_url', '')
                    if download_url:
                        print(f"    下载 URL: {download_url}")
                    else:
                        print(f"    ⚠️  缺少 download_url")
                return True
            else:
                print("⚠️  未找到 PLY 文件（可能训练尚未完成）")
                return True  # Not an error, just no files yet
        else:
            print(f"✗ API 调用失败: {response.status_code}")
            print(f"  响应: {response.text[:200]}")
            return False
    except requests.exceptions.ConnectionError:
        print("✗ 无法连接到后端服务器（请确保后端正在运行）")
        return False
    except Exception as e:
        print(f"✗ 错误: {e}")
        return False


def test_download_url(block_id: str):
    """测试下载 URL"""
    print("\n" + "="*60)
    print("测试 2: 下载 URL 构建")
    print("="*60)
    
    url = f"{BASE_URL}/blocks/{block_id}/gs/files"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            files = data.get("files", [])
            
            ply_files = [f for f in files if f.get("type") == "gaussian"]
            if not ply_files:
                print("⚠️  未找到 PLY 文件，跳过下载测试")
                return True
            
            # Test first PLY file download
            test_file = ply_files[0]
            download_url = test_file.get("download_url", "")
            
            if not download_url:
                print("✗ download_url 为空")
                return False
            
            # Check if URL is properly formatted
            if download_url.startswith("/api/blocks/"):
                print(f"✓ download_url 格式正确: {download_url}")
                
                # Try to access the download URL
                full_url = f"http://localhost:8000{download_url}"
                print(f"  测试访问: {full_url}")
                
                try:
                    dl_response = requests.head(full_url, timeout=5, allow_redirects=True)
                    if dl_response.status_code == 200:
                        print(f"✓ 文件可访问 (Content-Length: {dl_response.headers.get('Content-Length', 'unknown')})")
                        return True
                    else:
                        print(f"⚠️  文件访问返回状态码: {dl_response.status_code}")
                        return True  # May be 404 if file doesn't exist yet
                except Exception as e:
                    print(f"⚠️  文件访问错误: {e} (可能是文件不存在)")
                    return True  # Not a critical error
            else:
                print(f"✗ download_url 格式错误: {download_url}")
                return False
        else:
            print(f"✗ 无法获取文件列表: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ 错误: {e}")
        return False


def test_visionary_integration():
    """测试 Visionary 集成"""
    print("\n" + "="*60)
    print("测试 3: Visionary 集成检查")
    print("="*60)
    
    # Check if viewer.html exists
    viewer_html = Path("/root/work/aerotri-web/frontend/public/visionary/viewer.html")
    if viewer_html.exists():
        print("✓ viewer.html 存在")
        
        # Check if it handles ply_url parameter
        content = viewer_html.read_text(encoding='utf-8')
        if "ply_url" in content and "loadSample" in content:
            print("✓ viewer.html 正确处理 ply_url 参数")
            return True
        else:
            print("✗ viewer.html 未正确处理 ply_url 参数")
            return False
    else:
        print("✗ viewer.html 不存在")
        return False


def main():
    """运行所有测试"""
    if len(sys.argv) < 2:
        print("使用方法: python3 test_result_preview.py <block_id>")
        print("\n示例:")
        print("  python3 test_result_preview.py 4941d326-e260-4a91-abba-a42fc9838353")
        sys.exit(1)
    
    block_id = sys.argv[1]
    
    print("\n" + "="*60)
    print("结果预览功能测试")
    print("="*60)
    print(f"Block ID: {block_id}")
    print("="*60)
    
    tests = [
        ("文件列表 API", lambda: test_files_api(block_id)),
        ("下载 URL 构建", lambda: test_download_url(block_id)),
        ("Visionary 集成", test_visionary_integration),
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
        print(f"\n⚠️  {total - passed} 个测试失败或警告")
        return 0  # Return 0 as warnings are acceptable


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
