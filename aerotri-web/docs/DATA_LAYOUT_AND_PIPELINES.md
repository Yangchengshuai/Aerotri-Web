## AeroTri Web 数据目录与流水线说明

本文梳理 `/root/work/aerotri-web` 的目录结构、数据库与各类输出文件的关系，重点说明：

- Block 工作目录：`data/blocks/`
- 空三（SfM）输出目录：`data/outputs/`
- 缩略图缓存：`data/thumbnails/`
- 核心数据库：`aerotri.db`、`database.db`、`sparse/0`、`recon/` 等

并对当前 OpenMVS 重建 runner 的输入输出路径做对照说明。

---

## 1. 顶层目录结构总览

```text
/root/work/aerotri-web
├── backend/                      # FastAPI 后端（API、模型、服务、WebSocket）
│   └── app/
│       ├── api/                  # REST API 路由
│       ├── models/               # ORM 模型 & 数据库初始化
│       ├── schemas.py            # Pydantic 请求/响应模型
│       ├── services/             # 任务执行、文件解析、工作区管理等服务
│       └── ws/                   # WebSocket 进度推送
├── frontend/                     # Vue + ElementPlus 前端
├── data/                         # 所有持久化数据（数据库 + 任务输出）
│   ├── aerotri.db                # 主业务数据库（SQLite）
│   ├── blocks/                   # 每个 Block 的工作目录（工作图像等）
│   ├── outputs/                  # 每个 Block 的 SfM / 重建输出目录
│   └── thumbnails/               # 所有图片缩略图缓存
└── tools/, README.md, ...
```

从“一个 Block 的生命周期”来看：

- **`aerotri.db`** 记录 Block 的元数据和状态；
- **`data/blocks`** 存放每个 Block 的“工作影像数据集”（安全可变区）；
- **`data/outputs`** 存放空三（SfM）和 OpenMVS 重建的输出；
- **`data/thumbnails`** 存放所有图片的缩略图缓存。

### 1.1 backend/app 结构与主要脚本作用

```text
backend/app
├── main.py                # FastAPI 入口，挂载 API & WS，并调用 init_db()
├── api/                   # REST API 分模块路由
│   ├── blocks.py          # Block 的 CRUD（创建、列表、更新、删除）
│   ├── images.py          # Block 内图像列表、缩略图、原图访问、删除
│   ├── filesystem.py      # 浏览服务器文件系统，选择图像目录
│   ├── gpu.py             # GPU 状态查询
│   ├── tasks.py           # 空三任务：/blocks/{id}/run|status|stop
│   ├── results.py         # SfM 结果访问：相机、点云、统计
│   └── reconstruction.py  # OpenMVS 重建：reconstruct / status / files / download
├── models/
│   ├── block.py           # Block ORM 模型（见第 2 节）
│   └── database.py        # SQLite 连接、AsyncSessionLocal、init_db + 轻量迁移
├── schemas.py             # Blocks / Tasks / Images / GPU / Reconstruction 等 Pydantic 模型
├── services/
│   ├── task_runner.py     # 空三任务调度：COLMAP/GLOMAP CLI、进度解析、日志写入
│   ├── openmvs_runner.py  # OpenMVS 重建流水线：undistort → densify → mesh → refine → texture
│   ├── workspace_service.py # per-block 工作目录 & 图像硬链接/软链接管理
│   ├── image_service.py   # 缩略图生成与缓存、图像尺寸统计
│   ├── result_reader.py   # 读取 COLMAP binary（cameras.bin / points3D.bin）并转换为 API 结构
│   ├── log_parser.py      # 解析 COLMAP/GLOMAP 日志，提取阶段进度，用于 WebSocket 与 DB 更新
│   └── gpu_service.py 等   # GPU 信息、工作区辅助等（按文件名职责划分）
└── ws/
    └── progress.py        # WebSocket `/ws/blocks/{id}/progress`，由 TaskRunner/OpenMVSRunner 推送进度
```

整体关系可用下图概括：

```text
[Frontend] ──HTTP/WS──> [backend/app/main.py]
   │                        │
   │                        ├── api/*.py        # REST 路由
   │                        ├── ws/progress.py  # WebSocket 路由
   │                        └── services/*.py   # 具体业务执行
   │
   └── 通过 Block ID 与 DB + data/blocks + data/outputs 对应
```

---

## 2. Block 记录结构（aerotri.db）

### 2.1 `blocks` 表（模型：`backend/app/models/block.py`）

```text
表：blocks
主键：id (UUID, string)
```

关键字段（只列与数据路径和任务相关的）：

- **基础信息**
  - `id`: Block 唯一 ID（例如 `0ebaeff6-bb55-4ab7-9a5c-47eefbdcb674`）
  - `name`: Block 名称（前端显示，如 “City1”）
  - `status`: 空三任务状态（`created/running/completed/failed/cancelled`）
  - `algorithm`: 使用的算法（`colmap` / `glomap`）
  - `matching_method`: 匹配方法（`sequential/exhaustive/...`）

- **输入路径**
  - `image_path`: 用户在前端选择的**原始图像目录**（绝对路径）。
  - `source_image_path`: 当前实现中与 `image_path` 相同，用于未来兼容。
  - `working_image_path`: 后端为该 Block 构建的**工作图像目录**（位于 `data/blocks/{id}/images`）。

- **输出路径**
  - `output_path`: SfM / GLOMAP 输出目录（位于 `data/outputs/{id}`）。

- **空三任务状态 / 统计**
  - `current_stage`: 当前粗粒度阶段（`feature_extraction/matching/mapping/completed`）。
  - `current_detail`: 日志解析出来的更细粒度阶段。
  - `progress`: 0–100，TaskRunner 维护。
  - `error_message`: 失败时的最后错误信息。
  - `statistics`: JSON，记录各阶段耗时与参数（`stage_times/total_time/algorithm_params`）。

- **OpenMVS 重建字段**
  - `recon_status`: `NOT_STARTED/RUNNING/COMPLETED/FAILED/CANCELLED`
  - `recon_progress`: 重建总体进度 0–100。
  - `recon_current_stage`: `undistort/convert/densify/mesh/refine/texture/completed`。
  - `recon_output_path`: 重建输出根目录（`<output_path>/recon`）。
  - `recon_error_message`: 重建失败时的错误摘要（包含最后若干行日志）。
  - `recon_statistics`: JSON，记录重建阶段耗时 / 参数等。

所有前端展示、接口查询，最终都会落到这一行记录上。

---

## 3. Block 工作目录：`data/blocks/{block_id}`

### 3.1 创建与用途

- 创建路径：`WorkspaceService.get_block_root(block_id)`
  - 定义位置：`backend/app/services/workspace_service.py`
  - 逻辑：
    ```python
    def get_block_root(block_id: str) -> str:
        return f"/root/work/aerotri-web/data/blocks/{block_id}"
    ```

- 工作图像目录：
  ```python
  def get_working_images_dir(block_id: str) -> str:
      return os.path.join(get_block_root(block_id), "images")
  ```

- 在 **创建 Block** 时（`backend/app/api/blocks.py`）：
  - 校验 `image_path` 存在；
  - 调用 `WorkspaceService.populate_working_dir(block_id, image_path)`：
    - 在 `data/blocks/{block_id}/images` 下遍历源目录中的图像文件：
      - 优先创建 **硬链接**（`os.link`），若失败则退回到 **符号链接**（`os.symlink`）。
    - 返回该工作目录路径，写入 `Block.working_image_path`。

### 3.2 目录结构示意（完整展开）

```text
data/blocks/
├── {block_id_1}/
│   └── images/                 # 该 Block 的“安全工作图像目录”
│       ├── DJI_2025..._0001_V.JPG  # 硬链接/软链接，文件名与原始目录一致
│       ├── DJI_2025..._0002_V.JPG
│       └── ...
├── {block_id_2}/
│   └── images/
│       └── ...
└── ...
```

目前 `data/blocks/{id}` 下只使用了 `images/` 子目录，后续如需为每个 Block 存放额外配置或中间缓存，也应优先放在该 Block 目录下（不影响原始 `image_path`）。

用途小结：

- 前端所有图像预览 / 缩略图 / 删除操作都只作用于 `working_image_path`，避免误删原始数据；
- 空三 / 重建阶段读取图像时也优先使用 `working_image_path`（如果存在），保证路径稳定。

---

## 4. 空三输出目录：`data/outputs/{block_id}`

### 4.1 目录创建 & 使用（TaskRunner）

- 定义位置：`backend/app/services/task_runner.py`

- 当用户点击“运行空三”（`POST /api/blocks/{id}/run`）时：

```python
output_path = f"/root/work/aerotri-web/data/outputs/{block.id}"
os.makedirs(output_path, exist_ok=True)
block.output_path = output_path
```

随后在 `_run_task` 中，使用：

- `database_path = os.path.join(block.output_path, "database.db")`
- `sparse_path   = os.path.join(block.output_path, "sparse")`

来组织 COLMAP/GLOMAP 的输出。

### 4.2 SfM 输出结构（database.db / sparse/0 / run.log）

典型结构如下：

```text
data/outputs/{block_id}
├── database.db          # COLMAP 数据库（特征 & 匹配关系）
├── sparse/
│   └── 0/
│       ├── cameras.bin
│       ├── images.bin
│       ├── points3D.bin
│       └── ...
└── run.log              # TaskRunner 写入的空三任务日志（feature/matching/mapping）
```

说明：

- `database.db`：COLMAP 的 SQLite 数据库，包含：
  - 图像表（图像文件名与相机 ID 映射）；
  - 特征点、描述子、匹配对等。
- `sparse/0/`：SfM 的稀疏重建结果：
  - `cameras.bin`：相机内参（焦距、主点、畸变系数等）。
  - `images.bin`：每张图像的姿态（四元数 + 平移）、对应相机 ID，以及关联的 2D-3D 观测。
  - `points3D.bin`：三维点坐标、颜色、重投影误差和观测列表。
- `run.log`：TaskRunner 在运行 COLMAP/GLOMAP 各阶段时，将 stdout/stderr 追加到该文件，方便排错和恢复。

ASCII 简图（Block 粗略数据流）：

```text
[原始图像目录 image_path]
           │
           ▼
  WorkspaceService.populate_working_dir
           │
           ▼
data/blocks/{id}/images  (working_image_path)
           │
           ├──(TaskRunner: feature_extraction/matching/mapping 读取图像)
           │
           ▼
data/outputs/{id}/database.db + sparse/0/*
```

---

## 5. 缩略图缓存：`data/thumbnails`

- 定义位置：`backend/app/services/image_service.py`
- 常量：`THUMBNAIL_CACHE_DIR = "/root/work/aerotri-web/data/thumbnails"`

缩略图生成流程：

1. 前端请求：`GET /api/blocks/{block_id}/images/{image_name}/thumbnail?size=200`
2. 后端根据 `Block.working_image_path`（若为空则回退 `image_path`）找到原始图片。
3. `ImageService.get_thumbnail(image_path, size)`：
   - 生成 cache key：`md5(f"{image_path}_{size}")`。
   - 若缓存文件存在且比原图新，直接返回。
   - 否则用 PIL 生成缩略图写入 `data/thumbnails/{hash}.jpg`。

此目录与 Block ID 没有直接绑定关系，是“路径 + 尺寸”的纯缓存。

---

## 6. OpenMVS 重建输出目录：`<output_path>/recon`

### 6.1 目录结构（OpenMVSRunner）

位置：`backend/app/services/openmvs_runner.py`

在 `start_reconstruction` 中：

```python
recon_dir   = os.path.join(block.output_path, "recon")
dense_dir   = os.path.join(recon_dir, "dense")
mesh_dir    = os.path.join(recon_dir, "mesh")
refine_dir  = os.path.join(recon_dir, "refine")
texture_dir = os.path.join(recon_dir, "texture")
```

典型完整结构：

```text
data/outputs/{block_id}
├── database.db
├── sparse/
│   └── 0/
│       ├── cameras.bin
│       ├── images.bin
│       ├── points3D.bin
│       └── ...
└── recon/
    ├── run_recon.log           # 本次重建的全量日志
    ├── dense/
    │   ├── images/             # COLMAP 去畸变后的图像
    │   ├── sparse/0/*          # 去畸变后对应的 COLMAP sparse
    │   ├── scene.mvs           # InterfaceCOLMAP 生成的 MVS 场景
    │   ├── scene_dense.mvs     # DensifyPointCloud 输出
    │   └── scene_dense.ply     # 稠密点云（可用于预览）
    ├── mesh/
    │   ├── scene_dense.mvs     # 从 dense 目录复制/重用
    │   └── scene_dense_mesh.ply
    ├── refine/
    │   ├── scene_dense.mvs
    │   └── scene_dense_refine.ply
    └── texture/
        ├── scene_dense.mvs
        ├── scene_dense_refine.ply
        ├── scene_dense_refine_texture.obj
        ├── scene_dense_refine_texture.mtl
        └── scene_dense_refine_texture_*.png
```

注意：具体文件名由 OpenMVS 决定，上面是典型命名；当前实现里我们主要依赖 `.mvs/.ply/.obj` 文件存在性及其所在阶段目录来区分。

### 6.2 MVS 管线的关键文件说明

- **`scene.mvs`**（dense/）
  - 由 `InterfaceCOLMAP` 把 COLMAP 的 sparse（相机 + 稀疏点）转换为 OpenMVS 场景。
  - 包含：相机、图像路径、稀疏点等。

- **`scene_dense.mvs` & `scene_dense.ply`**（dense/）
  - 由 `DensifyPointCloud scene.mvs` 输出。
  - `.mvs` 里包含稠密点云；`.ply` 是可视化用的点云文件。

- **`scene_dense_mesh.ply`**（mesh/）
  - 由 `ReconstructMesh scene_dense.mvs` 输出的三角网格。

- **`scene_dense_refine.ply`**（refine/）
  - 由 `RefineMesh` 对网格做几何细化之后的网格。

- **`scene_dense_refine_texture.obj + .mtl + .png`**（texture/）
  - 由 `TextureMesh` 输出的带纹理网格，前端 Three.js 主要加载 `.obj + .mtl + 纹理图`。

---

## 7. OpenMVSRunner 的路径对照与错误分析

### 7.1 OpenMVSRunner 输入输出路径一览

以一个完成 SfM 的 Block 为例：

```text
Block.image_path         # 原始图像目录（用户选择）
Block.working_image_path # data/blocks/{id}/images （如有）
Block.output_path        # data/outputs/{id}
```

在 `_run_pipeline` 中关键路径使用：

```python
sparse_dir = os.path.join(block.output_path or "", "sparse", "0")
images_dir = block.working_image_path or block.image_path
log_path   = os.path.join(recon_dir, "run_recon.log")
```

然后各阶段执行：

1. **去畸变：COLMAP image_undistorter**

```python
_run_undistort(
    images_dir=images_dir,
    sparse_dir=sparse_dir,
    dense_dir=dense_dir,
)

cmd = [
  COLMAP_PATH, "image_undistorter",
  "--image_path", images_dir,
  "--input_path", sparse_dir,
  "--output_path", dense_dir,
  "--output_type", "COLMAP",
  "--max_image_size", "3200",
]
```

- 输入：
  - `images_dir`：推荐使用 `Block.working_image_path`（`data/blocks/{id}/images`）。
  - `sparse_dir`：`data/outputs/{id}/sparse/0`。
- 输出：
  - `dense_dir/images/`：去畸变后的图像。
  - `dense_dir/sparse/0/`：对应的 sparse。

2. **COLMAP → MVS：InterfaceCOLMAP**

```python
dense_dir_abs = str(Path(dense_dir).resolve())
scene_path    = os.path.join(dense_dir_abs, "scene.mvs")

cmd = [
  OPENMVS_INTERFACE_COLMAP,
  "-i", dense_dir_abs,
  "-o", scene_path,
  "--image-folder", os.path.join(dense_dir_abs, "images"),
  "-v", "2",
]
```

- 输入：
  - `dense_dir_abs/sparse/0` 和 `dense_dir_abs/images`。
- 输出：
  - `dense_dir_abs/scene.mvs`：其中带有 **OpenMVS 需要的图像路径信息**（应指向 `dense_dir_abs/images/...`）。

3. **DensifyPointCloud**

```python
scene_path = os.path.join(dense_dir, "scene.mvs")

cmd = [
  OPENMVS_DENSIFY,
  scene_path,
  "--cuda-device", str(gpu_index),
  "--resolution-level", "1",
  "--number-views", "5",
  "--number-views-fuse", "3",
  "--estimate-colors", "1",
  "--estimate-normals", "1",
  "-v", "2",
]
```

- 输入：
  - `dense_dir/scene.mvs`，其中记录了图像路径（应为 `dense_dir/images/...`）。
- 输出：
  - `dense_dir/scene_dense.mvs`
  - `dense_dir/scene_dense.ply`

4. **ReconstructMesh / RefineMesh / TextureMesh**

随后三个阶段均以 `scene_dense.mvs` 和前一阶段生成的 `.ply` 为输入，输出位于 `mesh_dir/`、`refine_dir/`、`texture_dir/`，路径与上面 6.1 中的结构对齐。

### 7.2 报错路径与设计不一致的地方

你在重建 City1 时，OpenMVS 日志报错：

```text
Reconstruction stage 'densify' failed with exit code 1
error: failed reloading image '/root/work/aerotri-web/backend/images/DJI_20250805150529_0597_V.JPG'
...
error: preparing images for dense reconstruction failed (errors loading images)
```

对照上面的设计，**DensifyPointCloud 理论上应该只访问 `dense_dir/images/` 下的图像**，而不是 `/root/work/aerotri-web/backend/images/...`。  
出现这种情况，通常意味着：

1. 当前使用的 `scene.mvs` 是 **旧版本**，其中的图像路径仍然是早期 Pipeline（或独立脚本）生成的，例如：
   - 当时的 `InterfaceCOLMAP` 使用 `--image-folder /root/work/aerotri-web/backend/images`；
   - 或者最初 SfM 的 COLMAP 数据就是基于 `/root/work/aerotri-web/backend/images`。
2. 新的 `OpenMVSRunner` 虽然调用了 InterfaceCOLMAP，但可能因为：
   - `dense_dir` 下已存在旧的 `scene.mvs`，且 InterfaceCOLMAP 因前置错误未成功覆盖；
   - DensifyPointCloud 仍然读到旧文件，于是里面的路径还是 `/root/work/aerotri-web/backend/images/...`。

再结合你目前真实的图像路径（已经在 `data/blocks/{id}/images` 下），就会出现：

- **scene.mvs 内部路径指向老目录 `/root/work/aerotri-web/backend/images`；**
- 该目录中不再有完整的 DJI 图像，OpenMVS 在 densify 时“reload image”失败，报 exit code 1。

### 7.3 如何修正 / 避免这个问题

从“设计”角度，当前 `OpenMVSRunner` 的路径使用是合理的（全部围绕 `output_path` / `recon` / `dense/images`），问题主要出在 **历史数据的 scene.mvs 指向旧路径**。解决有两个层面：

#### 方案 A：为老 Block 补一份兼容目录（快速修复）

适用于你已经有一个稳定的 SfM 结果，但最初是基于 `/root/work/aerotri-web/backend/images` 做的：

1. 找到 City1 对应 Block 的真实图像（现在在 `data/blocks/{city1_id}/images`）。
2. 在 `/root/work/aerotri-web/backend/images` 下，补齐这些文件：

```bash
mkdir -p /root/work/aerotri-web/backend/images
cp /root/work/aerotri-web/data/blocks/{city1_id}/images/*.JPG \
   /root/work/aerotri-web/backend/images/
```

这样即使旧的 `scene.mvs` 仍然指向 `/root/work/aerotri-web/backend/images`，DensifyPointCloud 也能顺利 reload 到图片，重建可以继续进行。

#### 方案 B：为老 Block 重新生成 scene.mvs（推荐但成本略高）

更干净的做法是：

1. 删除该 Block `recon/` 目录下旧的 MVS 文件：

```bash
rm -rf /root/work/aerotri-web/data/outputs/{city1_id}/recon
```

2. 确认 `Block.working_image_path` 指向 `data/blocks/{city1_id}/images`，且该目录下图像完整。
3. 再次在前端点击“开始重建”，让新的 `OpenMVSRunner` 根据当前的：
   - `images_dir = block.working_image_path`
   - `dense_dir = output_path/recon/dense`
   - `--image-folder = dense_dir/images`
   
重新生成一份 **内部路径指向 `recon/dense/images` 的 scene.mvs**，此后 densify 将不再访问 `/root/work/aerotri-web/backend/images`。

> 注意：如果 City1 的稀疏结果（`sparse/0`）本身就是基于一个已经不存在的图像目录构建的，从几何上重新跑 SfM 才是完全稳妥的方案。但在大多数情况下，只要 `sparse/0` 保持可读，重新生成 MVS 并不会出问题。

#### 方案 C：后续代码层面的保护性改进（可选）

为了进一步降低“旧 scene.mvs 复用”的风险，可以在 `OpenMVSRunner._run_pipeline` 中增加一些安全措施，例如：

- 在运行 InterfaceCOLMAP 前，如果 `dense_dir/scene.mvs` 已存在，记录时间戳或直接先删掉旧文件；
- 在 densify 前，解析刚生成的 `scene.mvs`，检查其中的图像路径是否落在预期的 `dense_dir/images` 下，否则直接报错并提示用户需要重新跑 SfM 或修正路径。

这些属于“健壮性提升”，不影响当前架构，只是让错误更早、更可解释。

---

## 8. 小结

- **`aerotri.db`** 通过 `blocks` 表把前端看到的 Block 与磁盘上的 `data/blocks/{id}` / `data/outputs/{id}` 关联起来。
- **`data/blocks/{id}/images`** 是 per-block 的安全工作图像目录，前端预览和一些图像操作都会围绕它。
- **`data/outputs/{id}`** 包含 SfM 的 `database.db` 和 `sparse/0`，以及在其下的 `recon/` 目录中存放的 OpenMVS 稠密/网格/纹理输出。
- `OpenMVSRunner` 按设计应只依赖：
  - `Block.output_path` 下的 `sparse/0`；
  - `Block.working_image_path`（或 `image_path`）；
  - 并在 `<output_path>/recon` 下构建完整的 MVS 管线。
- 当前你遇到的 `densify` 阶段错误，是因为使用到的 `scene.mvs` 中图像路径仍指向旧目录 `/root/work/aerotri-web/backend/images`，而该目录下图像不完整。  
  通过补齐旧目录或重新生成 scene.mvs / 重新跑 SfM，可以与本文所述的数据布局保持一致，避免该错误。 


