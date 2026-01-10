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
  - **GLOMAP mapper_resume**: 支持基于已有 COLMAP 结果进行 GLOMAP 全局优化，创建优化版本
  - **OpenMVG Global SfM（CPU 友好全局式）**: 支持 OpenMVG 全局 SfM 流水线，自动执行 ImageListing/ComputeFeatures/ComputeMatches/GeometricFilter/GlobalSfM，并导出 COLMAP 格式结果供前端可视化和后续处理；可在前端设置相机模型、默认焦距、几何模型与线程数
  - **版本管理**: 支持查看和管理同一 Block 的不同版本（原始结果 + GLOMAP 优化版本）
  - **分区 SfM 功能**: 支持大规模数据集的分区重建和合并
    - 分区配置：可配置分区大小、重叠区域、SfM 流水线模式
    - 分区管理：查看分区状态、进度和独立结果
    - 分区合并：支持多种合并策略（rigid_keep_one, sim3_keep_one）
  - **参数优化**: 
    - 默认相机模型从 `SIMPLE_RADIAL` 改为 `OPENCV`
    - 默认最大特征数从 `15000` 提升至 `20000`，前端上限提升至 `50000`
    - 空间匹配自动检测坐标类型（GPS/笛卡尔），移除手动 `spatial_is_gps` 参数
    - **GLOMAP Bundle Adjustment 损失函数类型支持**: 支持配置损失函数类型（"huber"、"cauchy"、"softl1"、"trivial"），默认为 "huber"
  - **分区合并改进**:
    - 修复分区合并时 2D points 数据丢失问题，完整保留并正确重映射 point3d_id
    - 改进 ID 重映射机制，从 1 开始重新分配以避免溢出问题
    - 修复相机参数读取，使用相机模型映射而非文件中的 num_params 字段
    - 修复 cameras.bin 写入格式，符合 COLMAP 标准格式（不包含 num_params 字段）
    - 添加溢出检查和验证，防止 ID 超出 32/64 位整数限制
    - 改进相机去重逻辑，使用容差比较处理不同分区中相同相机的参数差异
    - 改进重叠图像对齐，使用已合并结果而非仅前一个分区作为参考
- 结果浏览与分析
  - 三维视图中展示相机轨迹与稀疏点云
  - 支持从后端按需抽样加载点云，以及一键下载完整 `points3D.ply` 点云文件
  - **分区模式支持**: 可在分区视图和合并结果视图之间切换
  - **分区统计**: 支持查看各分区的统计信息和合并后的聚合统计
  - **版本切换**: 支持在 3D 视图中切换不同版本的结果（原始 + GLOMAP 优化版本）
  - **相机选择与交互**: 支持双击选择相机、查看相机详情、删除相机
  - **相机重投影误差可视化**: 自动计算并显示每个相机的平均重投影误差，支持在前端调整问题相机阈值（默认 1.0 px）；在列表与 3D 视图中以颜色标识（正常=绿色、问题=蓝色、无误差数据=黄色），并支持按误差排序和筛选
- OpenMVS 重建流水线（实验特性）
  - 针对已完成的 SfM 结果，可发起稠密重建 / 网格 / 纹理流水线（OpenMVS）
  - 后端在 Block 上维护独立的重建状态字段（`recon_status`、`recon_progress`、`recon_current_stage` 等）
  - 前端在「重建」页签中展示进度、阶段与输出文件列表，支持下载重建产物
  - **重建参数预设 + 自定义参数**: 支持 fast/balanced/high 质量预设，并允许对稠密/网格/优化/纹理各阶段参数进行覆盖（前端“高级参数”面板）
  - **重建版本管理与对比**: 支持创建/取消/删除多个版本；提供 `/blocks/{id}/recon-versions` 系列 API（列表/创建/获取/取消/删除/文件/下载/日志 tail）；新增版本列表卡片与“重建版本对比”页面，配合 `SplitModelViewer` 同步展示两个 OBJ 并并列展示参数与统计差异
  - 改进：修复去畸变阶段的异常退出处理，即使程序异常退出但输出文件已生成也视为成功
  - 改进：自动配置 Ceres 库路径到 LD_LIBRARY_PATH，解决运行时库依赖问题
- 任务队列与并发控制
  - 支持将 Block 加入队列、取消排队、置顶
  - 支持设置最大并发数（同时运行任务数量上限），后端调度器会自动从队列派发任务
- 3DGS（3D Gaussian Splatting）训练与预览
  - 后端封装 3DGS 训练任务（通过 `GS_REPO_PATH` / `GS_PYTHON` 调用外部仓库）
  - Block 维度维护独立的 3DGS 状态字段（`gs_status`、`gs_progress`、`gs_current_stage` 等），支持任务恢复
  - 前端在「3DGS」页签中配置训练参数、选择 GPU、查看日志与产物列表
  - 内置基于 WebGPU 的 `visionary` 预览页，可在线预览导出的 `point_cloud.ply`
  - **自动相机模型检测与去畸变**: 训练前自动检测相机模型，如非 PINHOLE/SIMPLE_PINHOLE 则自动运行 COLMAP image_undistorter
  - **RTX 5090 支持**: 自动配置 CUDA 架构以支持 RTX 5090（Blackwell sm_120）
- 3D GS Tiles 转换
  - 支持将 3DGS 训练产物（PLY 格式）转换为 3D Tiles 格式
  - Block 维度维护独立的 3D GS Tiles 状态字段（`gs_tiles_status`、`gs_tiles_progress`、`gs_tiles_current_stage` 等），支持任务恢复
  - 前端在「3DGS」页签的「3D Tiles 转换」子标签页中启动转换任务、查看进度、日志与产物列表
  - 支持选择不同迭代版本（iteration_7000, iteration_30000 等）
  - 支持 SPZ 压缩格式，可减少约 90% 文件大小
  - 支持获取 tileset.json URL，可在 Cesium 等 3D Tiles 查看器中加载
- 3D Tiles 转换
  - 支持将 OpenMVS 重建结果（OBJ 格式）转换为 3D Tiles 格式，用于 Web 端可视化
  - Block 维度维护独立的 3D Tiles 状态字段（`tiles_status`、`tiles_progress`、`tiles_current_stage` 等），支持任务恢复
  - 前端在「3D Tiles」页签中启动转换任务、查看进度、日志与产物列表
  - 支持获取 tileset.json URL，可在 Cesium 等 3D Tiles 查看器中加载
- InstantSfM 实时可视化
  - 支持启用实时可视化功能，通过 WebSocket 实时显示优化过程、相机位姿和点云
  - 前端提供实时可视化查看器，可在任务运行期间查看优化进度
- 相机选择与交互
  - 3D 视图中支持双击选择相机，查看相机详情信息
  - 支持删除选中的相机，实时更新 3D 场景

## 快速开始（AeroTri Web）

### 后端

```bash
cd aerotri-web/backend
python3 -m pip install -r requirements.txt
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

> 注意：`pip install -r requirements.txt` 会安装 `psutil`，供 OpenMVG pipeline 的线程/内存自适应逻辑使用（无需额外配置）。

> 如需启用 GLOMAP / InstantSfM / OpenMVS / OpenMVG，请根据文档提前准备好对应可执行程序与环境变量（如 `GLOMAP_PATH`、`INSTANTSFM_PATH`、`OPENMVG_BIN_DIR`、`OPENMVG_SENSOR_DB` 等）。

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
