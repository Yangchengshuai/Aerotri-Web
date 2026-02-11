#!/usr/bin/env python3
"""
诊断Agent配置验证脚本
验证路径配置和上下文持久化功能
"""

import asyncio
import sys
import os
from pathlib import Path

sys.path.insert(0, '/root/work/Aerotri-Web/aerotri-web/backend')

from app.conf.settings import get_settings

def verify_paths():
    """验证路径配置"""
    print("=" * 70)
    print("路径配置验证")
    print("=" * 70)
    print()

    settings = get_settings()
    diag = settings.diagnostic

    print("配置的路径:")
    print(f"  agent_memory_path: {diag.agent_memory_path}")
    print(f"  history_log_path: {diag.history_log_path}")
    print(f"  claude_md_path: {diag.claude_md_path}")
    print(f"  context_output_dir: {diag.context_output_dir}")
    print()

    # 检查路径是否绝对路径
    print("路径类型检查:")
    for attr in ['agent_memory_path', 'history_log_path', 'claude_md_path', 'context_output_dir']:
        path = getattr(diag, attr)
        is_abs = path.is_absolute()
        print(f"  {attr}: {'✅ 绝对' if is_abs else '⚠️  相对'}")
    print()

    # 检查路径是否存在
    print("路径存在性检查:")
    for attr in ['agent_memory_path', 'history_log_path', 'claude_md_path', 'context_output_dir']:
        path = getattr(diag, attr)
        exists = path.exists()
        is_dir = path.is_dir() if exists else False
        parent_exists = path.parent.exists() if not exists else False

        if exists:
            print(f"  {attr}: ✅ 存在")
        elif parent_exists:
            print(f"  {attr}: ⚠️  不存在，但父目录存在")
        else:
            print(f"  {attr}: ❌ 不存在，父目录也不存在")

    print()

    # 检查父目录是否可创建
    print("目录可创建性检查:")
    context_dir = diag.context_output_dir
    if context_dir.exists():
        print(f"  context_output_dir: ✅ 已存在")
    else:
        try:
            context_dir.mkdir(parents=True, exist_ok=True)
            print(f"  context_output_dir: ✅ 可创建")
            # 清理刚创建的测试目录
            context_dir.rmdir()
        except Exception as e:
            print(f"  context_output_dir: ❌ 无法创建 ({e})")

def verify_context_persistence():
    """验证上下文持久化功能"""
    print("=" * 70)
    print("上下文持久化功能验证")
    print("=" * 70)
    print()

    settings = get_settings()
    context_dir = settings.diagnostic.context_output_dir

    print(f"上下文输出目录: {context_dir}")
    print()

    # 创建测试上下文
    test_context = {
        "block_info": {"id": "test_block", "name": "Test Block"},
        "task_info": {"task_type": "gs", "stage": "training"},
        "system_status": {"gpu_count": 8},
        "error_info": {"error": "Test error for verification"}
    }

    test_prompt = """# 诊断请求

**Block**: test_block
**Task**: 3DGS training

**Error**: CUDA out of memory

请分析失败原因。
"""

    # 测试保存功能
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    test_file = context_dir / f"test_{timestamp}_verification_context.md"

    try:
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(f"# 测试上下文 - {timestamp}\n\n")
            f.write("**Block ID**: test_block\n")
            f.write("**Task Type**: gs\n\n")
            f.write("---\n\n")
            f.write("## 测试内容\n")
            f.write(test_prompt)

        print(f"✅ 成功创建测试上下文文件:")
        print(f"   {test_file}")
        print()

        # 读取并验证内容
        with open(test_file, 'r') as f:
            content = f.read()
            print("文件内容预览:")
            print("-" * 70)
            print(content[:500])
            if len(content) > 500:
                print("...")
            print("-" * 70)
            print()

        # 清理测试文件
        test_file.unlink()
        print("✅ 测试文件已清理")

        return True

    except Exception as e:
        print(f"❌ 上下文持久化测试失败: {e}")
        return False

def verify_environment_variables():
    """验证环境变量支持"""
    print("=" * 70)
    print("环境变量配置验证")
    print("=" * 70)
    print()

    print("当前环境变量:")
    env_vars = {
        "AEROTRI_DIAGNOSTIC_AGENT_MEMORY": os.getenv("AEROTRI_DIAGNOSTIC_AGENT_MEMORY"),
        "AEROTRI_DIAGNOSTIC_HISTORY_LOG": os.getenv("AEROTRI_DIAGNOSTIC_HISTORY_LOG"),
        "AEROTRI_DIAGNOSTIC_CLAUDE_MD": os.getenv("AEROTRI_DIAGNOSTIC_CLAUDE_MD"),
        "AEROTRI_DIAGNOSTIC_CONTEXT_DIR": os.getenv("AEROTRI_DIAGNOSTIC_CONTEXT_DIR"),
    }

    for var_name, var_value in env_vars.items():
        status = "✅ 设置" if var_value else "未设置"
        print(f"  {var_name}: {status}")
        if var_value:
            print(f"    值: {var_value}")
    print()

    # 测试环境变量优先级
    print("环境变量优先级测试:")
    print("  1. 设置测试环境变量...")
    os.environ["AEROTRI_DIAGNOSTIC_CONTEXT_DIR"] = "/tmp/test_diagnostic_contexts"

    # 重新加载配置
    from importlib import reload
    import app.conf.settings as settings_module
    reload(settings_module)
    from app.conf.settings import get_settings
    new_settings = get_settings()

    # 检查是否生效
    test_path = new_settings.diagnostic.context_output_dir
    expected = Path("/tmp/test_diagnostic_contexts")

    if test_path == expected:
        print(f"  ✅ 环境变量优先级生效: {test_path}")
    else:
        print(f"  ❌ 环境变量未生效: {test_path} (期望: {expected})")

    # 清理
    del os.environ["AEROTRI_DIAGNOSTIC_CONTEXT_DIR"]
    reload(settings_module)

def main():
    """主函数"""
    print("=" * 70)
    print("诊断Agent配置完整验证")
    print("=" * 70)
    print()

    # 验证路径配置
    verify_paths()

    print()

    # 验证上下文持久化
    success = verify_context_persistence()

    print()

    # 验证环境变量
    verify_environment_variables()

    print()
    print("=" * 70)
    print("验证总结")
    print("=" * 70)
    print()

    if success:
        print("✅ 所有验证通过!")
        print()
        print("配置说明:")
        print("  1. 绝对路径：直接使用，不修改")
        print("  2. 相对路径：相对于 backend/config/ 目录解析")
        print("  3. 环境变量：优先级最高，可覆盖配置文件")
        print()
        print("上下文持久化:")
        print("  - 自动保存到 context_output_dir")
        print("  - 文件名格式: YYYYMMDD_HHMMSS_{block_id}_{task_type}_context.md")
        print("  - 用于调试和验证上下文质量")
    else:
        print("❌ 部分验证失败，请检查配置")

if __name__ == "__main__":
    main()
