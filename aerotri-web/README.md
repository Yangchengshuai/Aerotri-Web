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
| `COLMAP_PATH` | COLMAP 可执行文件路径 | `/root/work/colmap/build_cuda/src/colmap/exe/colmap` |
| `GLOMAP_PATH` | GLOMAP 可执行文件路径 | `/root/work/colmap/build_cuda/src/glomap/glomap` |
| `INSTANTSFM_PATH` | InstantSfM 可执行文件路径 | 根据安装路径配置 |

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
| `/ws/blocks/{id}/progress` | WebSocket | 实时进度 |

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
8. **合并分区**（如使用分区模式）: 分区完成后可手动触发合并操作
9. **对比分析**: 创建多个 Block 使用不同算法，在对比页面分析结果

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

### InstantSfM (快速全局式 SfM)
- 快速全局式 SfM 算法，适用于大规模数据集

### 通用参数
- 特征提取: max_image_size, max_num_features, camera_model
- 匹配: method (sequential/exhaustive/vocab_tree), overlap

### 分区 SfM 参数
- `partition_enabled`: 启用分区模式
- `partition_strategy`: 分区策略（如 "name_range_with_overlap"）
- `partition_params`: 分区参数（partition_size, overlap）
- `sfm_pipeline_mode`: SfM 流水线模式（如 "global_feat_match"）
- `merge_strategy`: 合并策略（"rigid_keep_one" 或 "sim3_keep_one"）

## 许可证

MIT License
