# RTX 5090 PyTorch 完整修复指南

## 问题诊断

**错误信息**：
```
RuntimeError: CUDA error: no kernel image is available for execution on the device
NVIDIA GeForce RTX 5090 with CUDA capability sm_120 is not compatible with the current PyTorch installation.
```

**根本原因**：
- RTX 5090 使用 Blackwell 架构（sm_120 compute capability）
- 当前 PyTorch 版本不支持 sm_120
- CUDA 扩展未为 sm_120 编译

## 解决方案

根据 [vLLM RTX 5090 配置指南](https://discuss.vllm.ai/t/vllm-on-rtx5090-working-gpu-setup-with-torch-2-9-0-cu128/1492)，有两种方法：

### 方案A：使用 PyTorch 2.9.0 Nightly Wheels（推荐）⭐⭐⭐⭐⭐

**优点**：
- ✅ 快速（10-30分钟）
- ✅ 无需编译 PyTorch
- ✅ 官方维护

**步骤**：

```bash
# 1. 运行自动修复脚本
/root/work/gs_workspace/fix_rtx5090_pytorch.sh

# 脚本会自动：
# - 卸载旧版本 PyTorch
# - 安装 PyTorch 2.9.0+cu128 nightly
# - 重新编译 CUDA 扩展（diff-gaussian-rasterization, simple-knn）
# - 验证安装
```

**手动步骤**（如果脚本失败）：

```bash
source /root/work/gs_workspace/gs_env/bin/activate

# 卸载旧版本
pip uninstall -y torch torchvision torchaudio diff-gaussian-rasterization simple-knn

# 安装 PyTorch 2.9.0 nightly
pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu128

# 设置编译环境变量（关键！）
export TORCH_CUDA_ARCH_LIST="12.0"
export CMAKE_CUDA_ARCHITECTURES=120
export MAX_JOBS=$(nproc)

# 重新编译 CUDA 扩展
cd /root/work/gs_workspace/gaussian-splatting

cd submodules/diff-gaussian-rasterization
pip install -e . --no-build-isolation
cd ../..

cd submodules/simple-knn
pip install -e . --no-build-isolation
cd ../..
```

---

### 方案B：从源码构建 PyTorch（如果 wheels 不可用）⭐⭐⭐

**优点**：
- ✅ 完全控制编译选项
- ✅ 确保 sm_120 支持

**缺点**：
- ❌ 耗时（2-4小时）
- ❌ 需要大量磁盘空间（~20GB）
- ❌ 需要更多依赖

**步骤**：

```bash
# 1. 从源码构建 PyTorch
/root/work/gs_workspace/install_pytorch_from_source.sh

# 2. 然后运行修复脚本重新编译扩展
/root/work/gs_workspace/fix_rtx5090_pytorch.sh
```

**手动步骤**：

```bash
source /root/work/gs_workspace/gs_env/bin/activate

# 克隆 PyTorch
cd /tmp
git clone --recursive https://github.com/pytorch/pytorch.git
cd pytorch
git checkout main  # 或特定 nightly 分支

# 设置编译环境
export TORCH_CUDA_ARCH_LIST="12.0"
export CMAKE_CUDA_ARCHITECTURES=120
export MAX_JOBS=$(nproc)
export USE_CUDA=1
export USE_CUDNN=1

# 构建并安装
pip install ninja pyyaml setuptools wheel
python setup.py build develop

# 然后重新编译 3DGS 扩展（见方案A）
```

---

## 关键环境变量

编译 CUDA 扩展时**必须**设置：

```bash
export TORCH_CUDA_ARCH_LIST="12.0"        # Blackwell sm_120
export CMAKE_CUDA_ARCHITECTURES=120      # CMake CUDA 架构
export MAX_JOBS=$(nproc)                 # 并行编译任务数
```

**为什么重要**：
- 没有这些变量，CUDA 扩展会为默认架构（通常是 sm_75/sm_80）编译
- RTX 5090 需要 sm_120，否则会出现 "no kernel image" 错误

---

## 验证安装

修复后运行验证：

```python
import torch
import sys
sys.path.insert(0, '/root/work/gs_workspace/gaussian-splatting')

# 1. 检查 PyTorch
print(f"PyTorch: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")

if torch.cuda.is_available():
    print(f"Device: {torch.cuda.get_device_name(0)}")
    capability = torch.cuda.get_device_capability(0)
    print(f"Compute capability: {capability[0]}.{capability[1]}")
    
    # 2. 测试 CUDA 操作
    x = torch.randn(10, 10).cuda()
    y = torch.randn(10, 10).cuda()
    z = torch.matmul(x, y)
    print("✓ CUDA operations working")
    
    # 3. 测试 3DGS 扩展
    try:
        import diff_gaussian_rasterization
        print("✓ diff-gaussian-rasterization imported")
        
        # 尝试使用（需要正确的上下文）
        print("✓ All checks passed!")
    except Exception as e:
        print(f"✗ Extension import failed: {e}")
```

---

## 训练时设置

即使修复后，训练时也建议设置环境变量：

```bash
# 在 gs_runner.py 中，训练命令前添加：
env["TORCH_CUDA_ARCH_LIST"] = "12.0"
env["CUDA_LAUNCH_BLOCKING"] = "1"  # 用于调试（可选）
```

---

## 常见问题

### Q1: 编译失败 "f16 arithmetic and compare instructions"

**A**: 这通常意味着：
1. CUDA 版本不匹配（需要 12.8+）
2. 环境变量未正确设置
3. 尝试设置：`export TORCH_CUDA_ARCH_LIST="12.0+PTX"`

### Q2: "no kernel image" 错误仍然存在

**A**: 检查：
1. CUDA 扩展是否重新编译（检查 `.so` 文件时间戳）
2. 运行时是否设置了 `TORCH_CUDA_ARCH_LIST`
3. PyTorch 版本是否为 2.9.0+cu128

### Q3: 编译时间太长

**A**: 
- 减少 `MAX_JOBS`（例如 `export MAX_JOBS=4`）
- 使用预编译 wheels（方案A）而不是源码构建
- 确保有足够的 RAM（建议 32GB+）

### Q4: 磁盘空间不足

**A**:
- PyTorch 源码构建需要 ~20GB
- 清理旧构建：`rm -rf /tmp/pytorch/build`
- 使用预编译 wheels 可节省空间

---

## 性能参考

根据 vLLM 测试（类似场景）：
- **启动时间**：~72秒（首次加载和编译）
- **训练速度**：取决于模型大小和参数
- **内存使用**：正常（与 PyTorch 2.4 类似）

---

## 参考链接

- [vLLM RTX 5090 配置指南](https://discuss.vllm.ai/t/vllm-on-rtx5090-working-gpu-setup-with-torch-2-9-0-cu128/1492)
- [PyTorch 官方安装指南](https://pytorch.org/get-started/locally/)
- [CUDA Compute Capability](https://developer.nvidia.com/cuda-gpus)

---

## 快速开始

**最简单的方法**：

```bash
# 一键修复（推荐）
/root/work/gs_workspace/fix_rtx5090_pytorch.sh

# 如果失败，尝试从源码构建
/root/work/gs_workspace/install_pytorch_from_source.sh
/root/work/gs_workspace/fix_rtx5090_pytorch.sh
```

预计时间：
- 方案A（wheels）：10-30分钟
- 方案B（源码）：2-4小时

