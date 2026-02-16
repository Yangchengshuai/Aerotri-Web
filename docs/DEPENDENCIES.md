# Aerotri-Web 依赖说明

本文档详细列出 Aerotri-Web 的所有第三方依赖。

## 目录

- [算法库](#算法库必需)
- [3D Tiles 转换工具](#d-tiles-转换工具可选)
- [Python 依赖](#python-依赖)
- [系统依赖](#系统依赖)
- [子模块](#子模块)

---

## 算法库（必需）

项目依赖以下外部算法库，需要单独编译或下载：

| 算法 | 用途 | 安装方式 | 许可证 |
|------|------|----------|--------|
| **COLMAP** | SfM 稀疏重建 | [源码编译](https://github.com/colmap/colmap) | BSD |
| **GLOMAP** | 全局 SfM 优化 | [源码编译](https://github.com/APRIL-ZJU/GLoMAP) | MIT |
| **OpenMVG** | CPU 友好 SfM | [源码编译](https://github.com/openMVG/openMVG) | BSL-1.1 |
| **InstantSfM** | 快速 SfM | [源码编译](https://github.com/zju3dv/instant-sfm) | MIT |
| **OpenMVS** | 密集重建 | [预编译](http://cdcseacave.com/openmvs) 或 [源码](https://github.com/cdcseacave/openmvs) | AGPL-3.0 |
| **3DGS** | 3D 高斯溅射 | [源码](https://github.com/nerfstudio-project/gaussian-splatting) | NVIDIA |
| **Ceres Solver** | 非线性优化 | [源码编译](http://ceres-solver.org) | BSD |
| **Visionary** | 3DGS 查看器 | [源码](https://github.com/Visionary-Laboratory/visionary) | MIT |

### COLMAP 安装

**从源码编译**：

```bash
git clone https://github.com/colmap/colmap.git
cd colmap
mkdir build && cd build
cmake .. -DCMAKE_CUDA_ARCHITECTURES=native
make -j$(nproc)
sudo make install
```

**预编译版本**：
- Ubuntu: `sudo apt-get install colmap`
- macOS: `brew install colmap`

### GLOMAP 安装

```bash
git clone https://github.com/APRIL-ZJU/GLoMAP.git
cd GLoMAP
mkdir build && cd build
cmake ..
make -j$(nproc)
sudo make install
```

### OpenMVG 安装

```bash
git clone https://github.com/openMVG/openMVG.git
cd openMVG
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=RELEASE
make -j$(nproc)
```

### InstantSfM 安装

```bash
git clone https://github.com/zju3dv/instant-sfm.git
cd instant-sfm
# 按照官方文档安装
```

### OpenMVS 安装

**Ubuntu（预编译）**：
```bash
sudo apt-add-repository ppa:cdcseacave/openmvs
sudo apt-get update
sudo apt-get install openmvs
```

**从源码编译**：
```bash
git clone https://github.com/cdcseacave/openMVS.git
cd openMVS
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=RELEASE
make -j$(nproc)
sudo make install
```

### 3D Gaussian Splatting 安装

```bash
git clone --recursive https://github.com/nerfstudio-project/gaussian-splatting.git
cd gaussian-splatting
pip install -r requirements.txt
```

---

## 3D Tiles 转换工具（可选）

用于将 OpenMVS/3DGS 输出转换为 Cesium 3D Tiles 格式：

| 工具 | 用途 | 安装方式 | 源码位置 |
|------|------|----------|----------|
| **obj2gltf** | OBJ → GLB/GLTF | `npm install -g obj2gltf` | [CesiumGS/obj2gltf](../CesiumGS/obj2gltf) |
| **exiftool** | EXIF GPS 提取 | `apt-get install libimage-exiftool-perl` | [exiftool.org](https://exiftool.org/) |
| **tensorboard** | 可视化（可选） | `pip install tensorboard` | [tensorboard.org](https://www.tensorflow.org/tensorboard) |

### obj2gltf 安装

```bash
# 方式 1: 全局安装（推荐）
npm install -g obj2gltf

# 方式 2: 使用项目源码
cd CesiumGS/obj2gltf
npm install
node bin/obj2gltf.js --version
```

### 3D Tiles 转换说明

**本项目使用 3D Tiles 1.1 格式**，无需额外转换工具（如 3d-tiles-tools）。

转换流程：
```
OpenMVS 重建 (OBJ/MTL) → obj2gltf → GLB → tileset.json (3D Tiles 1.1)
```

优势：
- **无外部依赖**: 不依赖 `npx 3d-tiles-tools`，避免 Node 版本兼容问题
- **更快转换**: 直接生成 tileset.json，无需 B3DM 中间格式
- **完全兼容**: 3D Tiles 1.1 原生支持 GLB，Cesium 完美支持
- **地理定位**: 自动注入 ENU→ECEF 变换矩阵（`root.transform`）

---

## Python 依赖

**后端核心依赖** (`requirements.txt`):
- FastAPI >= 0.100.0
- SQLAlchemy >= 2.0
- Pydantic >= 2.0
- uvicorn[standard]
- aiofiles
- python-multipart
- pyproj (地理参考)
- numpy, scipy, opencv-python

**可选依赖**:
- tensorboard (可视化)
- py3dtiles (3D Tiles 生成，替代方案)
- pynvml (GPU 监控)

---

## 系统依赖

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y \
    build-essential \
    git \
    cmake \
    libeigen3-dev \
    libcairo2-dev \
    libpango1.0-dev \
    libglib2.0-dev \
    libimage-exiftool-perl \
    nodejs \
    npm \
    python3-dev \
    python3-pip \
    python3-venv
```

---

## 子模块

本项目使用 Git Submodules 管理第三方依赖库：

```bash
# 克隆时自动获取子模块
git clone --recurse-submodules https://github.com/Yangchengshuai/Aerotri-Web.git

# 或如果已克隆，手动初始化
git submodule update --init --recursive
```

**子模块列表**:

| 子模块 | 路径 | 用途 | 版本 |
|--------|------|------|------|
| **ceres-solver** | `ceres-solver/` | 非线性优化库 | 46b4b3b |
| **colmap** | `colmap3.11/colmap/` | SfM 稀疏重建 | 682ea9a (3.11.1) |
| **gaussian-splatting** | `gs_workspace/gaussian-splatting/` | 3DGS 训练 | main |
| **instantsfm** | `instantsfm/` | 快速 SfM | 0.2.0 |
| **openMVG** | `openMVG/` | CPU 友好 SfM | v2.0 |
| **visionary** | `visionary/` | 3DGS WebGPU 查看器 | main |
| **CesiumGS** | `CesiumGS/` | 3D Tiles 转换工具 | - |

**说明**:
- 子模块使用特定版本 commit 确保稳定性
- 部分子模块配置了固定版本（如 ceres-solver @ 46b4b3b）
- 克隆失败可使用镜像源：`ghfast.top/https://github.com/...`

---

## SPZ 压缩工具（3DGS 输出优化）

SPZ 是一种高效的 3D Gaussian Splatting 点云压缩格式，可将 PLY 文件压缩约 10x。

| 工具 | 用途 | 安装方式 | 源码位置 |
|------|------|----------|----------|
| **ply_to_spz** | PLY → SPZ 压缩 | 见下方说明 | `backend/third_party/spz` |

**特性**:
- 压缩比: 约 10x (183MB → 15MB)
- 无损质量: 压缩后视觉质量几乎无差异
- 快速压缩: C++ 实现的高性能压缩
- 标准格式: 符合 SPZ 规范

**构建 ply_to_spz**:

```bash
cd backend/third_party/spz
mkdir -p build && cd build
cmake ..
make -j$(nproc)

# 验证安装
./ply_to_spz
# Usage: ply_to_spz <input.ply> <output.spz>
```

👉 **安装详情**: [安装指南](./02-installation/)
