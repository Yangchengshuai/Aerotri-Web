## 文档信息

- **文档名称**: AeroTri Web 重建模块（OpenMVS）PRD
- **版本**: v0.1
- **作者**: （待填）
- **相关项目**: AeroTri Web（基于 COLMAP/GLOMAP 的空三工具）
- **最后更新**: （待填）

## 1. 背景与目标

### 1.1 背景

当前 AeroTri Web 已支持基于 COLMAP/GLOMAP 的空中三角测量（SfM）流程，输出稀疏点云和相机位姿，并在 Web 前端提供 3D 可视化与参数调试能力。  
但在实际航测/测绘/场景重建需求中，**用户强烈需要后续的稠密重建与高质量纹理网格模型**，以用于：

- 交付可视化模型给下游客户（设计、运维、展示等）
- 在不同参数配置下对比重建质量（噪声、细节、纹理效果）
- 对特定场景（如 DJI 航拍）的 Pipeline 进行性能和质量调优

OpenMVS 已在当前服务器环境中独立验证了从 COLMAP sparse 结果到纹理模型的完整流程（参考 `data/test_openmvs_pipeline.sh`）。  
本 PRD 旨在将该能力**产品化集成到 AeroTri Web**，形成可视化、可监控、可调参与可复用的重建模块。

### 1.2 目标

- 在保持现有 SfM 能力的前提下，**新增一个“重建模块（Reconstruction）”**，作为 Block 的后处理流水线：
  - 稠密点云（DensifyPointCloud）
  - Mesh 重建（ReconstructMesh）
  - Mesh 优化（RefineMesh）
  - 纹理贴图（TextureMesh）
- 支持在 Web 前端一键触发重建任务，并实时查看进度与日志。
- 支持对 **各阶段中间结果文件** 进行：
  - 文件信息查看（阶段、大小、生成时间）
  - 下载
  - 基础 3D 预览（Three.js）

### 1.3 非目标

- 首版不做复杂的 3D 高级分析能力，例如：
  - 多版本模型叠加对比
  - 着色模式高级切换（法线/深度等）
  - 剖切、量测等工程功能
- 首版不支持集群/多机分布式重建，仅支持与当前后端在同一台服务器上的本地 OpenMVS 调用。

## 2. 角色视角

### 2.1 资深算法工程师

- 希望：
  - 能方便地从同一套 SfM 结果出发，使用不同 OpenMVS 参数进行多次重建。
  - 查看每次重建的中间输出（dense / mesh / refine / texture）质量。
  - 在日志中快速定位重建失败原因（CUDA、内存、参数不合适等）。
- 关注点：
  - 参数可配置性（至少支持 decimate、thickness-factor、resolution-level 等关键参数的预设）。
  - 输出命名规范、文件路径稳定、便于脚本化处理。

### 2.2 高级软件架构师 / 后端工程师

- 希望：
  - 重建任务与现有 SfM 任务解耦（单独的 Runner / 状态机）。
  - 所有 CLI 调用、日志、错误信息都可以被定位和追踪。
  - 任务恢复、失败标记有清晰语义，避免“僵尸任务”。
- 关注点：
  - Block 模型如何扩展以支持重建状态与统计信息。
  - 与现有 `TaskRunner`、WebSocket 通知机制的兼容性。
  - OpenMVS 与 COLMAP 的路径、GPU 资源占用管理。

### 2.3 高级产品经理

- 希望：
  - 用户在 Block 详情页中能自然地从“空三结果”走向“重建结果”，流程清晰。
  - 所有关键功能有可观测性（状态、进度、耗时、错误）和可控性（开始/查看/下载）。
- 关注点：
  - 功能范围清晰，版本切分合理（先支持一键重建 + 基础预览，后续再扩展高级特性）。
  - 与现有“Block 对比”、“统计分析”等功能的衔接。

### 2.4 高级前端 UI / 交互专家

- 希望：
  - 界面清晰表达“SfM（稀疏）”与“Reconstruction（稠密+Mesh+纹理）”两个层级。
  - 重建模块的 UI 简洁且易扩展，将来可增加更多高级参数与可视化能力。
- 关注点：
  - 3D 预览组件的复用性和性能（大模型加载时的反馈与保护）。
  - 不影响现有 Block 列表与详情页的使用体验。

## 3. 用户故事

### 3.1 基础用户故事

1. **一键重建**
   - 作为：空三用户
   - 我希望：在空三（SfM）任务完成后，在 Block 详情页点击“开始重建”，系统自动完成从稠密点云到纹理网格的完整流程。
   - 以便：我能快速得到可视化效果较好的 3D 模型用于演示和对外交付。

2. **查看中间结果**
   - 作为：算法/调参工程师
   - 我希望：能够在 Web 上看到每个重建阶段的输出文件信息，并预览稠密点云、Mesh 和纹理模型的 3D 效果。
   - 以便：我能判断是哪个阶段的参数导致整体效果不好，快速定位问题。

3. **查看日志与失败原因**
   - 作为：工程师
   - 我希望：在重建失败时能够查看最后若干行日志和失败阶段，知道是 CUDA 内存、参数不当还是输入数据问题。
   - 以便：我调整参数或数据后能快速重试。

4. **多次重建（预留能力）**
   - 作为：算法工程师
   - 我希望：未来能基于同一个 Block 做多次不同配置的重建，并至少保留“最后一次”的结果（首版可以不做完整多版本管理，但模型要不阻碍后续扩展）。
   - 以便：可以系统性对比不同参数配置对重建质量的影响。

## 4. 功能需求

### 4.1 后端功能

1. **重建任务触发**
   - 从现有 Block（已完成 SfM）出发，触发一条重建流水线：
     - `COLMAP image_undistorter`
     - `InterfaceCOLMAP`
     - `DensifyPointCloud`
     - `ReconstructMesh`
     - `RefineMesh`
     - `TextureMesh`
   - 使用已有 Block 的 `image_path` / `output_path` / `gpu_index` 等信息。
   - 参数配置：
     - 首版暴露一个 `quality_preset`：`fast` / `balanced` / `high`（内部映射到 decimate/resolution-level 等具体值）。
   - CLI 路径通过环境变量或配置提供（OpenMVS 可执行路径）。

2. **重建状态与进度管理**
   - 为每个 Block 增加独立的重建状态机，至少包含：
     - `NOT_STARTED` / `RUNNING` / `COMPLETED` / `FAILED` / `CANCELLED`
   - 记录当前阶段：
     - `undistort` / `convert` / `densify` / `mesh` / `refine` / `texture`
   - 记录阶段耗时和总耗时，存入 `recon_statistics` 字段。

3. **中间结果输出规范**
   - 在 Block 的输出目录下创建统一的重建目录，例如：
     - `<block.output_path>/recon/`
       - `dense/`：`{scene}_dense.ply`, `{scene}_dense.mvs`
       - `mesh/`：`{scene}_dense_mesh.ply`
       - `refine/`：`{scene}_dense_refine.ply`
       - `texture/`：`{scene}_dense_refine_texture.obj` + `mtl/png`
   - 每个阶段结束时，记录该阶段产生的文件信息：
     - 文件名、大小、生成时间、阶段类型。

4. **日志记录与错误处理**
   - 每次重建任务生成独立日志文件，例如：
     - `<block.output_path>/recon/run_recon.log`
   - 捕获子进程退出码和最后若干行日志，生成用户可读的错误描述（结合现有 `ProcessCrashError` 经验）。

### 4.2 前端功能

1. **Block 详情页中新增“重建”区域**
   - 显示当前 Block 的重建状态：
     - 未开始 / 运行中 / 已完成 / 失败。
   - 提供主操作按钮：
     - `开始重建`：触发 POST 接口。
   - 禁用重复触发逻辑（重建运行中时按钮不可用）。

2. **阶段卡片与文件信息**
   - 对四个主要阶段展示卡片：
     - 稠密点云 / 网格 / 优化网格 / 纹理模型
   - 每张卡片展示：
     - 状态图标：未生成 / 处理中 / 已生成
     - 文件大小、生成时间（从后端 file list API 获取）
     - 行为按钮：
       - `预览`：打开 Three.js 预览窗口，加载对应资源。
       - `下载`：下载原始 `.ply` / `.obj` / 贴图等文件。

3. **基础 3D 预览组件**
   - 使用 Three.js 实现：
     - 轨道控制（旋转/缩放/平移）
     - 自动适配视角（fit to model）
   - 支持资源类型：
     - Point Cloud：读取 `.ply` 并以点模式渲染。
     - Mesh：读取 `.ply` 并以三角面渲染，简单光照。
     - Texture Model：读取 `.obj` + 贴图，渲染带纹理的网格。
   - 性能保护：
     - 加载前显示文件大小和“加载中”提示。
     - 文件超过一定大小（例如 > 200MB）时提示用户可能较慢，由用户确认后再加载。

## 5. API 需求

### 5.1 REST API

1. **触发重建**

- `POST /api/blocks/{id}/reconstruct`
- 请求体（示例）：

```json
{
  "quality_preset": "balanced"
}
```

- 行为：
  - 校验 Block 是否存在且 SfM 已完成。
  - 若当前有重建在 RUNNING，则返回错误或忽略重复启动（具体策略在实现文档中细化）。
  - 异步启动重建任务，立即返回接受状态。

- 响应示例：

```json
{
  "block_id": "xxx",
  "recon_status": "RUNNING"
}
```

2. **查询重建状态**

- `GET /api/blocks/{id}/reconstruction/status`
- 响应示例：

```json
{
  "block_id": "xxx",
  "recon_status": "RUNNING",
  "recon_progress": 52.3,
  "recon_current_stage": "mesh",
  "recon_statistics": {
    "stage_times": {
      "undistort": 12.5,
      "densify": 120.3,
      "mesh": 45.1
    },
    "total_time": 200.1,
    "params": {
      "quality_preset": "balanced",
      "openmvs": {
        "decimate": 0.5,
        "resolution_level": 1,
        "thickness_factor": 1.5
      }
    }
  }
}
```

3. **列出重建输出文件**

- `GET /api/blocks/{id}/reconstruction/files`
- 响应示例：

```json
{
  "files": [
    {
      "stage": "dense",
      "type": "point_cloud",
      "name": "scene_dense.ply",
      "size_bytes": 123456789,
      "mtime": "2025-12-18T10:20:30Z",
      "preview_supported": true,
      "download_url": "/api/blocks/xxx/reconstruction/download?file=scene_dense.ply"
    },
    {
      "stage": "mesh",
      "type": "mesh",
      "name": "scene_dense_mesh.ply",
      "size_bytes": 234567890,
      "mtime": "2025-12-18T10:25:00Z",
      "preview_supported": true,
      "download_url": "..."
    }
  ]
}
```

4. **下载重建文件**

- `GET /api/blocks/{id}/reconstruction/download?file=...`
- 行为：
  - 校验文件是否在该 Block 的重建目录下。
  - 以文件流方式返回。

### 5.2 WebSocket（进度通知）

- 方案 A（首版）：复用现有 `/ws/blocks/{id}/progress`
  - 在消息体中增加重建相关字段或 stage 前缀：

```json
{
  "pipeline": "reconstruction",
  "stage": "mesh",
  "progress": 67.5,
  "message": "ReconstructMesh: 67%"
}
```

- 前端根据 `pipeline` 区分 SfM 与重建。

## 6. 前端交互稿描述

### 6.1 Block 详情页结构调整

```mermaid
flowchart TD
  blockDetail[BlockDetailView]
  sfmPanel[SfM 面板(现有)]
  reconPanel[Reconstruction 面板(新增)]
  previewModal[3D 预览弹窗]

  blockDetail --> sfmPanel
  blockDetail --> reconPanel
  reconPanel --> previewModal
```

### 6.2 Reconstruction 面板内容

- 顶部区域：
  - 标题：重建（Reconstruction）
  - 状态标签：未开始 / 运行中 / 已完成 / 失败
  - 主按钮：
    - 开始重建（未开始/失败时可点击）
    - 运行中...（禁用态）
- 中部区域：阶段卡片列表
  - 每卡片显示当前状态与文件摘要信息。
- 底部区域：
  - “最近日志”列表：显示 `run_recon.log` 的最后 20 行。

### 6.3 3D 预览交互

- 入口：点击任一阶段卡片上的预览按钮。
- 预览方式：弹出 Modal 或右侧 Drawer：
  - 标题：`[Block 名称] - [阶段名] 预览`
  - 内容：
    - 加载进度提示（包括文件大小）
    - Three.js Canvas
- 基础交互：
  - 鼠标左键拖拽旋转
  - 滚轮缩放
  - 右键拖拽平移
  - 双击重置视角（可选）

## 7. 非功能性需求

- 性能
  - 重建任务单次可能耗时数分钟到数十分钟，需要稳定的进度与日志输出。
  - 前端对大文件预览要有明确提示，避免误操作导致浏览器崩溃。
- 可靠性
  - 后端在重启后应能正确反映重建任务最终状态（至少标记为 FAILED），避免长期 RUNNING 状态。
- 可扩展性
  - 数据模型与 API 设计要为未来多次重建、参数模板、多 Block 对比保留空间。


