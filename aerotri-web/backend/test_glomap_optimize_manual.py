#!/usr/bin/env python3
"""手动测试GLOMAP优化功能的脚本"""
import os
import sys
import subprocess
from pathlib import Path

# Library paths for runtime dependencies
CERES_LIB_PATH = "/root/opt/ceres-2.3-cuda/lib"

def test_glomap_optimize():
    """测试GLOMAP优化"""
    # 设置路径 - 使用新合并的结果（包含2D points）
    input_colmap_path = "/root/work/aerotri-web/data/outputs/b156bd90-2725-409d-862a-166c0cb0096a/merged/sparse/0"
    output_path = "/root/work/aerotri-web/data/outputs/d51667cc-945c-473e-b25a-4546faa10a1d/sparse"
    
    # 验证输入路径
    if not os.path.isdir(input_colmap_path):
        print(f"错误: 输入路径不存在: {input_colmap_path}")
        return 1
    
    # 检查COLMAP文件
    required_files = ["cameras.bin", "images.bin", "points3D.bin"]
    missing_files = []
    for f in required_files:
        if not os.path.exists(os.path.join(input_colmap_path, f)):
            missing_files.append(f)
    
    if missing_files:
        print(f"错误: 缺少COLMAP文件: {missing_files}")
        return 1
    
    print(f"输入COLMAP路径: {input_colmap_path}")
    print(f"输出路径: {output_path}")
    print(f"找到COLMAP文件: {', '.join(required_files)}")
    
    # 创建输出目录
    os.makedirs(output_path, exist_ok=True)
    
    # 构建GLOMAP命令
    cmd = [
        "/usr/local/bin/glomap",
        "mapper_resume",
        "--input_path", input_colmap_path,
        "--output_path", output_path,
        "--output_format", "bin",
        "--GlobalPositioning.use_gpu", "1",
        "--BundleAdjustment.use_gpu", "1",
        "--skip_global_positioning", "0",
        "--skip_bundle_adjustment", "0",
        "--skip_pruning", "0",
        "--GlobalPositioning.optimize_positions", "1",
        "--GlobalPositioning.optimize_points", "1",
        "--GlobalPositioning.optimize_scales", "1",
        "--BundleAdjustment.optimize_rotations", "1",
        "--BundleAdjustment.optimize_translation", "1",
        "--BundleAdjustment.optimize_intrinsics", "1",
        "--BundleAdjustment.optimize_principal_point", "0",
        "--BundleAdjustment.optimize_points", "1",
    ]
    
    print(f"\n执行命令: {' '.join(cmd)}\n")
    print("=" * 80)
    
    try:
        # 设置环境变量（包含库路径）
        env = os.environ.copy()
        current_ld_path = env.get("LD_LIBRARY_PATH", "")
        if CERES_LIB_PATH not in current_ld_path:
            env["LD_LIBRARY_PATH"] = f"{CERES_LIB_PATH}:{current_ld_path}" if current_ld_path else CERES_LIB_PATH
        
        # 运行GLOMAP
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
            env=env  # 使用包含库路径的环境变量
        )
        
        # 实时输出
        if result.stdout:
            print(result.stdout)
        
        if result.returncode == 0:
            print("\n✅ GLOMAP优化成功完成!")
            print(f"结果保存在: {output_path}")
            
            # 检查输出文件
            output_files = ["cameras.bin", "images.bin", "points3D.bin"]
            print("\n检查输出文件:")
            for filename in output_files:
                filepath = os.path.join(output_path, "0", filename)
                if os.path.exists(filepath):
                    size = os.path.getsize(filepath)
                    print(f"  ✓ {filename} ({size:,} bytes)")
                else:
                    print(f"  ✗ {filename} (不存在)")
            
            return 0
        else:
            print(f"\n❌ GLOMAP优化失败，退出码: {result.returncode}")
            return result.returncode
            
    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = test_glomap_optimize()
    sys.exit(exit_code)

