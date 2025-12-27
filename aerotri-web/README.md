# AeroTri Web - 空中三角测量工具

基于 COLMAP/GLOMAP 的 Web 端空中三角测量工具，提供可视化操作、参数调试、进度监控和结果对比能力。

## 功能特性

- **Block 管理**: 创建、编辑、删除测量项目
- **图像预览**: 支持缩略图浏览、分页加载、删除图像
- **算法配置**: 
  - 支持 COLMAP (增量式)、GLOMAP (全局式) 和 InstantSfM (快速全局式) 算法
  - 可配置特征提取、匹配、Mapper 参数
  - GPU 加速支持
  - **Pose Prior 支持**: 使用 EXIF GPS 位置先验加速重建（COLMAP/GLOMAP）
  - **GLOMAP mapper_resume**: 支持基于已有 COLMAP 结果进行 GLOMAP 全局优化
  - **版本管理**: 支持查看和管理同一 Block 的不同版本（原始结果 + 优化版本）
- **GPU 监控**: 实时显示 GPU 状态，选择空闲 GPU；组件每 2 秒自动轮询 GPU 数据以更新状态（轮询期间刷新按钮会隐藏，避免界面闪烁）
- **进度监控**: 
  - 实时阶段指示器
  - WebSocket 推送进度
  - 日志实时显示
- **3D 可视化**: 
  - Three.js 渲染相机位姿和稀疏点云
  - 交互式旋转、缩放、平移
  - 图层显示控制
  - **分区模式支持**: 支持查看单个分区结果或合并后的结果
  - **版本切换**: 支持在 3D 视图中切换不同版本的结果（原始 + GLOMAP 优化版本）
  - **相机选择与交互**: 支持双击选择相机、查看相机详情、删除相机
- **统计分析**: 
  - 处理结果统计
  - 各阶段耗时
  - 算法参数记录
  - **分区统计**: 支持查看各分区的统计信息和合并后的聚合统计
- **分区 SfM**: 
  - 支持大规模数据集的分区重建
  - 分区配置：可配置分区大小、重叠区域、SfM 流水线模式
  - 分区管理：查看分区状态、进度和结果
  - 分区合并：支持多种合并策略（rigid_keep_one, sim3_keep_one）
- **Block 对比**: 对比不同算法/参数的处理结果

## 技术栈

### 后端
- Python 3.10+
- FastAPI
- SQLite + SQLAlchemy
- WebSocket
- pynvml (GPU 监控)
- aiohttp (WebSocket 可视化代理)

### 前端
- Vue.js 3 + TypeScript
- Vite
- Element Plus
- Pinia
- Three.js

## 快速开始

### 1. 后端启动

```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. 前端启动

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

访问 http://localhost:3000

### 3. 运行测试

```bash
# 后端测试
cd backend
pytest

# 前端测试
cd frontend
npm run test
```

## 环境变量

### 后端

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `AEROTRI_DB_PATH` | 数据库文件路径 | `/root/work/aerotri-web/data/aerotri.db` |
| `AEROTRI_IMAGE_ROOT` | 图像浏览根目录 | `/mnt/work_odm/chengshuai` |
| `COLMAP_PATH` | COLMAP 可执行文件路径 | `/usr/local/bin/colmap`（可改为自编译路径，如 `/root/work/colmap3.11/colmap/build/src/colmap/exe/colmap`） |
| `GLOMAP_PATH` | GLOMAP 可执行文件路径 | `/usr/local/bin/glomap`（可改为自编译路径，如 `/root/work/glomap/build/glomap/glomap`） |
| `INSTANTSFM_PATH` | InstantSfM 可执行文件路径 | 根据安装路径配置（例如 `ins-sfm`） |
| `GS_REPO_PATH` | 3DGS 训练仓库路径（包含 `train.py`） | `/root/work/gs_workspace/gaussian-splatting` |
| `GS_PYTHON` | 运行 3DGS 的 Python 解释器（已装好 gaussian-splatting 依赖与 CUDA 扩展） | `/root/work/gs_workspace/gs_env/bin/python`（默认值，可通过环境变量覆盖） |

## API 文档

启动后端后访问 http://localhost:8000/docs 查看 Swagger API 文档。

### 主要 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/blocks` | GET/POST | Block 列表/创建 |
| `/api/blocks/{id}` | GET/PATCH/DELETE | Block 详情/更新/删除 |
| `/api/blocks/{id}/images` | GET | 图像列表 |
| `/api/blocks/{id}/run` | POST | 提交任务 |
| `/api/blocks/{id}/status` | GET | 任务状态 |
| `/api/blocks/{id}/stop` | POST | 停止任务 |
| `/api/gpu/status` | GET | GPU 状态 |
| `/api/blocks/{id}/result/cameras` | GET | 相机数据 |
| `/api/blocks/{id}/result/points` | GET | 点云数据 |
| `/api/blocks/{id}/partitions/config` | GET/PUT | 分区配置 |
| `/api/blocks/{id}/partitions/preview` | POST | 分区预览 |
| `/api/blocks/{id}/partitions/status` | GET | 分区状态 |
| `/api/blocks/{id}/partitions/{index}/result/*` | GET | 分区结果 |
| `/api/blocks/{id}/merge` | POST | 合并分区结果 |
| `/api/blocks/{id}/reconstruct` | POST | OpenMVS 重建（开始） |
| `/api/blocks/{id}/reconstruction/status` | GET | OpenMVS 重建状态 |
| `/api/blocks/{id}/reconstruction/files` | GET | OpenMVS 重建产物列表 |
| `/api/blocks/{id}/reconstruction/download` | GET | OpenMVS 重建产物下载 |
| `/api/blocks/{id}/reconstruction/log_tail` | GET | OpenMVS 重建日志 tail |
| `/api/blocks/{id}/gs/train` | POST | 启动 3DGS 训练 |
| `/api/blocks/{id}/gs/status` | GET | 3DGS 状态 |
| `/api/blocks/{id}/gs/cancel` | POST | 取消 3DGS 训练 |
| `/api/blocks/{id}/gs/files` | GET | 3DGS 产物列表 |
| `/api/blocks/{id}/gs/download` | GET | 3DGS 产物下载 |
| `/api/blocks/{id}/gs/log_tail` | GET | 3DGS 日志 tail |
| `/api/blocks/{id}/glomap/mapper_resume` | POST | GLOMAP mapper_resume 优化任务 |
| `/api/blocks/{id}/versions` | GET | Block 版本列表 |
| `/ws/blocks/{id}/progress` | WebSocket | 实时进度 |
| `/ws/blocks/{id}/visualization` | WebSocket | InstantSfM 实时可视化 |

## 目录结构

```
aerotri-web/
├── backend/
│   ├── app/
│   │   ├── api/           # API 路由
│   │   ├── models/        # 数据模型
│   │   ├── services/      # 业务逻辑
│   │   ├── ws/            # WebSocket
│   │   ├── main.py        # 入口
│   │   └── schemas.py     # Pydantic 模型
│   ├── tests/             # 测试
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/           # API 调用
│   │   ├── components/    # Vue 组件
│   │   ├── composables/   # 组合式函数
│   │   ├── stores/        # Pinia stores
│   │   ├── types/         # TypeScript 类型
│   │   └── views/         # 页面视图
│   └── package.json
└── README.md
```

## 使用流程

1. **新建 Block**: 点击"新建 Block"，输入名称和图像目录路径
2. **配置参数**: 选择算法 (COLMAP/GLOMAP/InstantSfM)，配置特征提取、匹配、Mapper 参数
   - 可选：启用 Pose Prior（使用 EXIF GPS 位置先验）
   - 可选：启用分区模式（适用于大规模数据集）
3. **分区配置**（如启用）: 配置分区大小、重叠区域、SfM 流水线模式和合并策略
4. **选择 GPU**: 查看 GPU 状态，选择空闲的 GPU
5. **运行空三**: 点击"运行空三"开始处理
6. **监控进度**: 实时查看处理阶段和进度
   - 分区模式：可查看各分区的独立进度
7. **查看结果**: 完成后在 3D 视图中浏览相机位姿和点云
   - 分区模式：可在分区视图和合并结果视图之间切换
   - 版本管理：可在版本选择器中切换不同版本的结果（原始 + GLOMAP 优化版本）
8. **合并分区**（如使用分区模式）: 分区完成后可手动触发合并操作
9. **GLOMAP 优化**（可选）: 对于已完成的 GLOMAP Block，可点击"使用 GLOMAP 继续优化"按钮，基于当前结果进行一轮 mapper_resume 全局优化
10. **对比分析**: 创建多个 Block 使用不同算法，在对比页面分析结果

## 3DGS（3D Gaussian Splatting）训练与预览（V1）

### 前置条件

- 必须先完成 SfM（Block 状态为 `completed`，且存在 `data/outputs/{block_id}/sparse/0`）。
- 后端需配置 `GS_REPO_PATH`/`GS_PYTHON`（见上文环境变量）。

### 自动相机模型检测与去畸变

- 3DGS 训练前会自动检测相机模型（从 COLMAP 稀疏重建中读取）
- 如果相机模型不是 `PINHOLE` 或 `SIMPLE_PINHOLE`，会自动运行 COLMAP `image_undistorter` 进行去畸变
- 去畸变后的图像和相机参数将用于 3DGS 训练，确保兼容性

### RTX 5090 支持

- 自动设置 `TORCH_CUDA_ARCH_LIST=12.0` 以支持 RTX 5090（Blackwell sm_120）架构

### Web 端入口

- 在 Block 详情页切换到 **"3DGS"** 标签页：可配置训练参数、选择 GPU、启动/取消训练、查看日志与产物列表。
- 产物 `point_cloud.ply` 支持点击 **"预览"**：会在同域页面 `/visionary/index.html` 中打开。

### 预览兼容性说明

- 预览依赖 WebGPU，推荐 Chrome/Edge 较新版本 + 独显环境。
- 若浏览器/驱动不支持 WebGPU，可使用"下载"将 `point_cloud.ply` 下载到本地离线查看。

## 支持的算法参数

### COLMAP (增量式 SfM)
- `use_pose_prior`: 使用 EXIF GPS 位置先验加速重建
- `Mapper.ba_use_gpu`: BA GPU 加速
- `Mapper.ba_gpu_index`: GPU 索引

### GLOMAP (全局式 SfM)
- `use_pose_prior`: 使用 EXIF GPS 位置先验加速全局定位和 BA
- `GlobalPositioning.use_gpu`: 全局定位 GPU 加速
- `GlobalPositioning.min_num_images_gpu_solver`: GPU Solver 最小图像数
- `BundleAdjustment.use_gpu`: BA GPU 加速
- **跳过阶段控制**: `skip_preprocessing`, `skip_view_graph_calibration`, `skip_relative_pose_estimation`, `skip_rotation_averaging`, `skip_track_establishment`, `skip_global_positioning`, `skip_bundle_adjustment`, `skip_retriangulation`, `skip_pruning`
- **迭代参数**: `ba_iteration_num`, `retriangulation_iteration_num`
- **轨迹建立参数**: `track_establishment_min_num_tracks_per_view`, `track_establishment_min_num_view_per_track`, `track_establishment_max_num_view_per_track`, `track_establishment_max_num_tracks`
- **全局定位参数**: `global_positioning_optimize_positions`, `global_positioning_optimize_points`, `global_positioning_optimize_scales`, `global_positioning_thres_loss_function`, `global_positioning_max_num_iterations`
- **束调整参数**: `bundle_adjustment_optimize_rotations`, `bundle_adjustment_optimize_translation`, `bundle_adjustment_optimize_intrinsics`, `bundle_adjustment_optimize_principal_point`, `bundle_adjustment_optimize_points`, `bundle_adjustment_thres_loss_function`, `bundle_adjustment_max_num_iterations`
- **重三角化参数**: `triangulation_complete_max_reproj_error`, `triangulation_merge_max_reproj_error`, `triangulation_min_angle`, `triangulation_min_num_matches`
- **内点阈值参数**: `thresholds_max_angle_error`, `thresholds_max_reprojection_error`, `thresholds_min_triangulation_angle`, `thresholds_max_epipolar_error_E`, `thresholds_max_epipolar_error_F`, `thresholds_max_epipolar_error_H`, `thresholds_min_inlier_num`, `thresholds_min_inlier_ratio`, `thresholds_max_rotation_error`

### InstantSfM (快速全局式 SfM)
- 快速全局式 SfM 算法，适用于大规模数据集
- **实时可视化**: 支持启用实时可视化功能，实时显示优化过程、相机位姿和点云（需要 InstantSfM 支持）
  - `enable_visualization`: 启用实时可视化
  - `visualization_port`: 可视化端口（可选，留空则自动检测 viser 服务器端口）

### 通用参数
- 特征提取: max_image_size, max_num_features, camera_model
  - 默认相机模型: `OPENCV`（原为 `SIMPLE_RADIAL`）
  - 默认最大特征数: `15000`（原为 `12000`）
- 匹配: method (sequential/exhaustive/vocab_tree), overlap
  - **空间匹配**: COLMAP 会自动从数据库检测坐标类型（GPS 或笛卡尔坐标），无需手动指定 `spatial_is_gps` 参数

### 分区 SfM 参数
- `partition_enabled`: 启用分区模式
- `partition_strategy`: 分区策略（如 "name_range_with_overlap"）
- `partition_params`: 分区参数（partition_size, overlap）
- `sfm_pipeline_mode`: SfM 流水线模式（如 "global_feat_match"）
- `merge_strategy`: 合并策略（"rigid_keep_one" 或 "sim3_keep_one"）

### GLOMAP mapper_resume 参数
- `input_colmap_path`: 输入 COLMAP 稀疏重建目录路径（包含 cameras.bin/txt, images.bin/txt, points3D.bin/txt）
- `glomap_params`: GLOMAP 优化参数（支持所有 GLOMAP mapper 参数，但部分跳过阶段参数在 mapper_resume 模式下不可用）
- `gpu_index`: GPU 索引

## 许可证

MIT License
