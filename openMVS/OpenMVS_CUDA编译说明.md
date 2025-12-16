# OpenMVS CUDA 编译说明文档

## 1. 编译环境信息

### 操作系统
- **系统**: Linux 5.15.0-25-generic
- **发行版**: Ubuntu 20.04 LTS
- **架构**: x86_64

### CUDA 环境
- **CUDA 版本**: 12.8 (Release 12.8, V12.8.93)
- **CUDA 架构**: 120 (对应 NVIDIA Blackwell 架构)
- **支持 GPU**: NVIDIA GeForce RTX 5090
- **编译参数**: `-DCMAKE_CUDA_ARCHITECTURES="120"`

> **重要提示**: CUDA 架构 120 专为 RTX 5090 等最新 Blackwell 架构 GPU 优化。如果使用其他 GPU，需要调整此参数：
> - RTX 4090/4080: 89 (Ada Lovelace)
> - RTX 3090/3080: 86 (Ampere)
> - RTX 2080 Ti: 75 (Turing)

### Eigen 库
- **版本**: 3.4.0
- **安装方式**: 本地编译
- **安装路径**: `/root/work/openMVS/eigen-3.4.0`
- **CMake 配置**:
  ```cmake
  -DEIGEN3_INCLUDE_DIR=/root/work/openMVS/eigen-3.4.0
  -DEigen3_DIR=/root/work/openMVS/eigen-3.4.0/build
  ```

### 编译器
- **编译器**: GCC 11.4.0
- **C++ 标准**: C++23
- **编译器标志**: 
  - `-O3` (Release 优化)
  - `-fopenmp` (OpenMP 支持)
  - `-msse4.2` (SSE 指令集优化)

### 关键依赖库版本
| 库名称 | 版本 | 用途 |
|--------|------|------|
| CGAL | 5.x | 计算几何算法库 |
| OpenCV | 4.2.0 | 图像处理 |
| Boost | 1.71.0 | C++ 扩展库 |
| VCG | latest | 网格处理库 |
| Ceres | 可选 | 优化库 |

## 2. 硬件环境要求

### GPU 要求
- **推荐 GPU**: NVIDIA GeForce RTX 5090 (8张)
- **GPU 驱动版本**: 570.124.06 或更高
- **显存要求**: 
  - 最小: 8GB VRAM
  - 推荐: 24GB+ VRAM (处理大规模场景)
  - 本次编译环境: 8x RTX 5090 (32GB VRAM each)

### CPU 和内存
- **CPU**: Intel Xeon Gold 6530 (128 cores)
- **内存**: 推荐 64GB+ RAM，本次环境 503.54GB
- **磁盘**: 推荐 500GB+ 可用空间

### 支持的 GPU 架构
OpenMVS 支持以下 NVIDIA GPU 架构（需相应调整 CMAKE_CUDA_ARCHITECTURES）:
- **Blackwell** (sm_120): RTX 5090, RTX 5080
- **Ada Lovelace** (sm_89): RTX 4090, RTX 4080
- **Ampere** (sm_86): RTX 3090, A100
- **Turing** (sm_75): RTX 2080 Ti, Titan RTX
- **Volta** (sm_70): V100, Titan V

## 3. 编译过程

### 3.1 环境准备

```bash
# 克隆 OpenMVS 仓库
git clone --recurse-submodules https://github.com/cdcseacave/openMVS.git
cd openMVS

# 准备 Eigen 3.4.0
cd eigen-3.4.0
mkdir build && cd build
cmake ..
cd ../..
```

### 3.2 CMake 配置

创建编译目录并配置：

```bash
# 创建 CUDA 编译目录
mkdir build_cuda && cd build_cuda

# CMake 配置
cmake .. \
  -DCMAKE_BUILD_TYPE=Release \
  -DOpenMVS_USE_CUDA=ON \
  -DOpenMVS_USE_OPENMP=ON \
  -DOpenMVS_MAX_CUDA_COMPATIBILITY=OFF \
  -DCMAKE_CUDA_ARCHITECTURES="120" \
  -DEIGEN3_INCLUDE_DIR=/root/work/openMVS/eigen-3.4.0 \
  -DEigen3_DIR=/root/work/openMVS/eigen-3.4.0/build \
  -DVCG_ROOT=/root/work/openMVS/vcg \
  -DCMAKE_INSTALL_PREFIX=/usr/local
```

**关键参数说明**:
- `OpenMVS_USE_CUDA=ON`: 启用 CUDA 支持
- `OpenMVS_USE_OPENMP=ON`: 启用 OpenMP 多线程
- `CMAKE_CUDA_ARCHITECTURES="120"`: 指定 GPU 计算能力架构
- `OpenMVS_MAX_CUDA_COMPATIBILITY=OFF`: 关闭最大兼容性模式，提升性能

### 3.3 编译

```bash
# 使用所有 CPU 核心编译
make -j$(nproc)

# 安装
sudo make install
```

## 4. 编译问题及解决方案

### 问题 1: CGAL 命名空间错误

**错误信息**:
```
error: 'CGAL::Point_set_processing_3::parameters' has not been declared
```

**原因**: CGAL 5.x 版本移除了 `Point_set_processing_3::parameters` 命名空间，改为直接使用 `CGAL::parameters`。

**解决方案**:
修改文件 `/root/work/openMVS/libs/MVS/DepthMap.cpp` 第 1535 行：

```cpp
// 修改前
CGAL::Point_set_processing_3::parameters::point_map(CGAL::First_of_pair_property_map<PointVectorPair>())

// 修改后
CGAL::parameters::point_map(CGAL::First_of_pair_property_map<PointVectorPair>())
```

完整修改：
```cpp
CGAL::pca_estimate_normals<CGAL::Sequential_tag>(
    pointvectors, numNeighbors,
    CGAL::parameters::point_map(CGAL::First_of_pair_property_map<PointVectorPair>())
    .normal_map(CGAL::Second_of_pair_property_map<PointVectorPair>())
);
```

### 问题 2: VCG 库警告

**警告信息**:
```
warning: unused variable 'xxx' [-Wunused-variable]
```

**说明**: 这些是来自 VCG 库的警告，不影响编译和使用，可以忽略。

### 问题 3: CUDA 架构不匹配

**症状**: 编译成功但运行时 GPU 不被识别或性能低下。

**解决方案**: 确认你的 GPU 架构并设置正确的 `CMAKE_CUDA_ARCHITECTURES` 值：

```bash
# 查询 GPU 计算能力
nvidia-smi --query-gpu=compute_cap --format=csv

# 常见架构对应关系
# 8.9 -> 89 (RTX 4090)
# 8.6 -> 86 (RTX 3090)
# 7.5 -> 75 (RTX 2080 Ti)
# 12.0 -> 120 (RTX 5090)
```

## 5. 编译结果验证

### 5.1 检查可执行文件

编译成功后，以下可执行文件将安装到 `/usr/local/bin/OpenMVS/`:

```bash
ls -lh /usr/local/bin/OpenMVS/
```

**核心工具**:
- `DensifyPointCloud` (6.4MB) - 点云密集化
- `ReconstructMesh` (4.9MB) - 网格重建
- `RefineMesh` (4.6MB) - 网格细化
- `TextureMesh` (4.7MB) - 网格纹理化
- `TransformScene` (4.4MB) - 场景变换

**接口工具**:
- `InterfaceCOLMAP` (2.8MB) - COLMAP 格式转换
- `InterfaceMetashape` (4.5MB) - Metashape 格式转换
- `InterfaceMVSNet` (4.5MB) - MVSNet 格式转换
- `InterfacePolycam` (4.4MB) - Polycam 格式转换

**测试工具**:
- `Tests` (7.0MB) - 单元测试程序

### 5.2 CUDA 支持验证

#### 方法 1: 检查 CUDA 库链接

```bash
ldd /usr/local/bin/OpenMVS/DensifyPointCloud | grep -i cuda
```

**预期输出**:
```
libcuda.so.1 => /usr/lib/x86_64-linux-gnu/libcuda.so.1
libcudart.so.12 => /usr/local/cuda/lib64/libcudart.so.12
```

#### 方法 2: 检查 CUDA 符号

```bash
strings /usr/local/bin/OpenMVS/DensifyPointCloud | grep -i cuda | head -10
```

**预期输出**:
```
libcuda.so.1
libcudart.so.12
cudaFree
cudaDestroyTextureObject
cudaGetLastError
cudaMalloc
cudaMemcpy
```

#### 方法 3: 运行测试

```bash
# 查看版本信息和系统识别
/usr/local/bin/OpenMVS/DensifyPointCloud --help
```

**预期输出示例**:
```
OpenMVS x64 v2.3.0
Build date: Dec 16 2025, 14:57:34
CPU: INTEL(R) XEON(R) GOLD 6530 (128 cores)
RAM: 503.54GB Physical Memory
OS: Linux 5.15.0-25-generic (x86_64)
SSE & AVX compatible CPU & OS detected
```

### 5.3 Python 绑定验证

```bash
# 检查 Python 绑定
ls -lh /usr/local/lib/pyOpenMVS.so

# 测试导入
python3 -c "import sys; sys.path.insert(0, '/usr/local/lib'); import pyOpenMVS; print('PyOpenMVS loaded successfully')"
```

### 5.4 功能快速测试

创建测试配置文件验证各模块是否正常工作：

```bash
# 测试 DensifyPointCloud
/usr/local/bin/OpenMVS/DensifyPointCloud --help

# 测试 ReconstructMesh
/usr/local/bin/OpenMVS/ReconstructMesh --help

# 测试 TextureMesh
/usr/local/bin/OpenMVS/TextureMesh --help
```

所有命令应正常显示帮助信息而不报错。

## 6. 安装和路径配置

### 6.1 安装路径

- **可执行文件**: `/usr/local/bin/OpenMVS/`
- **库文件**: `/usr/local/lib/OpenMVS/`
- **头文件**: `/usr/local/include/OpenMVS/`
- **CMake 配置**: `/usr/local/lib/cmake/OpenMVS/`
- **Python 绑定**: `/usr/local/lib/pyOpenMVS.so`

### 6.2 创建符号链接（可选）

为方便使用，可以创建符号链接到 `/usr/local/bin`:

```bash
sudo ln -sf /usr/local/bin/OpenMVS/* /usr/local/bin/
```

之后可以直接运行：
```bash
DensifyPointCloud --help
```

### 6.3 环境变量设置

添加到 `~/.bashrc`:

```bash
# OpenMVS 路径
export OPENMVS_HOME=/usr/local/bin/OpenMVS
export PATH=$OPENMVS_HOME:$PATH
export LD_LIBRARY_PATH=/usr/local/lib/OpenMVS:$LD_LIBRARY_PATH
```

## 7. 性能优化建议

### 7.1 CUDA 性能

- 确保使用正确的 GPU 架构编译（`CMAKE_CUDA_ARCHITECTURES`）
- 关闭 `OpenMVS_MAX_CUDA_COMPATIBILITY` 以获得最佳性能
- 使用多 GPU 时，确保 PCIe 带宽充足

### 7.2 CPU 性能

- 启用 OpenMP: `-DOpenMVS_USE_OPENMP=ON`
- 使用 Release 模式: `-DCMAKE_BUILD_TYPE=Release`
- 启用 IPO（链接时优化）: `-DCMAKE_INTERPROCEDURAL_OPTIMIZATION=ON`

### 7.3 内存优化

对于大规模场景处理：
- 确保足够的系统内存（推荐 64GB+）
- 使用 SSD 作为临时文件存储
- 考虑分块处理超大场景

## 8. 常见问题 FAQ

**Q: 为什么需要指定 Eigen 路径？**  
A: OpenMVS 需要 Eigen 3.4.0 或更高版本，系统默认版本可能较旧（如 3.3.7）。

**Q: 编译时间多久？**  
A: 使用 128 核 CPU 全速编译约 2-3 分钟。单核约 30-60 分钟。

**Q: 可以不使用 CUDA 吗？**  
A: 可以，设置 `-DOpenMVS_USE_CUDA=OFF`，但性能会显著降低。

**Q: 如何更新 OpenMVS？**  
A: 重新 pull 代码，删除 build 目录，重新编译安装。

## 9. 参考资源

- **官方 GitHub**: https://github.com/cdcseacave/openMVS
- **官方文档**: https://github.com/cdcseacave/openMVS/wiki
- **编译指南**: https://github.com/cdcseacave/openMVS/wiki/Building
- **CUDA 架构对照**: https://arnon.dk/matching-sm-architectures-arch-and-gencode-for-various-nvidia-cards/

---

**文档版本**: 1.0  
**最后更新**: 2025-12-16  
**适用 OpenMVS 版本**: v2.3.0  
**编译环境**: Ubuntu 20.04 + CUDA 12.8 + RTX 5090
