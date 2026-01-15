# OpenMVG 编译手册

本文档记录在 Ubuntu 20.04 Linux 系统上编译 OpenMVG 的完整步骤、遇到的问题及解决方案。

## 系统环境

- **操作系统**: Ubuntu 20.04 (Linux 5.15.0-139-generic)
- **编译器**: GCC 9.4.0
- **CMake**: 4.2+ (需要 >= 3.9)
- **Python**: 3.8.10

## 依赖库版本

### 核心依赖

| 库名称 | 版本 | 安装方式 | 用途 |
|--------|------|----------|------|
| **Eigen** | 3.4.0 | 源码编译 | 线性代数库 |
| **Ceres Solver** | 1.13.0 (内部) | OpenMVG 子模块 | 非线性优化 |
| **Ceres Solver** | 2.3.0 (CUDA) | 外部预编译 | 系统依赖 |
| **OpenMP** | 4.5 | 系统自带 | 并行计算 |
| **libtiff** | 4.1.0 | 系统自带 | TIFF 图像格式 |
| **libpng** | 1.6.37 | 系统自带 | PNG 图像格式 |
| **libjpeg** | - | 系统自带 | JPEG 图像格式 |
| **glog** | - | 系统自带 | 日志库 |
| **gflags** | 2.2.2 | 系统自带 | 命令行参数 |
| **CoinUtils** | 2.10.13 (内部) | OpenMVG 子模块 | 线性规划 |
| **Clp** | 1.16.10 (内部) | OpenMVG 子模块 | 线性规划求解器 |
| **Osi** | - (内部) | OpenMVG 子模块 | 线性规划接口 |
| **LEMON** | 1.3 (内部) | OpenMVG 子模块 | 图算法库 |

### 可选依赖

| 库名称 | 版本 | 用途 |
|--------|------|------|
| Qt5 | 5.12.8 | GUI 软件编译 |
| Sphinx | - | 文档生成 |
| Doxygen | - | API 文档生成 |

## 编译步骤

### 1. 安装系统依赖

```bash
sudo apt-get update
sudo apt-get install -y \
    libpng-dev \
    libjpeg-dev \
    libtiff-dev \
    libxxf86vm1 \
    libxxf86vm-dev \
    libxi-dev \
    libxrandr-dev \
    graphviz \
    cmake \
    build-essential \
    libgomp1
```

### 2. 准备源代码

```bash
cd /root/work/Aerotri-Web

# 如果使用 git clone（推荐带 --recursive）
git clone --recursive https://github.com/openMVG/openMVG.git
cd openMVG
git submodule init
git submodule update
```

### 3. 编译 Eigen 3.4.0

**重要**: Eigen 3.4.0 需要先于 OpenMVG 编译并安装。

```bash
cd /root/work/Aerotri-Web/eigen-3.4.0
mkdir -p build && cd build

# 配置
cmake .. \
    -DCMAKE_INSTALL_PREFIX=/usr/local

# 编译并安装
make -j$(nproc)
sudo make install
```

**验证安装**:
```bash
pkg-config --modversion eigen3
# 应该输出: 3.4.0

ls /usr/local/include/eigen3/Eigen/
# 应该能看到 Eigen 头文件
```

### 4. 修复 OpenMVG 子模块的 CMake 版本问题

由于现代 CMake (4.2+) 不再支持 CMake < 3.5，需要手动修改部分子模块的 CMakeLists.txt：

#### 4.1 修复 osi_clp

```bash
vi /root/work/Aerotri-Web/openMVG/src/dependencies/osi_clp/CMakeLists.txt
```

修改第 6 行：
```cmake
# 修改前
CMAKE_MINIMUM_REQUIRED(VERSION 2.6)

# 修改后
CMAKE_MINIMUM_REQUIRED(VERSION 3.9)
```

#### 4.2 修复 lemon

```bash
vi /root/work/Aerotri-Web/openMVG/src/third_party/lemon/CMakeLists.txt
```

修改第 1 行：
```cmake
# 修改前
CMAKE_MINIMUM_REQUIRED(VERSION 2.6)

# 修改后
CMAKE_MINIMUM_REQUIRED(VERSION 3.9)
```

#### 4.3 修复内部 ceres-solver

```bash
vi /root/work/Aerotri-Web/openMVG/src/third_party/ceres-solver/CMakeLists.txt
```

修改第 32-33 行：
```cmake
# 修改前
cmake_minimum_required(VERSION 2.8.0)
cmake_policy(VERSION 2.8)

# 修改后
cmake_minimum_required(VERSION 3.9)
cmake_policy(VERSION 3.9)
```

### 5. 配置 OpenMVG

```bash
cd /root/work/Aerotri-Web
mkdir -p openMVG_Build && cd openMVG_Build

# 配置构建
cmake -DCMAKE_BUILD_TYPE=RELEASE \
      -DOpenMVG_USE_RERUN=OFF \
      -DOpenMVG_USE_INTERNAL_CERES=ON \
      -DCMAKE_INSTALL_PREFIX=/root/work/Aerotri-Web/openMVG_Build/openMVG_install \
      ../openMVG/src/
```

**配置说明**:
- `CMAKE_BUILD_TYPE=RELEASE`: 发布版本，启用优化
- `OpenMVG_USE_RERUN=OFF`: 禁用 Rerun 日志功能（避免网络下载失败）
- `OpenMVG_USE_INTERNAL_CERES=ON`: 使用 OpenMVG 内置的 Ceres 1.13.0
- `CMAKE_INSTALL_PREFIX`: 指定安装路径

**配置输出摘要**:
```
** OpenMVG version: 2.1.0
** Build Shared libs: OFF
** Build OpenMVG tests: OFF
** Build OpenMVG softwares: ON
** Build OpenMVG GUI softwares: ON
** Enable OpenMP parallelization: ON

-- EIGEN: 3.4.0 (external)
-- CERES: 1.13.0 (internal)
-- CLP: 1.16.10 (internal)
-- COINUTILS: 2.10.13 (internal)
-- OSI: (internal)
-- LEMON: 1.3 (internal)
```

### 6. 编译并安装

```bash
# 编译（使用所有 CPU 核心）
cmake --build . --target install -j$(nproc)

# 或者使用传统 make
# make -j$(nproc)
# sudo make install
```

**编译时间**: 约 5-15 分钟（取决于 CPU 性能）

### 7. 验证安装

```bash
# 检查二进制文件
ls /root/work/Aerotri-Web/openMVG_Build/openMVG_install/bin/

# 应该看到约 40 个可执行文件，例如:
# openMVG_main_SfMInit_ImageListing
# openMVG_main_ComputeFeatures
# openMVG_main_ComputeMatches
# openMVG_main_SfM
# openMVG_main_openMVG2Colmap

# 测试运行
/root/work/Aerotri-Web/openMVG_Build/openMVG_install/bin/openMVG_main_SfMInit_ImageListing --help
```

## 遇到的问题及解决方案

### 问题 1: osi_clp CMake 版本过低

**错误信息**:
```
CMake Error at dependencies/osi_clp/CMakeLists.txt:6 (CMAKE_MINIMUM_REQUIRED):
  Compatibility with CMake < 3.5 has been removed from CMake.
```

**原因**: osi_clp 子模块要求的 CMake 版本为 2.6，但现代 CMake 已不再支持。

**解决方案**: 将 `dependencies/osi_clp/CMakeLists.txt` 第 6 行修改为 `CMAKE_MINIMUM_REQUIRED(VERSION 3.9)`

### 问题 2: lemon CMake 版本过低

**错误信息**:
```
CMake Error at third_party/lemon/CMakeLists.txt:1 (CMAKE_MINIMUM_REQUIRED):
  Compatibility with CMake < 3.5 has been removed from CMake.
```

**原因**: lemon 子模块要求的 CMake 版本为 2.6。

**解决方案**: 将 `third_party/lemon/CMakeLists.txt` 第 1 行修改为 `CMAKE_MINIMUM_REQUIRED(VERSION 3.9)`

### 问题 3: 内部 ceres-solver CMake 版本过低

**错误信息**:
```
CMake Error at third_party/ceres-solver/CMakeLists.txt:32 (cmake_minimum_required):
  Compatibility with CMake < 3.5 has been removed from CMake.
```

**原因**: OpenMVG 内置的 ceres-solver 子模块要求 CMake 2.8.0。

**解决方案**:
1. 将 `cmake_minimum_required(VERSION 2.8.0)` 改为 `cmake_minimum_required(VERSION 3.9)`
2. 将 `cmake_policy(VERSION 2.8)` 改为 `cmake_policy(VERSION 3.9)`

### 问题 4: Eigen 版本不匹配

**错误信息**:
```
Failed to find Ceres - Found Eigen dependency, but the version of Eigen found (3.4.0)
does not exactly match the version of Eigen Ceres was compiled with (3.3.7).
```

**原因**: 系统中预装的 Ceres Solver 1.14.0 是用 Eigen 3.3.7 编译的，而当前使用 Eigen 3.4.0，违反 One Definition Rule。

**解决方案**: 使用 `-DOpenMVG_USE_INTERNAL_CERES=ON` 强制使用 OpenMVG 内置的 Ceres Solver (1.13.0)，该版本会自动使用当前检测到的 Eigen 版本编译。

### 问题 5: Rerun SDK 下载失败

**错误信息**:
```
error: downloading 'https://github.com/rerun-io/rerun/releases/download/prerelease/rerun_cpp_sdk.zip' failed
       status_code: 56
       status_string: "Failure when receiving data from the peer"
```

**原因**: OpenMVG 2.1.0 默认启用 Rerun 日志功能，需要从 GitHub 下载 SDK，但网络连接失败或超时。

**解决方案**: 使用 `-DOpenMVG_USE_RERUN=OFF` 禁用 Rerun 功能（该功能是可选的，不影响核心 SfM 功能）。

### 问题 6: Eigen 3.3.7 SparseCholesky 模块错误

**错误信息**:
```
/usr/include/eigen3/Eigen/SparseCholesky:34:2: error: #error The SparseCholesky module has nothing to offer in MPL2 only mode
error: 'AMDOrdering' does not name a type
```

**原因**: Ubuntu 20.04 默认的 Eigen 3.3.7 版本过旧，部分功能在 MPL2 许可模式下不可用。

**解决方案**: 升级到 Eigen 3.4.0 或更高版本（见编译步骤第 3 步）。

### 问题 7: CPU 架构检测警告

**警告信息**:
```
CMake Warning at cmakeFindModules/OptimizeForArchitecture.cmake:170 (message):
  Your CPU (family 6, model 106) is not known.
```

**原因**: CPU 识别逻辑未包含较新的 CPU 型号。

**影响**: 优化标志会回退到 Core 2 架构，但编译仍会成功。

**解决方案**: 这是警告而非错误，可以忽略。如需优化，可手动指定 `-march=native`。

## 后端集成

### 环境变量配置

在使用 OpenMVG 的 Python 后端中，需要配置以下环境变量：

```bash
# OpenMVG 二进制文件路径
export OPENMVG_BIN_DIR="/root/work/Aerotri-Web/openMVG_Build/openMVG_install/bin"

# 传感器宽度数据库路径
export OPENMVG_SENSOR_DB="/root/work/Aerotri-Web/openMVG/src/openMVG/exif/sensor_width_database/sensor_width_camera_database.txt"
```

### Python 代码配置

在 `backend/app/services/task_runner.py` 中已更新默认路径：

```python
OPENMVG_BIN_DIR = os.environ.get(
    "OPENMVG_BIN_DIR",
    "/root/work/Aerotri-Web/openMVG_Build/openMVG_install/bin"
)
OPENMVG_SENSOR_DB = os.environ.get(
    "OPENMVG_SENSOR_DB",
    "/root/work/Aerotri-Web/openMVG/src/openMVG/exif/sensor_width_database/sensor_width_camera_database.txt"
)
```

### 主要工具说明

| 工具名称 | 功能 |
|---------|------|
| `openMVG_main_SfMInit_ImageListing` | 初始化 SfM 数据场景，扫描图像并提取 EXIF 信息 |
| `openMVG_main_ComputeFeatures` | 计算图像特征点（SIFT/AKAZE 等） |
| `openMVG_main_ComputeMatches` | 特征匹配 |
| `openMVG_main_GeometricFilter` | 几何验证，过滤错误匹配 |
| `openMVG_main_PairGenerator` | 生成图像对（用于匹配） |
| `openMVG_main_SfM` | 执行 SfM 重建（支持 INCREMENTAL/GLOBAL/STELLAR） |
| `openMVG_main_openMVG2Colmap` | 将 OpenMVG 结果转换为 COLMAP 格式 |

## 典型工作流

```bash
# 1. 初始化场景
openMVG_main_SfMInit_ImageListing \
    -i /path/to/images \
    -d /path/to/sensor_db.txt \
    -o /path/to/output/matches

# 2. 计算特征
openMVG_main_ComputeFeatures \
    -i /path/to/output/matches/sfm_data.json \
    -o /path/to/output/matches \
    -m SIFT \
    -p ULTRA

# 3. 生成图像对
openMVG_main_PairGenerator \
    -i /path/to/output/matches/sfm_data.json \
    -o /path/to/output/matches/pairs.txt

# 4. 计算匹配
openMVG_main_ComputeMatches \
    -i /path/to/output/matches/sfm_data.json \
    -p /path/to/output/matches/pairs.txt \
    -o /path/to/output/matches

# 5. 几何过滤
openMVG_main_GeometricFilter \
    -i /path/to/output/matches/sfm_data.json \
    -m /path/to/output/matches/matches.f.bin \
    -g /path/to/output/matches/matches.e.bin

# 6. 全局 SfM 重建
openMVG_main_SfM \
    -i /path/to/output/matches/sfm_data.json \
    -m /path/to/output/matches \
    -o /path/to/output/reconstruction \
    -s GLOBAL \
    -f 10
```

## 参考资源

- [OpenMVG 官方文档](https://github.com/openMVG/openMVG)
- [OpenMVG BUILD 指南](https://github.com/openMVG/openMVG/blob/master/BUILD.md)
- [Eigen 官方网站](http://eigen.tuxfamily.org/)
- [Ceres Solver 文档](http://ceres-solver.org/)

## 版本信息

- **文档创建时间**: 2025-01-15
- **OpenMVG 版本**: 2.1.0
- **文档维护者**: AeroTri 开发团队
