# AeroTri Web - 空中三角测量工具

基于 COLMAP/GLOMAP 的 Web 端空中三角测量工具，提供可视化操作、参数调试、进度监控和结果对比能力。

## 功能特性

- **Block 管理**: 创建、编辑、删除测量项目
  - **图像数量统计**: 创建 Block 时自动统计图像数量，前端显示图像数量标签
- **图像预览**: 支持缩略图浏览、分页加载、删除图像
 - **算法配置**: 
  - 支持 COLMAP (增量式)、GLOMAP (全局式)、InstantSfM (快速全局式) 和 OpenMVG (CPU 友好全局式) 算法
  - 可配置特征提取、匹配、Mapper 参数
  - GPU 加速支持
  - **Pose Prior 支持**: 使用 EXIF GPS 位置先验加速重建（COLMAP/GLOMAP）
  - **地理定位（Georeferencing）**: 支持使用 EXIF GPS 数据将模型对齐到 UTM 坐标系，并生成局部 ENU 偏移模型；3D Tiles 转换时会自动注入 transform 以在 Cesium 中真实定位
    - 可配置对齐最大误差（默认 20 米）和最小公共影像数（默认 3）
    - 支持外部参考影像文件（`georef_ref_images_path`）和自定义 UTM EPSG（`georef_epsg_utm`）
    - 输出 `geo_ref.json` 文件，包含 UTM EPSG、原点坐标和 ENU→ECEF 变换矩阵
  - **GLOMAP mapper_resume**: 支持基于已有 COLMAP 结果进行 GLOMAP 全局优化
  - **OpenMVG Global SfM**: 前端提供 OpenMVG 参数面板，可设置相机模型/默认焦距/特征预设/几何解算方式，后端将自动运行 ImageListing→ComputeFeatures→ComputeMatches→GlobalSfM 并导出 COLMAP 格式结果；默认线程数会根据系统内存与图像数量自动调整，亦可强制指定 `openmvg_params.num_threads`
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
- **重建版本管理**: 当前 Block 支持创建多个 OpenMVS 重建版本（每个版本保留参数/预设、阶段进度、统计和输出），前端提供版本列表、日志查看、产物下载与取消/删除操作
  - **版本级 3D Tiles 转换**: 每个重建版本支持独立的 3D Tiles 转换，版本列表显示 tiles 状态
  - **版本对比**: 在"重建版本对比"页面使用 `BrushCompareViewer`（基于 CesiumJS）并列对比两个版本的 3D Tiles
    - 使用单 Cesium viewer + splitDirection 实现真正的分屏效果，性能更优
    - 支持拖拽分割线调整左右视图比例
    - 两个 tileset 共享同一相机视角，实现同步对比
  - **纹理文件服务**: 支持直接访问纹理文件（OBJ/MTL/纹理图片），Three.js 可正确解析相对路径
- **相机重投影误差可视化**: 
  - 自动计算并显示每个相机的平均重投影误差
  - 支持文本格式（images.txt）和二进制格式（images.bin）的重投影误差计算
  - 相机列表中显示误差值，支持在前端调整“问题相机阈值”（默认 1.0 px）
  - 支持按误差排序和筛选问题相机
  - 3D 视图中相机颜色随阈值动态变化（正常=绿色、问题=蓝色、无误差数据=黄色），并支持“只显示问题相机”
  - 支持分区模式下的重投影误差计算
- **任务队列（Queue）**:
  - 支持将 Block 加入队列/取消排队/置顶
  - 支持设置最大并发数（同时运行任务数上限），后端调度器会自动派发队列任务
  - 支持通过环境变量 `QUEUE_MAX_CONCURRENT` 配置最大并发数（默认 1，范围 1-10）
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
- **3D Tiles 转换**: 
  - 支持将 OpenMVS 重建结果转换为 3D Tiles 格式
  - 转换流程：OBJ → GLB → 3D Tiles
  - 支持查看转换进度、日志和产物列表
  - 支持获取 tileset.json URL 用于 Cesium 等查看器
  - **版本级转换**: 支持为每个重建版本独立转换 3D Tiles，前端提供版本选择器
  - **地理定位支持**: 如果启用了地理定位，转换时会自动在 tileset.json 中注入 root.transform（ENU→ECEF 变换矩阵），使模型在 Cesium 中显示在真实地理位置
- **3D GS Tiles 转换**: 
  - 转换流程：PLY → [SPZ 压缩] → GLTF → 3D Tiles
  - 支持选择不同迭代版本和 SPZ 压缩（使用 `KHR_gaussian_splatting_compression_spz_2` 扩展）
  - SPZ 压缩可减少约 90% 文件大小
  - 支持查看转换进度、日志和产物列表
  - 支持获取 tileset.json URL 用于 Cesium 等查看器

## 技术栈

### 后端
- Python 3.10+
- FastAPI
- SQLite + SQLAlchemy
- WebSocket
- pynvml (GPU 监控)
- aiohttp (WebSocket 可视化代理)
- CORS 中间件（支持跨域请求，包括 FileResponse）

### 前端
- Vue.js 3 + TypeScript
- Vite
- Element Plus
- Pinia
- Three.js
- Cesium（3D Tiles 查看器）

## 快速开始

### 1. 后端启动

```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# [可选] 安装 SPZ Python bindings（用于 SPZ 压缩功能）
# 需要 Python 3.10+，使用 conda 环境
bash scripts/setup_spz_env.sh
# 或者手动创建 conda 环境：
# conda create -n spz-env python=3.10 -y
# conda activate spz-env
# cd third_party/spz && pip install -e .

# 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

> 提示：依赖中包含 `psutil`，用于 OpenMVG 阶段的线程/内存自适应分析；安装后即可让 OpenMVG pipeline 自动检测系统资源。

**SPZ 压缩功能配置**:
- SPZ Python bindings 安装在 conda 环境 `spz-env` 中
- 后端服务会自动检测并使用 conda 环境的 Python 来加载 SPZ 文件
- 可以通过环境变量 `SPZ_PYTHON` 指定 SPZ Python 路径（默认: `/root/miniconda3/envs/spz-env/bin/python`）
- 如果当前 Python 环境已有 SPZ，会优先使用；否则自动使用 conda 环境

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

### 后端配置

AeroTri Web 支持灵活的配置方式，优先级从高到低为：**环境变量 > YAML 配置文件 > 默认值**。

### 最小化启动（无需配置）

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

系统会使用以下默认值：
- 数据库：`./data/aerotri.db`
- 输出目录：`./data/outputs/`
- 算法路径：假设在系统 `PATH` 中

### 环境变量配置

**核心配置**：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `AEROTRI_ENV` | 运行环境（development/production） | `production` |
| `AEROTRI_DEBUG` | 调试模式 | `false` |
| `AEROTRI_DB_PATH` | 数据库文件路径 | `./data/aerotri.db` |
| `AEROTRI_IMAGE_ROOT` | 图像浏览根目录（单个，向后兼容） | `./data/images` |
| `AEROTRI_IMAGE_ROOTS` | 图像浏览根目录（多个，冒号分隔） | - |

**算法路径**：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `COLMAP_PATH` | COLMAP 可执行文件路径 | `colmap`（从 PATH 查找） |
| `GLOMAP_PATH` | GLOMAP 可执行文件路径 | `glomap`（从 PATH 查找） |
| `INSTANTSFM_PATH` | InstantSfM 可执行文件路径 | `ins-sfm` |
| `OPENMVG_BIN_DIR` | OpenMVG 可执行文件目录 | `/usr/local/bin` |
| `OPENMVG_SENSOR_DB` | OpenMVG 相机传感器数据库 | `/usr/local/share/sensor_width_camera_database.txt` |
| `OPENMVS_BIN_DIR` | OpenMVS 可执行文件目录 | `/usr/local/lib/openmvs/bin` |

**3D Gaussian Splatting**：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `GS_REPO_PATH` | 3DGS 训练仓库路径（包含 `train.py`） | `/opt/gaussian-splatting` |
| `GS_PYTHON` | 运行 3DGS 的 Python 解释器（已装好 CUDA 扩展） | `python` |
| `TENSORBOARD_PATH` | TensorBoard 可执行文件 | `tensorboard` |
| `SPZ_PYTHON` | SPZ Python 环境路径 | `python` |

**cuDSS 加速支持**（推荐）：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `CUDSS_DIR` | cuDSS 安装路径 | `/opt/cudss` |

> **重要提示**：COLMAP 和 GLOMAP 的 Bundle Adjustment 阶段可以使用 cuDSS（CUDA Dense Sparse Solver）进行 GPU 加速。
>
> 如果没有正确安装 cuDSS，算法日志会输出：
> ```
> Requested to use GPU for bundle adjustment, but Ceres was compiled without cuDSS support. Falling back to CPU-based sparse solvers
> ```
>
> 这会导致 Bundle Adjustment 阶段运行时间显著延长。
>
> **检查 cuDSS 支持状态**：
> ```bash
> # 检查 Ceres 库是否包含 cuDSS 支持
> ls /root/opt/ceres-2.3-cuda/lib | grep ceres
> ```
>
> 预期输出应包含 `libceres.so` 和 cuDSS 相关库文件。
>
> **安装 cuDSS**（需要 NVIDIA 开发者账号）：
> 1. 从 https://developer.nvidia.com/cudss 下载 cuDSS
> 2. 重新编译 Ceres Solver 并启用 cuDSS 支持：
>    ```bash
>    cd ceres-solver
>    mkdir build && cd build
>    cmake .. \
>      -DCMAKE_CUDA_ARCHITECTURES=native \
>      -DCUDSS_DIR=/path/to/cudss \
>      -DBUILD_SHARED_LIBS=ON
>    make -j$(nproc)
>    sudo make install
>    ```
> 3. 重新编译 COLMAP/GLOMAP

**队列配置**：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `QUEUE_MAX_CONCURRENT` | 队列最大并发数 | `1`（范围 1-10） |

### 使用配置文件（推荐用于生产）

AeroTri Web 采用**双文件配置架构**：

```bash
cd backend/config

# 主配置文件（应用设置、路径、算法配置等）
cp application.yaml.example application.yaml

# 可观测性配置（通知、诊断）
cp observability.yaml.example observability.yaml

# 编辑配置
vim application.yaml
```

**配置文件结构**：
- `application.yaml` - 主配置文件（app、paths、database、algorithms、gpu、queue 等）
- `observability.yaml` - 可观测性配置（DingTalk 通知、诊断 Agent）

**示例配置**（application.yaml）：
```yaml
# 应用配置
app:
  debug: false
  environment: production
  log_level: INFO

# 路径配置
paths:
  data_dir: "./data"
  outputs_dir: "./data/outputs"

# 算法配置
algorithms:
  colmap:
    path: "/usr/local/bin/colmap"
  glomap:
    path: "/usr/local/bin/glomap"

# 3DGS 配置
gaussian_splatting:
  repo_path: "/opt/gaussian-splatting"
  python: "/opt/gs_env/bin/python"

# 图像根路径
image_roots:
  paths:
    - name: "本地数据"
      path: "/data/images"
    - name: "NAS 存储"
      path: "/mnt/storage"
```

### 多环境配置

为不同环境创建独立配置文件：

```bash
# 开发环境
backend/config/application.development.yaml

# 生产环境
backend/config/application.production.yaml

# 激活环境
export AEROTRI_ENV=development
uvicorn app.main:app --reload
```

### 更多配置选项

详细的配置说明请参阅：
- **[完整配置指南](../docs/CONFIGURATION.md)** - 所有配置项的详细说明
- **[可观测性配置示例](../config/observability.yaml.example)** - 通知和诊断配置
- **[迁移指南](../docs/MIGRATION.md)** - 从旧配置系统迁移的步骤

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
| `/api/blocks/{id}/recon-versions` | GET | 重建版本列表（包含每个版本的状态、参数、输出路径、进度） |
| `/api/blocks/{id}/recon-versions` | POST | 创建并启动一个新的 OpenMVS 重建版本 |
| `/api/blocks/{id}/recon-versions/{version_id}` | GET | 获取版本详情 |
| `/api/blocks/{id}/recon-versions/{version_id}` | DELETE | 删除版本（非运行中，含产物清理） |
| `/api/blocks/{id}/recon-versions/{version_id}/cancel` | POST | 取消运行中的版本 |
| `/api/blocks/{id}/recon-versions/{version_id}/files` | GET | 列出版本产物（稠密/网格/纹理） |
| `/api/blocks/{id}/recon-versions/{version_id}/download` | GET | 下载指定版本产物 |
| `/api/blocks/{id}/recon-versions/{version_id}/log_tail` | GET | 获取版本日志 tail |
| `/api/blocks/{id}/recon-versions/{version_id}/texture/{filename:path}` | GET | 服务纹理文件（OBJ/MTL/纹理图片） |
| `/api/blocks/{id}/recon-versions/{version_id}/tiles/convert` | POST | 启动版本级 3D Tiles 转换 |
| `/api/blocks/{id}/recon-versions/{version_id}/tiles/status` | GET | 获取版本 3D Tiles 转换状态 |
| `/api/blocks/{id}/recon-versions/{version_id}/tiles/files` | GET | 列出版本 3D Tiles 产物 |
| `/api/blocks/{id}/recon-versions/{version_id}/tiles/download` | GET | 下载版本 3D Tiles 文件 |
| `/api/blocks/{id}/recon-versions/{version_id}/tiles/tileset_url` | GET | 获取版本 tileset.json URL |
| `/api/blocks/{id}/georef/download` | GET | 下载 geo_ref.json 文件 |
| `/api/reconstruction/presets` | GET | OpenMVS 重建质量预设（fast/balanced/high）及其默认分阶段参数 |
| `/api/reconstruction/params-schema` | GET | OpenMVS 重建参数 schema（类型/范围/说明，用于前端动态表单） |
| `/api/blocks/{id}/reconstruction/status` | GET | OpenMVS 重建状态 |
| `/api/blocks/{id}/reconstruction/files` | GET | OpenMVS 重建产物列表 |
| `/api/blocks/{id}/reconstruction/download` | GET | OpenMVS 重建产物下载 |
| `/api/blocks/{id}/reconstruction/log_tail` | GET | OpenMVS 重建日志 tail |
| `/api/queue` | GET | 队列列表（含当前运行数与最大并发数） |
| `/api/queue/config` | GET/PUT | 队列配置（最大并发数） |
| `/api/queue/blocks/{id}/enqueue` | POST | 将 Block 加入队列 |
| `/api/queue/blocks/{id}/dequeue` | POST | 将 Block 从队列移除 |
| `/api/queue/blocks/{id}/queue/top` | POST | 将 Block 置顶（移动到队列首位） |
| `/api/blocks/{id}/gs/train` | POST | 启动 3DGS 训练 |
| `/api/blocks/{id}/gs/status` | GET | 3DGS 状态 |
| `/api/blocks/{id}/gs/cancel` | POST | 取消 3DGS 训练 |
| `/api/blocks/{id}/gs/files` | GET | 3DGS 产物列表 |
| `/api/blocks/{id}/gs/download` | GET | 3DGS 产物下载 |
| `/api/blocks/{id}/gs/log_tail` | GET | 3DGS 日志 tail |
| `/api/blocks/{id}/gs/tiles/convert` | POST | 启动 3D GS Tiles 转换 |
| `/api/blocks/{id}/gs/tiles/status` | GET | 3D GS Tiles 状态 |
| `/api/blocks/{id}/gs/tiles/cancel` | POST | 取消 3D GS Tiles 转换 |
| `/api/blocks/{id}/gs/tiles/files` | GET | 3D GS Tiles 产物列表 |
| `/api/blocks/{id}/gs/tiles/download` | GET | 3D GS Tiles 产物下载 |
| `/api/blocks/{id}/gs/tiles/log_tail` | GET | 3D GS Tiles 日志 tail |
| `/api/blocks/{id}/gs/tiles/tileset_url` | GET | 获取 3D GS Tiles tileset.json URL |
| `/api/blocks/{id}/tiles/convert` | POST | 启动 3D Tiles 转换（OpenMVS 重建结果） |
| `/api/blocks/{id}/tiles/status` | GET | 3D Tiles 状态 |
| `/api/blocks/{id}/tiles/cancel` | POST | 取消 3D Tiles 转换 |
| `/api/blocks/{id}/tiles/files` | GET | 3D Tiles 产物列表 |
| `/api/blocks/{id}/tiles/download` | GET | 3D Tiles 产物下载 |
| `/api/blocks/{id}/tiles/log_tail` | GET | 3D Tiles 日志 tail |
| `/api/blocks/{id}/tiles/tileset_url` | GET | 获取 tileset.json URL |
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
10. **对比分析**: 创建多个 Block 使用不同算法，在对比页面分析结果；Block 详情页也可以进入「重建版本对比」，同步查看两个 OpenMVS 版本的模型、参数与统计差异

## 3D Tiles 转换

### 前置条件

- 必须先完成 OpenMVS 重建（Block 的 `recon_status` 为 `completed`，且存在重建输出文件）。

### 功能特性

- 支持将 OpenMVS 重建结果（OBJ 格式）转换为 3D Tiles 格式
- **使用 3D Tiles 1.1 格式**：直接引用 GLB 文件，无需 B3DM 转换
- 转换流程：OBJ → GLB → tileset.json (3D Tiles 1.1)
- 支持查看转换进度、阶段和日志
- 支持下载转换产物（tileset.json、GLB 等）
- 支持获取 tileset.json URL，可在 Cesium 等 3D Tiles 查看器中加载

### 技术细节

**3D Tiles 1.1 格式优势**:
- 无需外部工具（3d-tiles-tools），避免 Node 版本兼容问题
- 更快的转换速度（减少一个转换步骤）
- 完全兼容 CesiumJS
- 地理定位支持（自动注入 ENU→ECEF 变换矩阵）

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

### Web 端入口

- 在 Block 详情页切换到 **"3D Tiles"** 标签页：可启动转换任务、查看进度、日志与产物列表。

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

## 3D GS Tiles 转换

### 前置条件

- 必须先完成 3DGS 训练（Block 的 `gs_status` 为 `completed`，且存在训练产物 `point_cloud.ply`）。

### 功能特性

- 支持将 3DGS 训练产物（PLY 格式）转换为 3D Tiles 格式
- 转换流程：PLY → GLTF → 3D Tiles
- 支持选择不同迭代版本（iteration_7000, iteration_30000 等）
- 支持 SPZ 压缩格式，可减少约 90% 文件大小
- 支持查看转换进度、阶段和日志
- 支持下载转换产物（tileset.json、tiles、GLB 等）
- 支持获取 tileset.json URL，可在 Cesium 等 3D Tiles 查看器中加载

### Web 端入口

- 在 Block 详情页的 **"3DGS"** 标签页中，切换到 **"3D Tiles 转换"** 子标签页：可启动转换任务、查看进度、日志与产物列表。
- 产物 `tileset.json` 支持点击 **"Cesium 预览"**：会在对话框中打开 Cesium 查看器进行预览。

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
- **束调整参数**: `bundle_adjustment_optimize_rotations`, `bundle_adjustment_optimize_translation`, `bundle_adjustment_optimize_intrinsics`, `bundle_adjustment_optimize_principal_point`, `bundle_adjustment_optimize_points`, `bundle_adjustment_thres_loss_function`, `bundle_adjustment_loss_function_type`, `bundle_adjustment_max_num_iterations`
  - `bundle_adjustment_loss_function_type`: 损失函数类型，可选值："huber"（默认）、"cauchy"、"softl1"、"trivial"
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
  - 默认最大特征数: `20000`（原为 `15000`），前端上限 `50000`
- 匹配: method (sequential/exhaustive/vocab_tree), overlap
  - **空间匹配**: COLMAP 会自动从数据库检测坐标类型（GPS 或笛卡尔坐标），无需手动指定 `spatial_is_gps` 参数
- **地理定位参数**（适用于 COLMAP/GLOMAP/InstantSfM/OpenMVG）:
  - `georef_enabled`: 启用地理定位（默认 false）
  - `georef_alignment_max_error`: 对齐最大误差（米，默认 20，范围 1-200）
  - `georef_min_common_images`: 最小公共影像数（默认 3，范围 3-50）
  - `georef_ref_images_path`: 外部参考影像文件路径（可选，格式：`IMAGE_NAME X Y Z`，通常为 UTM 米）
  - `georef_epsg_utm`: UTM EPSG 代码（使用外部参考影像时必需，例如 32633 表示 UTM Zone 33N）

### OpenMVG (全局式 SfM) 参数
- `openmvg_params.camera_model`: 相机模型编号（1:Pinhole, 2:Pinhole radial 1, 3:Pinhole radial 3, 4:Pinhole brown 2）
- `openmvg_params.focal_length`: 默认焦距（EXIF 不完整时使用）
- `openmvg_params.feature_preset`: 特征密度（NORMAL/HIGH）
- `openmvg_params.geometric_model`: 几何模型（e=Essential，f=Fundamental）
- `openmvg_params.num_threads`: 线程数（可选；不填则后端自适应）
- `openmvg_params.pair_mode`: 图像对生成模式（EXHAUSTIVE/CONTIGUOUS）
- `openmvg_params.contiguous_count`: 连续模式窗口大小（pair_mode=CONTIGUOUS 时生效）
- `openmvg_params.matching_method`: 匹配方法（AUTO/FASTCASCADEHASHINGL2/...，与 OpenMVG `openMVG_main_ComputeMatches` 参数一致）
- `openmvg_params.ratio`: 距离比率阈值（默认 0.8，越小越严格）

### OpenMVS 重建参数
- `quality_preset`: fast/balanced/high
- `custom_params`: 可选，自定义覆盖各阶段参数：
  - `custom_params.densify`（稠密点云）
  - `custom_params.mesh`（网格重建）
  - `custom_params.refine`（网格优化）
  - `custom_params.texture`（纹理贴图）

### 分区 SfM 参数
- `partition_enabled`: 启用分区模式
- `partition_strategy`: 分区策略（如 "name_range_with_overlap"）
- `partition_params`: 分区参数（partition_size, overlap）
- `sfm_pipeline_mode`: SfM 流水线模式（如 "global_feat_match"）
- `merge_strategy`: 合并策略（"rigid_keep_one" 或 "sim3_keep_one"）
- **分区合并改进**:
  - 完整保留并正确重映射 2D points 数据，确保 point2d_idx 与 tracks 对应关系正确
  - 从 1 开始重新分配所有 ID（image_id, camera_id, point_id），避免溢出问题
  - 使用容差比较进行相机去重，处理不同分区中相同相机的参数差异
  - 使用已合并结果作为参考进行对齐，而非仅使用前一个分区

### GLOMAP mapper_resume 参数
- `input_colmap_path`: 输入 COLMAP 稀疏重建目录路径（包含 cameras.bin/txt, images.bin/txt, points3D.bin/txt）
  - **自动检测**: 如果未设置，会自动检测 `merged/sparse/0`（分区合并结果）或 `sparse/0`（普通结果）
- `glomap_params`: GLOMAP 优化参数（支持所有 GLOMAP mapper 参数，但部分跳过阶段参数在 mapper_resume 模式下不可用）
  - `BundleAdjustment.loss_function_type`: 损失函数类型（"huber", "cauchy", "softl1", "trivial"），默认为 "huber"
- `gpu_index`: GPU 索引

## 许可证

MIT License
