## colmap_glomap 项目总览

本仓库用于汇总 **COLMAP/GLOMAP 源码**、**COLMAP 3.11 自编译版本**、**GLOMAP 上游源码镜像**、**Ceres-Solver 数值优化库**、**InstantSfM（快速全局式 SfM）**、**OpenMVS 重建工具链** 与配套的 **AeroTri Web（网页端空三与重建工具）** 以及 **3DGS（3D Gaussian Splatting）训练/预览集成**。

- **COLMAP**：增量式 SfM（空三）与 MVS 工具链（本仓库内路径：`colmap/`）
- **InstantSfM**：基于 COLMAP 的快速全局式 SfM 算法（本仓库内路径：`instantsfm/`，通过 `ins-sfm` 命令调用）
- **OpenMVS**：多视图立体重建（MVS）与网格/纹理重建工具链（本仓库内路径：`openMVS/`）
- **AeroTri Web**：面向空三调参、批处理与重建可视化的 Web 应用（本仓库内路径：`aerotri-web/`）

> 备注：为避免把本机/服务器上的数据集、重建输出、`node_modules` 等大文件推到仓库，已在根目录提供 `.gitignore`，并忽略 `aerotri-web/data/`、`openMVS/build*/` 等编译/运行时中间文件。

## 目录结构

```
work/
├── colmap/                 # COLMAP 源码（已脱离子仓库形式，作为普通目录提交）
├── colmap3.11/             # COLMAP 3.11 源码及本地构建目录（仅源码纳入版本控制）
├── ceres-solver/           # Ceres-Solver 数值优化库源码（仅源码纳入版本控制）
├── glomap/                 # GLOMAP 上游源码镜像（作为独立目录提交）
├── instantsfm/             # InstantSfM 源码/环境（通过 ins-sfm 命令调用）
├── openMVS/                # OpenMVS 源码与构建目录（仅源码纳入版本控制）
├── aerotri-web/            # Web 应用：FastAPI 后端 + Vue3 前端 + 3DGS/WebGPU 可视化
└── docs/                   # 本项目说明/使用/开发文档
```

> 说明：`ceres-solver/`、`colmap3.11/`、`glomap/` 目录中的 **源码** 会随仓库提交，内部的 `build*/`、`CMakeFiles/` 等编译中间文件通过根目录 `.gitignore` 统一忽略，不会进入版本控制。

## 文档

- **项目说明文档**：`docs/项目说明文档.md`
- **项目使用文档**：`docs/项目使用文档.md`
- **项目开发文档**：`docs/项目开发文档.md`
- **重建设计文档**：`docs/openmvs_reconstruction_design.md`、`docs/openmvs_reconstruction_prd.md`（如存在）

## AeroTri Web 功能概览

AeroTri Web 后端通过 FastAPI 暴露统一接口，前端使用 Vue3 + Element Plus 实现可视化与任务管理，当前主要能力包括：

- SfM 空三重建
  - 支持 COLMAP（增量式）、GLOMAP（全局式）与 InstantSfM（快速全局式）管线
  - **Pose Prior 支持**: COLMAP/GLOMAP 支持使用 EXIF GPS 位置先验加速重建
  - **分区 SfM 功能**: 支持大规模数据集的分区重建和合并
    - 分区配置：可配置分区大小、重叠区域、SfM 流水线模式
    - 分区管理：查看分区状态、进度和独立结果
    - 分区合并：支持多种合并策略（rigid_keep_one, sim3_keep_one）
- 结果浏览与分析
  - 三维视图中展示相机轨迹与稀疏点云
  - 支持从后端按需抽样加载点云，以及一键下载完整 `points3D.ply` 点云文件
  - **分区模式支持**: 可在分区视图和合并结果视图之间切换
  - **分区统计**: 支持查看各分区的统计信息和合并后的聚合统计
- OpenMVS 重建流水线（实验特性）
  - 针对已完成的 SfM 结果，可发起稠密重建 / 网格 / 纹理流水线（OpenMVS）
  - 后端在 Block 上维护独立的重建状态字段（`recon_status`、`recon_progress`、`recon_current_stage` 等）
  - 前端在「重建」页签中展示进度、阶段与输出文件列表，支持下载重建产物
- 3DGS（3D Gaussian Splatting）训练与预览
  - 后端封装 3DGS 训练任务（通过 `GS_REPO_PATH` / `GS_PYTHON` 调用外部仓库）
  - Block 维度维护独立的 3DGS 状态字段（`gs_status`、`gs_progress`、`gs_current_stage` 等），支持任务恢复
  - 前端在「3DGS」页签中配置训练参数、选择 GPU、查看日志与产物列表
  - 内置基于 WebGPU 的 `visionary` 预览页，可在线预览导出的 `point_cloud.ply`

## 快速开始（AeroTri Web）

### 后端

```bash
cd aerotri-web/backend
python3 -m pip install -r requirements.txt
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

> 如需启用 GLOMAP / InstantSfM / OpenMVS，请根据文档提前准备好对应可执行程序与环境变量（如 `GLOMAP_PATH`、`INSTANTSFM_PATH` 等）。

### 前端

```bash
cd aerotri-web/frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

访问：`http://<server-ip>:5173`

## 许可证

- `colmap/` 目录遵循其上游项目 LICENSE/协议。
- `instantsfm/`、`openMVS/` 目录遵循各自上游项目 LICENSE/协议（如有）。
- `aerotri-web/` 目录为本项目 Web 工具部分，遵循其目录下声明（如有）。
