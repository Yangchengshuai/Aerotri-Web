# RTX 5090 PyTorch 兼容性修复指南

## 问题分析

**错误信息**：
```
RuntimeError: CUDA error: no kernel image is available for execution on the device
NVIDIA GeForce RTX 5090 with CUDA capability sm_120 is not compatible with the current PyTorch installation.
The current PyTorch install supports CUDA capabilities sm_50 sm_60 sm_70 sm_75 sm_80 sm_86 sm_90.
```

**根本原因**：
- RTX 5090 使用 Blackwell 架构（sm_120 compute capability）
- 当前 PyTorch 版本（2.4.1+cu124）不支持 sm_120
- CUDA 扩展（diff-gaussian-rasterization, simple-knn）没有为 sm_120 编译

## 解决方案

### 方案1：升级到 PyTorch 2.9.0+cu128（推荐）⭐⭐⭐⭐⭐

**参考**：[vLLM RTX 5090 配置指南](https://discuss.vllm.ai/t/vllm-on-rtx5090-working-gpu-setup-with-torch-2-9-0-cu128/1492)

**优点**：
- ✅ 官方支持 sm_120
- ✅ 长期稳定
- ✅ 性能最优

**缺点**：
- ⚠️ 需要重新编译 CUDA 扩展
- ⚠️ 可能需要更新其他依赖

**实施步骤**：

```bash
# 1. 激活环境
source /root/work/gs_workspace/gs_env/bin/activate

# 2. 卸载旧版本
pip uninstall -y torch torchvision torchaudio diff-gaussian-rasterization simple-knn

# 3. 安装 PyTorch 2.9.0 nightly (cu128)
pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu128

# 4. 设置编译环境变量
export TORCH_CUDA_ARCH_LIST="12.0"
export FLASH_ATTN_CUDA_ARCHS="120"
export CMAKE_CUDA_ARCHITECTURES=120

# 5. 重新编译 CUDA 扩展
cd /root/work/gs_workspace/gaussian-splatting

# diff-gaussian-rasterization
cd submodules/diff-gaussian-rasterization
pip install -e . --no-build-isolation
cd ../..

# simple-knn
cd submodules/simple-knn
pip install -e . --no-build-isolation
cd ../..

# 6. 验证
python -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"
```

**自动化脚本**：
```bash
/root/work/gs_workspace/fix_rtx5090_pytorch.sh
```

---

### 方案2：使用 CPU 模式（临时方案）⭐⭐

**优点**：
- ✅ 无需修改环境
- ✅ 立即可用
- ✅ 避免兼容性问题

**缺点**：
- ❌ 训练速度极慢（10-100x 慢于 GPU）
- ❌ 不适合生产环境

**实施**：
在训练参数中设置 `data_device: "cpu"`（已在代码中支持）

---

### 方案3：使用 PyTorch 2.7+cu126（如果可用）⭐⭐⭐

**优点**：
- ✅ 相对稳定
- ✅ 可能有预编译 wheel

**缺点**：
- ⚠️ 可能仍不支持 sm_120
- ⚠️ 需要验证兼容性

**实施**：
```bash
pip install torch==2.7.0+cu126 torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126
# 然后重新编译扩展
```

---

### 方案4：等待官方稳定版本 ⭐⭐

**优点**：
- ✅ 无需手动编译
- ✅ 官方支持

**缺点**：
- ❌ 时间不确定（可能需要数月）
- ❌ 无法立即使用

---

## 推荐方案对比

| 方案 | 可靠性 | 性能 | 实施难度 | 推荐度 |
|------|--------|------|---------|--------|
| 方案1：PyTorch 2.9.0+cu128 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 中 | ⭐⭐⭐⭐⭐ |
| 方案2：CPU 模式 | ⭐⭐⭐⭐⭐ | ⭐ | 低 | ⭐⭐ |
| 方案3：PyTorch 2.7+cu126 | ⭐⭐⭐ | ⭐⭐⭐⭐ | 中 | ⭐⭐⭐ |
| 方案4：等待官方 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 低 | ⭐⭐ |

## 验证步骤

修复后验证：

```python
import torch
import sys
sys.path.insert(0, '/root/work/gs_workspace/gaussian-splatting')

# 1. 检查 PyTorch 版本
print(f"PyTorch: {torch.__version__}")

# 2. 检查 CUDA 可用性
print(f"CUDA available: {torch.cuda.is_available()}")

# 3. 检查设备信息
if torch.cuda.is_available():
    print(f"Device: {torch.cuda.get_device_name(0)}")
    print(f"Compute capability: {torch.cuda.get_device_capability(0)}")
    
    # 4. 测试基本 CUDA 操作
    x = torch.randn(10, 10).cuda()
    y = torch.randn(10, 10).cuda()
    z = torch.matmul(x, y)
    print("✓ CUDA operations working")

# 5. 测试 3DGS 导入
try:
    import diff_gaussian_rasterization
    print("✓ diff-gaussian-rasterization imported")
except Exception as e:
    print(f"✗ diff-gaussian-rasterization failed: {e}")

try:
    import simple_knn
    print("✓ simple-knn imported")
except Exception as e:
    print(f"⚠ simple-knn failed (optional): {e}")
```

## 常见问题

### Q1: 编译失败怎么办？

**A**: 检查：
1. CUDA 版本是否 >= 12.8
2. 环境变量是否正确设置
3. 是否有足够的磁盘空间和内存
4. 查看详细错误日志

### Q2: 训练时仍然报错？

**A**: 
1. 确认 `TORCH_CUDA_ARCH_LIST="12.0"` 在运行时也设置
2. 检查 `CUDA_VISIBLE_DEVICES` 是否正确
3. 尝试设置 `CUDA_LAUNCH_BLOCKING=1` 获取详细错误

### Q3: 性能如何？

**A**: 根据 vLLM 测试，PyTorch 2.9.0+cu128 在 RTX 5090 上：
- 启动时间：~72秒
- 推理速度：50-300+ tokens/s（取决于模型）
- 内存使用：正常

## 参考链接

- [vLLM RTX 5090 配置指南](https://discuss.vllm.ai/t/vllm-on-rtx5090-working-gpu-setup-with-torch-2-9-0-cu128/1492)
- [PyTorch 官方安装指南](https://pytorch.org/get-started/locally/)
- [CUDA Compute Capability](https://developer.nvidia.com/cuda-gpus)

