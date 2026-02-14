# 🦞 Aerotri-Web

> **AI-Collaborated Photogrammetry Platform** — 首个 AI 协作开发的摄影测量平台

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Vue 3](https://img.shields.io/badge/Vue-3.x-green.svg)](https://vuejs.org/)
[![AI-Collaborated](https://img.shields.io/badge/AI--Collaborated-✨-purple.svg)](./docs/06-ai-collaboration/)

Aerotri-Web 是一个基于 Web 的航空摄影测量平台，集成多种 SfM（Structure-from-Motion）算法，支持空中三角测量、密集重建、3D Gaussian Splatting 和 3D Tiles 转换。

## ✨ 特性

- **多算法支持**: COLMAP、GLOMAP、InstantSfM、OpenMVG
- **密集重建**: OpenMVS 密集重建、网格重建、纹理映射
- **3D Gaussian Splatting**: 高质量 3D 渲染
- **SPZ 压缩**: 3DGS 点云压缩（~10x 压缩比），支持 `KHR_gaussian_splatting_compression_spz_2` 扩展
- **3D Tiles 转换**: 支持 OpenMVS 和 3DGS 输出转换为 3D Tiles
- **地理参考**: GPS → UTM → ENU 坐标转换，支持真实地理定位
- **分区处理**: 大数据集支持分区和合并
- **企业通知**: 钉钉/飞书集成，支持任务状态监控、周期性汇总、系统健康上报
- **智能诊断**: 基于 OpenClaw 的 AI 驱动任务失败诊断和自动修复
- **任务队列**: 支持置顶、删除、并发控制（1-10）、自动调度
- **多版本管理**: 重建管线支持多版本参数管理和效果对比
- **模型对比**: Cesium 分屏同步对比、刷子式对比，支持 Block 级别和重建版本级别对比
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

## 🎬 演示视频

观看产品演示了解功能：

- [完整功能演示](https://www.bilibili.com/video/BV17EzQBzEP3/) - 核心功能完整演示
- [模型对比功能演示](https://www.bilibili.com/video/BV1mS6uB3Eyu/) - Block 对比和重建版本对比

## 🚀 快速开始

### 本地开发（推荐）

**后端**:
```bash
cd aerotri-web/backend
# 安装依赖
pip install -r requirements.txt
# 或手动安装核心依赖
pip install fastapi uvicorn sqlalchemy pydantic aiofiles python-multipart
# 启动开发服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**前端**:
```bash
cd aerotri-web/frontend
npm install
npm run dev -- --host 0.0.0.0 --port 3000
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

## 🤖 智能诊断 Agent (Diagnostic Agent)

基于 **OpenClaw** 的 AI 驱动任务诊断系统：

### 工作流程

1. **触发**: 任务失败时自动触发
2. **上下文收集**: 收集日志、系统状态、Block 信息、错误堆栈
3. **诊断分析**: 发送给 OpenClaw Agent 进行智能分析
4. **结果输出**: 生成诊断报告并可选自动修复

### 配置

文件：`aerotri-web/backend/config/observability.yaml`

```yaml
diagnostic:
  enabled: true
  openclaw_cmd: "openclaw"
  agent_id: "main"
  agent_memory_path: "/path/to/AerotriWeb_AGENT.md"
  claude_md_path: "/path/to/CLAUDE.md"
  timeout_seconds: 180
  auto_fix: false  # 谨慎启用自动修复
```

### OpenClaw Agent 知识库

Agent 使用项目文档 (`CLAUDE.md`) 和历史诊断经验作为知识库，提供：
- 失败原因分析
- 代码位置定位
- 修复建议
- 自动修复（可选）

## 🔔 通知服务 (Notification Services)

Aerotri-Web 集成企业级通知服务，支持钉钉和飞书：

### 钉钉集成

配置文件：`aerotri-web/backend/config/observability.yaml`

支持多通道通知：

| 通道 | 用途 | 事件类型 |
|------|------|----------|
| **block_events** | Block 运行通知 | task_started, task_completed, task_failed, diagnosis_completed |
| **backend_status** | 后端状态 | system_status, backend_startup, backend_shutdown, backend_error |
| **task_monitor** | 任务监控 | periodic_task_summary (周期性任务汇总) |

### 飞书集成

当前版本支持飞书配置框架（后续迭代）。

### 周期性汇总

- **任务汇总**: 每日定时发送 (cron 配置)
- **系统状态**: 周期性健康检查 (interval 配置)

### 配置示例

```yaml
notification:
  enabled: true
  dingtalk:
    channels:
      block_events:
        enabled: true
        webhook_url: "https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN"
        secret: "YOUR_SECRET"
  periodic:
    task_summary:
      enabled: true
      cron: "0 21 * * *"  # 每天 21:00
```

## 📋 任务队列管理 (Task Queue)

### 功能特性

- **自动调度**: 基于 `max_concurrent` 并发限制自动分发任务
- **队列管理**: 支持置顶 (moveToTop)、删除 (dequeue)、查询 (enqueue)
- **并发控制**: 可配置 1-10 并发任务数
- **实时状态**: WebSocket 实时更新队列状态和运行任务数

### API 端点

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/queue/blocks` | GET | 获取队列列表 |
| `/api/queue/blocks/{id}/enqueue` | POST | 添加到队列 |
| `/api/queue/blocks/{id}/dequeue` | POST | 从队列删除 |
| `/api/queue/blocks/{id}/move-to-top` | POST | 置顶任务 |
| `/api/queue/config` | GET | 获取队列配置 |
| `/api/queue/config` | PUT | 更新并发限制 |

### 环境变量

- `QUEUE_MAX_CONCURRENT`: 最大并发任务数 (默认: 1, 范围: 1-10)

## 🔍 模型对比 (Model Comparison)

### 多版本管理

支持为每个 Block 创建多个重建版本 (ReconVersion)，每个版本独立管理：
- 独立的 OpenMVS 重建参数 (密集重建、网格、纹理)
- 独立的输出目录 (dense/, mesh/, refine/, texture/)
- 独立的 3D Tiles 转换状态
- 版本间参数和效果对比

### Block 级别对比

**功能**: 对比不同 Block 的算法效果

**支持场景**:
- 不同空三算法对比 (COLMAP vs GLOMAP vs InstantSfM vs OpenMVG)
- 同一算法不同参数对比
- 不同数据集效果对比

**页面**: `CompareView.vue`

**对比维度**:
- 稀疏重建统计 (图像数、点云数、相机数)
- 重投影误差分布
- 相机参数对比

### 重建版本级别对比

#### Cesium 分屏对比 (SplitCesiumViewer)

**位置**: 3D Tiles Tab

**特性**:
- 双 Cesium Viewer 分屏显示
- **视角同步**: 可选开启/关闭相机同步
- 可拖动分屏线调整左右比例
- 支持不同重建版本的 3D Tiles 模型对比

#### 刷子式对比 (BrushCompareViewer)

**位置**: 重建 Tab → "对比模型" 按钮

**特性**:
- **单 Cesium Viewer + 后端 stencil 裁剪**: 高性能实现
- 拖动分屏线实时切换左右模型显示
- 刷子式交互：左侧显示左模型，右侧显示右模型
- 适用于同一场景不同参数的精细对比

### API 支持

- `GET /api/blocks/{id}/recon-versions` - 获取重建版本列表
- `POST /api/blocks/{id}/recon-versions` - 创建新版本
- `GET /api/blocks/{id}/recon-versions/{version_id}` - 获取版本详情
- `DELETE /api/blocks/{id}/recon-versions/{version_id}` - 删除版本
- `POST /api/blocks/{id}/recon-versions/{version_id}/cancel` - 取消运行中版本

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
| **Visionary** | 3DGS 查看器 | [源码](https://github.com/Visionary-Laboratory/visionary) | MIT |

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

本项目使用 Git Submodules 管理第三方依赖库：

```bash
# 克隆时自动获取子模块
git clone --recurse-submodules https://github.com/AeroTri/Aerotri-Web.git

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

## 🤝 贡献

我们欢迎所有形式的贡献！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

👉 [贡献指南](./docs/07-contribution/)


## 🙏 致谢

- [COLMAP](https://github.com/colmap/colmap) - Structure-from-Motion and Multi-View Stereo
- [GLOMAP](https://github.com/APRIL-ZJU/GLoMAP) - Global Structure-from-Motion
- [OpenMVG](https://github.com/openMVG/openMVG) - Open Multiple View Geometry
- [InstantSfM](https://github.com/zju3dv/instant-sfm) - Instant Structure-from-Motion
- [OpenMVS](https://github.com/cdcseacave/openmvs) - Open Multi-View Stereo Reconstruction
- [3D Gaussian Splatting](https://github.com/nerfstudio-project/gaussian-splatting) - 3D Gaussian Splatting for Real-Time Rendering
- [OpenClaw](https://github.com/openclaw/openclaw) - Personal AI Assistant
- [Claude Code](https://claude.ai/code) - AI 协作开发工具

## 🗺️ 后续开发规划

### 短期 (0-1 个月)
- [ ] 大场景分 Tile 重建支持
- [ ] ROI (感兴趣区域) 重建支持
- [ ] 大场景 3DGS 分 chunk 训练

### 中期 (1-2 个月)
- [ ] 手持激光雷达工作流支持
- [ ] 大场景分Tile重建，LOD加载

### 开源路线图
- [x] Phase 1: 基础设施（文档目录、GitHub 模板）
- [x] Phase 2: AI 协作专区（Case Studies）
- [x] Phase 3: OpenClaw 集成（智能诊断）
- [ ] Phase 4: 示例与教程
- [ ] Phase 5: 社区运营

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
- **[可观测性配置](aerotri-web/backend/config/observability.yaml.example)** - 通知和诊断配置

快速配置：
```bash
cd aerotri-web/backend/config
cp settings.yaml.example settings.yaml
cp observability.yaml.example observability.yaml  # 可选
vim settings.yaml  # 编辑你的配置
```

