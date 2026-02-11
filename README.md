# 🦞 Aerotri-Web

> **AI-Collaborated Photogrammetry Platform** — 首个 AI 协作开发的摄影测量平台

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Vue 3](https://img.shields.io/badge/Vue-3.x-green.svg)](https://vuejs.org/)
[![AI-Collaborated](https://img.shields.io/badge/AI--Collaborated-✨-purple.svg)](./docs/06-ai-collaboration/)

Aerotri-Web 是一个基于 Web 的航空摄影测量平台，集成多种 SfM（Structure-from-Motion）算法，支持空中三角测量、密集重建、3D Gaussian Splatting 和 3D Tiles 转换。

## ✨ 特性

- **多算法支持**: COLMAP、GLOMAP、InstantSfM、OpenMVG
- **密集重建**: OpenMVS 密集点云、网格重建、纹理映射
- **3D Gaussian Splatting**: 高质量实时 3D 渲染
- **3D Tiles 转换**: 支持 OpenMVS 和 3DGS 输出转换为 3D Tiles
- **地理参考**: GPS → UTM → ENU 坐标转换，支持真实地理定位
- **分区处理**: 大数据集自动分区和合并
- **智能诊断**: AI 驱动的任务失败诊断和自动修复
- **实时进度**: WebSocket 实时进度更新
- **GPU 监控**: 实时 GPU 状态监控和智能分配

## 🎯 AI 协作亮点

本项目是 **首个 AI-Collaborated Algorithm Engineering 开源项目**，展示了：

- **复利工程效应**: 知识持续积累，形成技术复利
- **苏格拉底提问法**: 提问比答案更重要
- **精准上下文**: 只提供相关信息，避免信息过载
- **可追溯性**: 诊断结果明确关联到具体代码位置
- **AI 团队管理者**: 开发者指挥 AI 而非被替代

👉 [了解 AI 协作经验](./docs/06-ai-collaboration/)

## 🚀 快速开始

### Docker 快速启动（推荐）

```bash
# 克隆仓库
git clone https://github.com/your-org/aerotri-web.git
cd aerotri-web

# 启动服务
docker-compose up -d

# 访问 Web 应用
open http://localhost:8000
```

### 本地开发

**后端**:
```bash
cd aerotri-web/backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**前端**:
```bash
cd aerotri-web/frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

👉 [详细安装指南](./docs/02-installation/)

## 📖 文档

- [快速开始](./docs/01-quickstart/) - 5 分钟快速体验
- [安装指南](./docs/02-installation/) - 系统要求和详细安装步骤
- [用户指南](./docs/03-user-guide/) - 功能使用说明
- [算法文档](./docs/04-algorithms/) - 各算法详解
- [开发指南](./docs/05-development/) - 架构和开发流程
- [AI 协作](./docs/06-ai-collaboration/) - AI 协作理念和 Case Studies
- [贡献指南](./docs/07-contribution/) - 如何参与贡献

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                      Frontend (Vue 3)                    │
│  BlockCard, ReconstructionPanel, ThreeViewer, etc.     │
└────────────────────┬────────────────────────────────────┘
                     │ WebSocket + HTTP
┌────────────────────▼────────────────────────────────────┐
│                   Backend (FastAPI)                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│  │ task_runner │  │ openmvs_    │  │   gs_runner     │ │
│  │ (SfM)       │  │ runner      │  │ (3DGS Training) │ │
│  └─────────────┘  └─────────────┘  └─────────────────┘ │
│  ┌──────────────────────────────────────────────────┐  │
│  │    Diagnostic Agent (OpenClaw Integration)       │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│              Algorithms (External Binaries)              │
│  COLMAP | GLOMAP | InstantSfM | OpenMVG | OpenMVS | 3DGS │
└─────────────────────────────────────────────────────────┘
```

## 🔧 环境变量

```bash
# 数据库
AEROTRI_DB_PATH=/root/work/aerotri-web/data/aerotri.db

# 图像根路径
AEROTRI_IMAGE_ROOTS=/data/images:/mnt/storage

# 算法路径
COLMAP_PATH=/usr/local/bin/colmap
GLOMAP_PATH=/usr/local/bin/glomap
INSTANTSFM_PATH=/path/to/ins-sfm
GS_REPO_PATH=/root/work/gs_workspace/gaussian-splatting

# cuDSS (可选，用于 Bundle Adjustment 加速)
CUDSS_DIR=/opt/cudss
```

👉 [完整配置说明](./aerotri-web/backend/config/settings.yaml.example)

## 🛠️ 第三方工具和依赖

### 算法库（必需）

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

### 3D Tiles 转换工具（可选）

用于将 OpenMVS/3DGS 输出转换为 Cesium 3D Tiles 格式：

| 工具 | 用途 | 安装方式 | 源码位置 |
|------|------|----------|----------|
| **obj2gltf** | OBJ → GLB/GLTF | `npm install -g obj2gltf` | [CesiumGS/obj2gltf](./CesiumGS/obj2gltf) |
| **exiftool** | EXIF GPS 提取 | `apt-get install libimage-exiftool-perl` | [exiftool.org](https://exiftool.org/) |
| **tensorboard** | 可视化（可选） | `pip install tensorboard` | [tensorboard.org](https://www.tensorflow.org/tensorboard) |

#### obj2gltf 安装

```bash
# 方式 1: 全局安装（推荐）
npm install -g obj2gltf

# 方式 2: 使用项目源码
cd CesiumGS/obj2gltf
npm install
node bin/obj2gltf.js --version
```

#### 3D Tiles 转换说明

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

**生成的 tileset.json 结构**:
```json
{
  "asset": {"version": "1.1"},
  "geometricError": 500,
  "root": {
    "boundingVolume": {"box": [0, 0, 0, 100, 0, 0, 0, 100, 0, 0, 0, 100]},
    "geometricError": 0,
    "content": {"uri": "model.glb"}
  }
}
```

#### SPZ 压缩工具（3DGS 输出优化）

SPZ 是一种高效的 3D Gaussian Splatting 点云压缩格式，可将 PLY 文件压缩约 10x，显著减少存储和传输开销。

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

**使用方法**:

1. **手动压缩**:
```bash
# 压缩 PLY 文件
ply_to_spz input.ply output.spz

# 或在 Python 中调用
import subprocess
subprocess.run([
    "/path/to/ply_to_spz",
    "point_cloud.ply",
    "point_cloud.spz"
])
```

2. **AeroTri 集成**:
   - 前端参数配置中启用 "训练完成后导SPZ"
   - 训练完成后自动将 `point_cloud.ply` 转换为 `.spz` 格式
   - SPZ 文件保存在 `{gs_output_path}/3dtiles/` 目录下

3. **3D Tiles 集成**:
   - SPZ 文件可直接用于 3D Tiles 转换
   - 支持 `KHR_gaussian_splatting_compression_spz_2` 扩展
   - 在 Cesium 中实现高效加载和渲染

**技术细节**:
- 坐标系: RUB (OpenGL/three.js 约定)
- 依赖: libz (标准 zlib 库)
- 构建: CMake + g++
- 许可证: 自定义开源许可证

### Python 依赖

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

### 系统依赖

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

### 子模块

本项目包含以下子模块：

```bash
# 初始化子模块
git submodule update --init --recursive

# 子模块列表
CesiumGS/obj2gltf          # OBJ 转 GLTF/GLB 工具
CesiumGS/3d-tiles-tools    # 3D Tiles 工具集
CesiumGS/cesium            # CesiumJS 前端库（可选）
```

## 🤝 贡献

我们欢迎所有形式的贡献！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

👉 [贡献指南](./docs/07-contribution/)

## 📊 开源路线图

- [x] Phase 1: 基础设施（文档目录、GitHub 模板）
- [ ] Phase 2: AI 协作专区（Case Studies）
- [ ] Phase 3: OpenClaw 集成（智能诊断）
- [ ] Phase 4: 示例与教程
- [ ] Phase 5: 社区运营

👉 [完整路线图](./docs/DEVELOPMENT_ROADMAP.md)

## 🙏 致谢

- [COLMAP](https://github.com/colmap/colmap) - Structure-from-Motion and Multi-View Stereo
- [GLOMAP](https://github.com/APRIL-ZJU/GLoMAP) - Global Structure-from-Motion
- [OpenMVG](https://github.com/openMVG/openMVG) - Open Multiple View Geometry
- [InstantSfM](https://github.com/zju3dv/instant-sfm) - Instant Structure-from-Motion
- [OpenMVS](https://github.com/cdcseacave/openmvs) - Open Multi-View Stereo Reconstruction
- [3D Gaussian Splatting](https://github.com/nerfstudio-project/gaussian-splatting) - 3D Gaussian Splatting for Real-Time Rendering
- [OpenClaw](https://github.com/openclaw/openclaw) - Personal AI Assistant
- [Claude Code](https://claude.ai/code) - AI 协作开发工具

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 📮 联系方式

- 问题反馈: [GitHub Issues](https://github.com/your-org/aerotri-web/issues)
- 功能建议: [GitHub Discussions](https://github.com/your-org/aerotri-web/discussions)
- 邮件: your-email@example.com

---

**用 ❤️ 和 AI 协作开发**

## 📄 配置

完整配置指南请查看：
- **[配置指南](aerotri-web/backend/config/CONFIGURATION_GUIDE.md)** - 所有配置参数说明

快速配置：
```bash
cd aerotri-web/backend/config
cp settings.yaml.example settings.yaml
vim settings.yaml  # 编辑你的配置
```

