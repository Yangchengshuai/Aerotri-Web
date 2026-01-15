# OpenMVS CUDA 加速版本编译手册

本文档记录了在 Linux (Ubuntu 20.04) 系统上编译 OpenMVS CUDA 加速版本的完整过程，包括依赖库版本、编译步骤、遇到的问题及解决方案。

## 目录

- [系统环境](#系统环境)
- [依赖库版本](#依赖库版本)
- [编译准备](#编译准备)
- [编译步骤](#编译步骤)
- [问题与解决方案](#问题与解决方案)
- [配置与使用](#配置与使用)
- [验证结果](#验证结果)

---

## 系统环境

### 硬件配置
- **CPU**: Intel(R) Xeon(R) Gold 5318Y @ 2.10GHz (96 cores)
- **GPU**: 8x NVIDIA GeForce RTX 4090 (24GB each)
- **内存**: 251.52 GB RAM
- **存储**: 1010.54GB (20.87TB)

### 软件环境
- **操作系统**: Linux 5.15.0-139-generic (x86_64)
- **编译器**: GCC 9.4.0
- **CMake**: 4.2.0
- **CUDA**: 12.3.107
- **Python**: 3.8.10

---

## 依赖库版本

### 核心依赖

| 库名称 | 版本 | 安装方式 | 用途 |
|--------|------|----------|------|
| **Eigen** | 3.4.0 | 源码编译 | 线性代数库 |
| **OpenCV** | 4.2.0 | 系统包管理器 | 图像处理 |
| **Boost** | 1.71.0 | 系统包管理器 | C++ 基础库 |
| **CGAL** | 5.0.2 | 系统包管理器 | 计算几何 |
| **VCG** | 最新 | Git 子模块 | 网格处理 |
| **CUDA** | 12.3 | NVIDIA 官方 | GPU 加速 |
| **Ceres Solver** | 2.3.0 | 源码编译（CUDA 版）| 非线性优化 |

### 可选依赖

| 库名称 | 版本 | 说明 |
|--------|------|------|
| libjxl | - | JPEG-XL 支持（本次编译未启用）|
| BreakPad | - | 崩溃报告（可选）|
| GLAD | - | OpenGL 加载（可选）|
| GLFW | - | 窗口管理（可选）|

---

## 编译准备

### 1. 安装系统依赖

```bash
# Ubuntu/Debian 系统
sudo apt-get update
sudo apt-get install -y \
    build-essential \
    cmake \
    git \
    libboost-dev \
    libboost-filesystem-dev \
    libboost-program-options-dev \
    libboost-system-dev \
    libboost-thread-dev \
    libcgal-dev \
    libopencv-dev \
    libeigen3-dev \
    ninja-build
```

### 2. 准备 VCG 库

```bash
cd /root/work/Aerotri-Web
git clone https://github.com/cdcseacave/vcg.git
```

### 3. 准备 Eigen 库（可选，使用系统自带）

```bash
# 如果需要特定版本
cd /root/work/Aerotri-Web
wget https://gitlab.com/libeigen/eigen/-/archive/3.4.0/eigen-3.4.0.tar.gz
tar -xzf eigen-3.4.0.tar.gz
```

### 4. 编译 Ceres Solver（CUDA 版本）

```bash
# 下载 Ceres Solver
cd /root/opt
git clone https://github.com/ceres-solver/ceres.git
cd ceres
git checkout 2.3.0

# 创建构建目录
mkdir build && cd build

# 配置 CMake（启用 CUDA）
cmake .. \
  -DCMAKE_BUILD_TYPE=Release \
  -DEIGEN_INCLUDE_DIR=/usr/local/include/eigen3 \
  -DCUDA=YES \
  -DCMAKE_INSTALL_PREFIX=/root/opt/ceres-2.3-cuda \
  -DBUILD_EXAMPLES=OFF \
  -DBUILD_TESTING=OFF

# 编译和安装
make -j$(nproc)
sudo make install
```

---

## 编译步骤

### 1. 克隆 OpenMVS 源码

```bash
cd /root/work/Aerotri-Web
git clone https://github.com/cdcseacave/openMVS.git
cd openMVS
```

### 2. 恢复 build 目录

**⚠️ 注意**: `build/` 目录包含 CMake 构建所需的源文件，不是编译输出目录。

```bash
# 如果 build/ 目录为空或损坏，从发布版本恢复
wget -q -O /tmp/build.tar.gz "https://github.com/cdcseacave/openMVS/archive/refs/tags/v2.3.0.tar.gz"
tar -xzf /tmp/build.tar.gz --strip-components=1 "openMVS-2.3.0/build/"
rm /tmp/build.tar.gz
```

### 3. 修复源码兼容性问题

#### 3.1 修复 CMakeLists.txt

```bash
# 启用 C 语言支持（默认只启用了 CXX）
sed -i 's/PROJECT(OpenMVS LANGUAGES CXX)/PROJECT(OpenMVS LANGUAGES C CXX)/' CMakeLists.txt
```

#### 3.2 修复 libs/IO/CMakeLists.txt

```bash
# 将 libjxl 改为可选依赖
sed -i 's/FIND_PACKAGE(PkgConfig REQUIRED)/FIND_PACKAGE(PkgConfig)/' libs/IO/CMakeLists.txt
sed -i 's/pkg_check_modules(${PREFIX} REQUIRED IMPORTED_TARGET/pkg_check_modules(${PREFIX} IMPORTED_TARGET/' libs/IO/CMakeLists.txt
```

在 `libs/IO/CMakeLists.txt` 中添加条件检查：

```cmake
FIND_PACKAGE(PkgConfig)
if(PkgConfig_FOUND)
    pkg_check_modules_fullpath_libs(JPEGXL libjxl)
else()
    SET(JPEGXL_LIBRARIES "")
    SET(JPEGXL_FOUND FALSE)
endif()
```

#### 3.3 修复 libs/Common/Config.h

查找并修复 `__has_builtin` 宏的使用（约第 235 行）：

```cpp
#if defined(__has_builtin)
#   if __has_builtin(__builtin_debugtrap)
#       define DEBUG_BREAK __builtin_debugtrap
#   else
#       // ... fallback code ...
#   endif
#endif
```

#### 3.4 移除 JPEG-XL 支持

在 `libs/Common/Types.inl` 中（约第 3080 行），删除 `.jxl` 格式支持：

```cpp
// 删除这段代码
// if (ext == ".jxl") {
//     compression_params.push_back(cv::IMWRITE_JPEGXL_QUALITY);
//     compression_params.push_back(95);
// } else
```

#### 3.5 适配 CGAL 5.0.2 API

在 `libs/MVS/SceneReconstruct.cpp` 中（约第 41-42 行）：

```cpp
// 修改前
#include <CGAL/AABB_traits_3.h>
#include <CGAL/AABB_triangle_primitive_3.h>

// 修改后
#include <CGAL/AABB_traits.h>
#include <CGAL/AABB_triangle_primitive.h>
```

#### 3.6 适配 Ceres 2.3 API

在 `libs/MVS/SceneRefine.cpp` 中（约第 1326-1327 行）：

```cpp
// 修改前
ceres::MeshProblem* problemData(new ceres::MeshProblem(refine));
ceres::GradientProblem problem(problemData);

// 修改后
auto problemData = std::make_unique<ceres::MeshProblem>(refine);
ceres::MeshProblem* problemDataPtr = problemData.get();
ceres::GradientProblem problem(std::move(problemData));

// 后续代码中使用 problemDataPtr 替代 problemData
```

### 4. 配置 CMake

```bash
# 创建独立的构建目录
mkdir -p /root/work/Aerotri-Web/openMVS/make
cd /root/work/Aerotri-Web/openMVS/make

# 运行 CMake 配置
cmake -DCMAKE_BUILD_TYPE=Release \
  -DOpenMVS_USE_CUDA=ON \
  -DOpenMVS_USE_CERES=ON \
  -DCMAKE_PREFIX_PATH=/root/opt/ceres-2.3-cuda \
  -DCMAKE_INSTALL_PREFIX=/root/work/Aerotri-Web/openMVS/install \
  -DEigen3_DIR=/root/work/Aerotri-Web/eigen-3.4.0 \
  -DVCG_ROOT=/root/work/Aerotri-Web/vcg \
  ..
```

**配置说明**:
- `OpenMVS_USE_CUDA=ON`: 启用 CUDA 加速
- `OpenMVS_USE_CERES=ON`: 启用 Ceres 优化
- `CMAKE_PREFIX_PATH`: 指定 CUDA 版本的 Ceres 路径
- `Eigen3_DIR`: Eigen 3.4.0 路径（如果使用系统自带可省略）
- `VCG_ROOT`: VCG 库路径

### 5. 编译

```bash
# 使用 8 线程编译
make -j8
```

**编译输出**:
```
[100%] Built target TransformScene
[100%] Built target Tests
```

### 6. 验证编译结果

```bash
# 查看生成的可执行文件
ls -lh /root/work/Aerotri-Web/openMVS/make/bin/

# 查看生成的库文件
ls -lh /root/work/Aerotri-Web/openMVS/make/lib/

# 测试运行
/root/work/Aerotri-Web/openMVS/make/bin/DensifyPointCloud --help
```

---

## 问题与解决方案

### 问题 1: build/ 目录缺失 Utils.cmake

**错误信息**:
```
CMake Error at CMakeLists.txt:104 (INCLUDE):
  INCLUDE could not find requested file: build/Utils.cmake
```

**原因**: `build/` 目录是源代码的一部分，包含 CMake 构建脚本，被 `.gitignore` 忽略或被误删。

**解决方案**:
```bash
# 方法 1: 从发布版本恢复
wget -q -O /tmp/build.tar.gz "https://github.com/cdcseacave/openMVS/archive/refs/tags/v2.3.0.tar.gz"
tar -xzf /tmp/build.tar.gz --strip-components=1 "openMVS-2.3.0/build/"
rm /tmp/build.tar.gz

# 方法 2: 手动创建目录和文件（不推荐）
mkdir -p build/Modules build/Templates
# 然后手动复制缺失的文件
```

### 问题 2: C 语言未启用

**错误信息**:
```
CMake Error: Unknown extension ".c" for file
try_compile() works only for enabled languages. Currently these are: CXX
```

**原因**: CMakeLists.txt 只启用了 CXX，但构建脚本需要编译 C 代码。

**解决方案**:
```bash
# 修改 CMakeLists.txt 第 73 行
# 修改前: PROJECT(OpenMVS LANGUAGES CXX)
# 修改后: PROJECT(OpenMVS LANGUAGES C CXX)
sed -i 's/PROJECT(OpenMVS LANGUAGES CXX)/PROJECT(OpenMVS LANGUAGES C CXX)/' CMakeLists.txt
```

### 问题 3: libjxl 依赖缺失

**错误信息**:
```
CMake Error: The following required packages were not found: - libjxl
```

**原因**: PkgConfig 将 libjxl 设为必需依赖，但系统未安装。

**解决方案**: 修改 `libs/IO/CMakeLists.txt`，将 libjxl 改为可选依赖（参见编译步骤 3.2）。

### 问题 4: __has_builtin 宏兼容性

**错误信息**:
```
error: missing binary operator before token "("
#if defined(__has_builtin) && __has_builtin(__builtin_debugtrap)
```

**原因**: GCC 9.4.0 不支持 `__has_builtin` 宏的单行条件判断。

**解决方案**: 分层嵌套预处理指令（参见编译步骤 3.3）。

### 问题 5: IMWRITE_JPEGXL_QUALITY 不存在

**错误信息**:
```
error: 'IMWRITE_JPEGXL_QUALITY' is not a member of 'cv'
```

**原因**: OpenCV 4.2.0 不支持 JPEG-XL 格式。

**解决方案**: 移除 JPEG-XL 代码支持（参见编译步骤 3.4）。

### 问题 6: CGAL AABB_traits_3.h 头文件缺失

**错误信息**:
```
fatal error: CGAL/AABB_traits_3.h: No such file or directory
```

**原因**: CGAL 5.0.2 API 变更，头文件命名从 `AABB_traits_3.h` 改为 `AABB_traits.h`。

**解决方案**: 更新头文件引用（参见编译步骤 3.5）。

### 问题 7: Ceres GradientProblem API 变更

**错误信息**:
```
error: no matching function for call to 'ceres::GradientProblem::GradientProblem(ceres::MeshProblem*&)'
```

**原因**: Ceres 2.3 使用 `std::unique_ptr` 替代裸指针。

**解决方案**: 使用智能指针（参见编译步骤 3.6）。

### 问题 8: Eigen 版本不匹配

**错误信息**:
```
CMake Error: Found Eigen dependency, but the version of Eigen found (3.4.0)
does not exactly match the version of Eigen Ceres was compiled with (3.3.7)
```

**原因**: 系统默认 Eigen 版本与编译 Ceres 时使用的版本不同。

**解决方案**:
1. 确保 `CMAKE_PREFIX_PATH` 指向正确的 Ceres 安装路径
2. 或使用与 Ceres 兼容的 Eigen 版本重新编译 Ceres

---

## 配置与使用

### 环境变量配置

#### 方式 1: 通过环境变量（推荐）

```bash
# 设置 OpenMVS 路径
export OPENMVS_BIN_DIR=/root/work/Aerotri-Web/openMVS/make/bin

# 设置 Ceres 库路径（运行时）
export LD_LIBRARY_PATH=/root/opt/ceres-2.3-cuda/lib:$LD_LIBRARY_PATH

# 验证
echo $OPENMVS_BIN_DIR
echo $LD_LIBRARY_PATH
```

#### 方式 2: 永久配置

添加到 `~/.bashrc` 或 `/etc/profile`:

```bash
cat >> ~/.bashrc << 'EOF'
# OpenMVS CUDA 加速版本
export OPENMVS_BIN_DIR=/root/work/Aerotri-Web/openMVS/make/bin
export LD_LIBRARY_PATH=/root/opt/ceres-2.3-cuda/lib:$LD_LIBRARY_PATH
EOF

source ~/.bashrc
```

### 后端集成配置

更新 `/root/work/Aerotri-Web/aerotri-web/backend/app/settings.py`:

```python
# ===== OpenMVS configuration =====
OPENMVS_BIN_DIR = Path(
    os.getenv("OPENMVS_BIN_DIR", "/root/work/Aerotri-Web/openMVS/make/bin")
)
```

更新 `/root/work/Aerotri-Web/aerotri-web/backend/app/services/task_runner.py`:

```python
# Library paths for runtime dependencies
CERES_LIB_PATH = "/root/opt/ceres-2.3-cuda/lib"
```

---

## 验证结果

### 1. 检查可执行文件

```bash
$ ls -lh /root/work/Aerotri-Web/openMVS/make/bin/
total 47M
-rwxr-xr-x 1 root root 5.7M Jan 15 11:16 DensifyPointCloud
-rwxr-xr-x 1 root root 2.8M Jan 15 11:16 InterfaceCOLMAP
-rwxr-xr-x 1 root root 4.5M Jan 15 11:16 InterfaceMVSNet
-rwxr-xr-x 1 root root 4.5M Jan 15 11:16 InterfaceMetashape
-rwxr-xr-x 1 root root 4.5M Jan 15 11:16 InterfacePolycam
-rwxr-xr-x 1 root root 4.7M Jan 15 11:16 ReconstructMesh
-rwxr-xr-x 1 root root 4.6M Jan 15 11:16 RefineMesh
-rwxr-xr-x 1 root root 6.2M Jan 15 11:17 Tests
-rwxr-xr-x 1 root root 4.7M Jan 15 11:16 TextureMesh
-rwxr-xr-x 1 root root 4.4M Jan 15 11:17 TransformScene
```

### 2. 检查库文件

```bash
$ ls -lh /root/work/Aerotri-Web/openMVS/make/lib/
total 19M
-rw-r--r-- 1 root root 1.3M Jan 15 11:12 libCommon.a
-rw-r--r-- 1 root root 2.0M Jan 15 11:12 libIO.a
-rw-r--r-- 1 root root  15M Jan 15 11:16 libMVS.a
-rw-r--r-- 1 root root 507K Jan 15 11:12 libMath.a
-rwxr-xr-x 1 root root  16K Jan 15 11:16 pyOpenMVS.so
```

### 3. 验证 CUDA 链接

```bash
$ ldd /root/work/Aerotri-Web/openMVS/make/bin/DensifyPointCloud | grep cuda
	libcuda.so.1 => /lib/x86_64-linux-gnu/libcuda.so.1 (0x00007f250a48c000)
	libcudart.so.12 => /usr/local/cuda-12.3/lib64/libcudart.so.12 (0x00007f250a1dc000)
```

### 4. 验证 Ceres 链接

```bash
$ ldd /root/work/Aerotri-Web/openMVS/make/bin/RefineMesh | grep ceres
	libceres.so.4 => /root/opt/ceres-2.3-cuda/lib/libceres.so.4 (0x00007f3adfb61000)
```

### 5. 功能测试

```bash
$ /root/work/Aerotri-Web/openMVS/make/bin/DensifyPointCloud --help
11:20:18 [App     ] OpenMVS x64 v2.3.0
11:20:18 [App     ] Build date: Jan 15 2026, 11:12:28
11:20:18 [App     ] CPU: Intel(R) Xeon(R) Gold 5318Y CPU @ 2.10GHz (96 cores)
11:20:18 [App     ] RAM: 251.52GB Physical Memory 2.00GB Virtual Memory
11:20:18 [App     ] OS: Linux 5.15.0-139-generic (x86_64)
11:20:18 [App     ] Disk: 1010.54GB (20.87TB) space
11:20:18 [App     ] SSE & AVX compatible CPU & OS detected
11:20:18 [App     ] Command line: DensifyPointCloud --help
11:20:18 [App     ] Available options:

Generic options:
  -h [ --help ]                         produce this help message
  -w [ --working-folder ] arg           working directory (default current directory)
  ...
```

---

## 性能优化建议

### 1. GPU 选择

OpenMVS 会自动检测可用的 GPU 设备。如果有多张 GPU，可以通过设置 `CUDA_VISIBLE_DEVICES` 环境变量来指定使用的 GPU：

```bash
# 使用 GPU 0
export CUDA_VISIBLE_DEVICES=0

# 使用多张 GPU（如果 OpenMVS 支持）
export CUDA_VISIBLE_DEVICES=0,1,2,3
```

### 2. 内存优化

对于大场景重建，建议：
- 增加 GPU 内存预算
- 使用分块处理
- 调整 DensifyPointCloud 的分辨率级别

### 3. 编译选项优化

重新编译时可考虑以下选项：

```bash
cmake -DCMAKE_BUILD_TYPE=Release \
  -DOpenMVS_USE_CUDA=ON \
  -DOpenMVS_USE_CERES=ON \
  -DOpenMVS_USE_OPENMP=ON \
  -DOpenMVS_ENABLE_IPO=ON \  # Interprocedural optimization
  -DCMAKE_CXX_FLAGS="-O3 -march=native" \
  ..
```

---

## 常见使用场景

### 场景 1: 从 COLMAP 稀疏重建生成密集点云

```bash
cd /path/to/project
/root/work/Aerotri-Web/openMVS/make/bin/InterfaceCOLMAP \
  --working-folder . \
  --config-file InterfaceCOLMAP.cfg \
  --archive-type 2
```

### 场景 2: 网格重建与优化

```bash
# 重建网格
/root/work/Aerotri-Web/openMVS/make/bin/ReconstructMesh \
  --working-folder . \
  --config-file ReconstructMesh.cfg

# 优化网格（使用 Ceres + CUDA）
/root/work/Aerotri-Web/openMVS/make/bin/RefineMesh \
  --working-folder . \
  --config-file RefineMesh.cfg \
  --gradient-solver 0  # 0 = Ceres
```

### 场景 3: 纹理映射

```bash
/root/work/Aerotri-Web/openMVS/make/bin/TextureMesh \
  --working-folder . \
  --config-file TextureMesh.cfg \
  --export-type ply
```

---

## 故障排查

### 问题: 运行时找不到 libcuda.so.1

**症状**:
```
error while loading shared libraries: libcuda.so.1: cannot open shared object file
```

**解决方案**:
```bash
# 检查 CUDA 驱动
nvidia-smi

# 检查 CUDA 运行时库
ls -la /usr/local/cuda-12.3/lib64/libcudart.so.12

# 添加到 LD_LIBRARY_PATH
export LD_LIBRARY_PATH=/usr/local/cuda-12.3/lib64:$LD_LIBRARY_PATH
```

### 问题: Ceres 库版本冲突

**症状**:
```
symbol lookup error: /root/opt/ceres-2.3-cuda/lib/libceres.so.4:
undefined symbol: _ZN5ceres18internal_parallel_for...
```

**解决方案**:
```bash
# 确保使用正确的 Ceres 库
ldd /root/work/Aerotri-Web/openMVS/make/bin/RefineMesh | grep ceres

# 清理旧的库缓存
sudo ldconfig

# 或设置 LD_LIBRARY_PATH 优先使用新编译的 Ceres
export LD_LIBRARY_PATH=/root/opt/ceres-2.3-cuda/lib:$LD_LIBRARY_PATH
```

### 问题: GPU 内存不足

**症状**:
```
CUDA out of memory. Tried to allocate XXX MB
```

**解决方案**:
1. 降低 DensifyPointCloud 的 `resolution_level`
2. 使用分块处理
3. 关闭其他占用 GPU 内存的程序

---

## 参考资源

### 官方文档
- [OpenMVS GitHub](https://github.com/cdcseacave/openMVS)
- [OpenMVS Wiki - Building](https://github.com/cdcseacave/openMVS/wiki/Building)
- [Ceres Solver](http://ceres-solver.org/)
- [CGAL Documentation](https://doc.cgal.org/)

### 相关工具
- [COLMAP](https://github.com/colmap/colmap)
- [OpenMVG](https://github.com/openMVG/openMVG)
- [Boost C++ Libraries](https://www.boost.org/)

---

## 版本信息

**文档版本**: 1.0
**编译日期**: 2026-01-15
**OpenMVS 版本**: 2.3.0
**维护者**: AeroTri Team

---

## 更新日志

| 日期 | 版本 | 更新内容 |
|------|------|----------|
| 2026-01-15 | 1.0 | 初始版本，记录 CUDA 加速版本编译过程 |

---

**注意**: 本文档基于实际编译过程整理，不同环境可能遇到不同问题。如遇到文档未涵盖的问题，请参考官方文档或提交 Issue。
