#!/usr/bin/env python3
"""手动测试3DGS训练、渲染、可视化流程

使用方法:
    python3 test_gs_manual.py <block_output_path>

示例:
    python3 test_gs_manual.py /root/work/aerotri-web/data/outputs/4941d326-e260-4a91-abba-a42fc9838353
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

# 从settings导入配置
sys.path.insert(0, os.path.dirname(__file__))
from app.settings import GS_PYTHON, GS_REPO_PATH


def run_command(cmd, cwd=None, env=None, check=True):
    """运行命令并打印输出"""
    print(f"\n{'='*60}")
    print(f"运行命令: {' '.join(cmd)}")
    if cwd:
        print(f"工作目录: {cwd}")
    print(f"{'='*60}\n")
    
    result = subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        capture_output=False,  # 实时输出
        text=True,
        check=check
    )
    return result


def check_dataset(dataset_dir):
    """检查数据集是否准备就绪"""
    print(f"\n检查数据集: {dataset_dir}")
    
    required_dirs = ["images", "sparse/0"]
    for dir_path in required_dirs:
        full_path = os.path.join(dataset_dir, dir_path)
        if not os.path.exists(full_path):
            print(f"❌ 缺少目录: {full_path}")
            return False
        print(f"✓ 找到目录: {full_path}")
    
    # 检查图像文件
    images_dir = os.path.join(dataset_dir, "images")
    image_files = [f for f in os.listdir(images_dir) 
                   if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    if not image_files:
        print(f"❌ 未找到图像文件")
        return False
    print(f"✓ 找到 {len(image_files)} 个图像文件")
    
    # 检查sparse文件
    sparse_dir = os.path.join(dataset_dir, "sparse", "0")
    required_files = ["cameras.bin", "images.bin", "points3D.bin"]
    for fname in required_files:
        fpath = os.path.join(sparse_dir, fname)
        if not os.path.exists(fpath):
            # 尝试.txt版本
            txt_path = fpath.replace(".bin", ".txt")
            if not os.path.exists(txt_path):
                print(f"❌ 缺少文件: {fname} (或 .txt 版本)")
                return False
        print(f"✓ 找到文件: {fname}")
    
    return True


def test_training(dataset_dir, model_dir, gpu_index=0, iterations=7000):
    """测试训练流程"""
    print(f"\n{'='*60}")
    print("开始3DGS训练测试")
    print(f"{'='*60}\n")
    
    # 清理旧的模型目录
    if os.path.exists(model_dir):
        print(f"清理旧的模型目录: {model_dir}")
        shutil.rmtree(model_dir)
    os.makedirs(model_dir, exist_ok=True)
    
    # 构建训练命令
    cmd = [
        GS_PYTHON,
        "train.py",
        "-s", dataset_dir,
        "-m", model_dir,
        "--iterations", str(iterations),
        "--resolution", "-1",  # Default: -1 (use original resolution)
        "--data_device", "cpu",
        "--sh_degree", "3",
    ]
    
    # 设置环境变量
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = str(gpu_index)
    if "TORCH_CUDA_ARCH_LIST" not in env:
        env["TORCH_CUDA_ARCH_LIST"] = "12.0"
    
    # Set PYTHONPATH to include gaussian-splatting and all submodules
    gs_repo_str = str(GS_REPO_PATH)
    submodules = [
        os.path.join(gs_repo_str, "submodules", "diff-gaussian-rasterization"),
        os.path.join(gs_repo_str, "submodules", "simple-knn"),
        os.path.join(gs_repo_str, "submodules", "fused-ssim"),
    ]
    pythonpath_parts = [gs_repo_str] + submodules
    current_pythonpath = env.get("PYTHONPATH", "")
    if current_pythonpath:
        pythonpath_parts.append(current_pythonpath)
    env["PYTHONPATH"] = ":".join(pythonpath_parts)
    
    print(f"Python: {GS_PYTHON}")
    print(f"工作目录: {GS_REPO_PATH}")
    print(f"CUDA_VISIBLE_DEVICES: {gpu_index}")
    print(f"TORCH_CUDA_ARCH_LIST: {env.get('TORCH_CUDA_ARCH_LIST', 'not set')}")
    print(f"PYTHONPATH: {env.get('PYTHONPATH', 'not set')}")
    
    try:
        run_command(cmd, cwd=str(GS_REPO_PATH), env=env, check=True)
        print("\n✓ 训练完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ 训练失败: {e}")
        return False


def check_training_output(model_dir):
    """检查训练输出"""
    print(f"\n{'='*60}")
    print("检查训练输出")
    print(f"{'='*60}\n")
    
    # 检查point_cloud目录
    pc_dir = os.path.join(model_dir, "point_cloud")
    if not os.path.exists(pc_dir):
        print(f"❌ 未找到 point_cloud 目录: {pc_dir}")
        return False
    print(f"✓ 找到 point_cloud 目录: {pc_dir}")
    
    # 查找.ply文件
    ply_files = []
    for root, dirs, files in os.walk(pc_dir):
        for f in files:
            if f.endswith('.ply'):
                ply_files.append(os.path.join(root, f))
    
    if not ply_files:
        print(f"❌ 未找到 .ply 文件")
        return False
    
    print(f"✓ 找到 {len(ply_files)} 个 .ply 文件:")
    for ply in sorted(ply_files):
        size = os.path.getsize(ply)
        print(f"  - {ply} ({size / 1024 / 1024:.2f} MB)")
    
    return True


def test_render(model_dir, output_dir, gpu_index=0):
    """测试渲染（如果render.py存在）"""
    render_script = GS_REPO_PATH / "render.py"
    if not render_script.exists():
        print(f"\n⚠️  未找到 render.py，跳过渲染测试")
        return False
    
    print(f"\n{'='*60}")
    print("测试渲染")
    print(f"{'='*60}\n")
    
    os.makedirs(output_dir, exist_ok=True)
    
    cmd = [
        GS_PYTHON,
        "render.py",
        "-m", model_dir,
        "-o", output_dir,
    ]
    
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = str(gpu_index)
    
    # Set PYTHONPATH to include gaussian-splatting and all submodules
    gs_repo_str = str(GS_REPO_PATH)
    submodules = [
        os.path.join(gs_repo_str, "submodules", "diff-gaussian-rasterization"),
        os.path.join(gs_repo_str, "submodules", "simple-knn"),
        os.path.join(gs_repo_str, "submodules", "fused-ssim"),
    ]
    pythonpath_parts = [gs_repo_str] + submodules
    current_pythonpath = env.get("PYTHONPATH", "")
    if current_pythonpath:
        pythonpath_parts.append(current_pythonpath)
    env["PYTHONPATH"] = ":".join(pythonpath_parts)
    
    try:
        run_command(cmd, cwd=str(GS_REPO_PATH), env=env, check=True)
        print("\n✓ 渲染完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ 渲染失败: {e}")
        return False


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    block_output_path = sys.argv[1]
    if not os.path.exists(block_output_path):
        print(f"❌ 路径不存在: {block_output_path}")
        sys.exit(1)
    
    # 路径设置
    gs_root = os.path.join(block_output_path, "gs")
    dataset_dir = os.path.join(gs_root, "dataset")
    model_dir = os.path.join(gs_root, "model")
    render_dir = os.path.join(gs_root, "render")
    
    print(f"\n{'='*60}")
    print("3DGS手动测试脚本")
    print(f"{'='*60}")
    print(f"Block输出路径: {block_output_path}")
    print(f"GS根目录: {gs_root}")
    print(f"数据集目录: {dataset_dir}")
    print(f"模型目录: {model_dir}")
    print(f"{'='*60}\n")
    
    # 检查配置
    if not os.path.exists(GS_PYTHON):
        print(f"❌ GS_PYTHON不存在: {GS_PYTHON}")
        sys.exit(1)
    if not os.path.exists(GS_REPO_PATH):
        print(f"❌ GS_REPO_PATH不存在: {GS_REPO_PATH}")
        sys.exit(1)
    
    print(f"✓ GS_PYTHON: {GS_PYTHON}")
    print(f"✓ GS_REPO_PATH: {GS_REPO_PATH}\n")
    
    # 步骤1: 检查数据集
    if not check_dataset(dataset_dir):
        print("\n❌ 数据集检查失败，请先运行数据集准备")
        sys.exit(1)
    
    # 步骤2: 训练（可选，如果已经训练过可以跳过）
    train_skip = input("\n是否跳过训练？(y/n，默认n): ").strip().lower() == 'y'
    if not train_skip:
        gpu_index = input("GPU索引 (默认0): ").strip() or "0"
        iterations = input("迭代次数 (默认7000): ").strip() or "7000"
        
        if not test_training(dataset_dir, model_dir, int(gpu_index), int(iterations)):
            print("\n❌ 训练失败")
            sys.exit(1)
    else:
        print("\n跳过训练步骤")
    
    # 步骤3: 检查训练输出
    if not check_training_output(model_dir):
        print("\n❌ 训练输出检查失败")
        sys.exit(1)
    
    # 步骤4: 测试渲染（可选）
    test_render_choice = input("\n是否测试渲染？(y/n，默认n): ").strip().lower() == 'y'
    if test_render_choice:
        gpu_index = input("GPU索引 (默认0): ").strip() or "0"
        test_render(model_dir, render_dir, int(gpu_index))
    
    print(f"\n{'='*60}")
    print("✓ 测试完成")
    print(f"{'='*60}\n")
    print(f"训练输出目录: {model_dir}")
    if test_render_choice:
        print(f"渲染输出目录: {render_dir}")


if __name__ == "__main__":
    main()
