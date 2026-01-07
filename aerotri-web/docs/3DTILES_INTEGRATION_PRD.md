# AeroTri Web + 3D Tiles 倾斜模型显示：PRD

## 0. 文档信息

- **产品**：AeroTri Web（空三 + 倾斜建模）扩展：3D Tiles 倾斜模型 Web 端显示
- **目标版本**：V1（可用）
- **相关仓库**：
  - `work/aerotri-web`：现有 Block/任务/重建/Three.js 可视化
  - `obj2gltf`：OBJ → GLB 转换工具（已全局安装）
  - `3d-tiles-tools`：GLB → 3D Tiles 转换工具（已全局安装）
  - `CesiumJS`：3D Tiles 渲染引擎（前端集成）
- **本文输出**：
  - 以 4 个角色视角的讨论纪要（算法/后端/前端/产品）
  - 收敛后的 PRD：范围、流程、数据流、接口、验收、风险

---

## 1. 背景与机会

现有 AeroTri Web 已支持：

- Block 管理、图像工作目录、SfM（COLMAP/GLOMAP/InstantSfM）任务调度
- SfM 结果（相机 + 稀疏点）Three.js 可视化
- OpenMVS 重建（undistort → densify → mesh → refine → texture）生成带纹理的 .obj/.mtl 文件

新增 3D Tiles 的价值：

- **地理空间集成**：3D Tiles 是 CesiumJS 原生格式，支持地理坐标系统、地形叠加、多数据源融合
- **大规模渲染**：相比 Three.js 直接加载 .obj，3D Tiles 支持 LOD、空间索引、流式加载，适合大规模倾斜模型
- **标准化格式**：3D Tiles 是 OGC 标准，便于与其他地理信息系统（GIS）集成
- **Web 端性能**：CesiumJS 针对 3D Tiles 做了大量优化，渲染性能优于通用 3D 引擎

---

## 2. 目标（Goals）与非目标（Non-goals）

### 2.1 Goals（V1）

- **G1：在 OpenMVS 纹理阶段完成后，自动/手动触发 3D Tiles 转换**（.obj/.mtl → .glb → 3D Tiles）
- **G2：转换过程可观测**：状态/阶段/进度/日志 tail/取消
- **G3：产物可管理**：列出 tileset.json 和 b3dm 文件，支持下载
- **G4：Web 端可加载查看 3D Tiles 模型**：在 Block 详情页内嵌 CesiumJS Viewer 显示倾斜模型
- **G5：与现有可视化并存**：Three.js 可视化（相机/点云）与 CesiumJS 可视化（倾斜模型）可切换或并列显示

### 2.2 Non-goals（暂不做）

- N1：分层瓦片（LOD）生成（V1 先做单个 b3dm，适合中小型模型）
- N2：地理坐标转换（V1 先使用模型本地坐标系，后续可扩展 WGS84/UTM）
- N3：多 Block 倾斜模型合并（先做单 Block 闭环）
- N4：3D Tiles 编辑/优化工具（先做基础转换与显示）

---

## 3. 角色模拟讨论纪要（四视角）

### 3.1 重建算法专家视角（算法正确性/格式兼容性）

- **输入契约**：3D Tiles 转换必须基于 OpenMVS 纹理阶段的输出：
  - 主文件：`scene_dense_texture.obj` 或 `scene_dense_mesh_refine_texture.obj`
  - 材质文件：对应的 `.mtl` 文件
  - 纹理图片：`.mtl` 中引用的 `.jpg/.png` 纹理文件（需在同一目录）
- **转换流程**：
  1. **OBJ → GLB**：使用 `obj2gltf` 工具
     - 输入：`.obj` + `.mtl` + 纹理图片目录
     - 输出：`.glb` 文件（二进制 glTF，包含几何和纹理）
     - 参数：`--binary`（输出 GLB）、`--checkTransparency`（检查透明度）
  2. **GLB → 3D Tiles**：使用 `3d-tiles-tools` 工具
     - 输入：`.glb` 文件
     - 输出：`tileset.json` + `*.b3dm` 文件（或单个 b3dm）
     - 命令：`3d-tiles-tools createTilesetJson` 或 `3d-tiles-tools glbToB3dm`
- **坐标系统**：
  - V1：保持模型本地坐标系（OpenMVS 输出的坐标系）
  - 后续：可扩展读取 COLMAP 相机 GPS 信息，转换为 WGS84/UTM
- **质量评估**：
  - 最小：转换成功、纹理正确、在 CesiumJS 中可加载显示
  - 可选：模型边界框（bounding box）计算、纹理压缩优化
- **风险点**：
  - `.mtl` 文件中的纹理路径可能是相对路径，需要确保 `obj2gltf` 能正确找到纹理
  - 大型模型（>100MB）转换为单个 b3dm 可能导致文件过大，影响加载性能

### 3.2 高级后端工程师视角（可运维/可恢复/资源管理）

- **复用现有模式**：参考 OpenMVS 重建的 `recon_*` 字段与 `/reconstruction/*` API，新增一套 `tiles_*` 字段与 `/tiles/*` API。
- **任务生命周期**：NOT_STARTED/RUNNING/COMPLETED/FAILED/CANCELLED + stage/progress + log tail + cancel + orphan recovery。
- **转换流程阶段**：
  - `obj_to_glb`：OBJ → GLB 转换
  - `glb_to_tiles`：GLB → 3D Tiles 转换
  - `completed`：转换完成
- **文件服务**：复用 reconstruction 的"列出文件/下载文件"方式，对 `outputs/{id}/tiles` 做安全的相对路径下载。
- **工具依赖**：
  - `obj2gltf`：已全局安装，通过 `obj2gltf` 命令调用
  - `3d-tiles-tools`：已全局安装，通过 `3d-tiles-tools` 命令调用
  - 环境变量配置（可选）：`OBJ2GLTF_PATH`、`3DTILES_TOOLS_PATH`
- **输出目录结构**：
  ```
  outputs/{block_id}/tiles/
  ├── run_tiles.log          # 转换日志
  ├── model.glb              # 中间产物（可选保留）
  ├── tileset.json           # 3D Tiles 根文件
  └── *.b3dm                 # 瓦片文件（V1 单个文件）
  ```

### 3.3 高级前端工程师视角（集成成本/体验/兼容性）

- **UI 入口**：Block 详情页的"重建"标签页中，在纹理阶段完成后显示"转换为 3D Tiles"按钮，或新增"3D Tiles"标签页：
  - 转换配置（可选参数）+ Start/Cancel
  - 状态展示：stage/progress + log tail + 文件卡片（下载/预览）
- **Viewer 方案**：
  - **内嵌 CesiumJS Viewer**：在 Block 详情页内嵌显示（与 Three.js 可视化并列或切换）
  - 使用 CesiumJS CDN 或本地构建版本
  - 输入：`tileset.json` 的 URL（后端提供）
  - 交互：鼠标旋转/缩放/平移、重置视角、显示/隐藏 UI 控件
- **兼容性策略**：
  - CesiumJS 需要 WebGL 支持（现代浏览器基本都支持）
  - 不支持 WebGL 时：提示"浏览器不支持 WebGL，建议使用 Chrome/Edge/Firefox 最新版本"
- **性能策略**：
  - V1 单个 b3dm 文件，适合中小型模型（<200MB）
  - 大文件加载时显示进度条
  - 加载失败时给出明确错误提示

### 3.4 产品经理视角（用户价值/范围控制/验收）

- **用户故事**：
  - 作为测绘/重建用户：OpenMVS 纹理完成后想一键转换为 3D Tiles 并在浏览器里查看倾斜模型
  - 作为算法调参者：想对比不同重建参数生成的倾斜模型效果
- **MVP 定义（V1）**：只做"能跑起来 + 能看见 + 可下载 + 可取消 + 可恢复"
- **清晰边界**：
  - 不做在线编辑/拼接/大规模批量转换调度
  - 先把单 Block 的闭环做稳
  - 不做地理坐标转换（V1 先使用本地坐标系）

---

## 4. 产品方案（收敛版）

### 4.1 总体流程

1. 用户创建 Block → 上传/选择图像 → 运行空三（SfM）
2. SfM COMPLETED 后，用户进入 Block 详情页"重建"标签页
3. 启动 OpenMVS 重建 → 等待纹理阶段完成
4. 纹理阶段完成后，显示"转换为 3D Tiles"按钮
5. 点击按钮 → 后端启动转换任务（.obj → .glb → 3D Tiles）
6. 前端轮询/WS 获取进度 + log tail
7. 转换产物生成 → 文件列表中出现 `tileset.json` → 点击"预览"在 CesiumJS Viewer 中打开

### 4.2 目录与产物规范

在 `data/outputs/{block_id}/tiles/` 下：

- `run_tiles.log`：转换日志（stdout/stderr 持久化）
- `model.glb`（可选）：中间产物 GLB 文件
- `tileset.json`：3D Tiles 根文件（必需）
- `*.b3dm`：瓦片文件（V1 单个文件，后续可扩展为多个）

### 4.3 后端能力需求（V1）

- **转换启动**：`POST /api/blocks/{id}/tiles/convert`
  - 入参：可选转换参数（如 `keep_glb`、`optimize`）
  - 前置校验：
    - Block 重建状态必须 COMPLETED 或纹理阶段已完成
    - `recon_output_path/texture/` 目录存在
    - `scene_dense_texture.obj` 或 `scene_dense_mesh_refine_texture.obj` 存在
- **状态查询**：`GET /api/blocks/{id}/tiles/status`
- **取消转换**：`POST /api/blocks/{id}/tiles/cancel`
- **日志 tail**：`GET /api/blocks/{id}/tiles/log_tail?lines=200`
- **文件列表**：`GET /api/blocks/{id}/tiles/files`
  - 返回：tileset.json、b3dm 文件、下载 URL
- **下载**：`GET /api/blocks/{id}/tiles/download?file=...`（相对路径防穿越）
- **Tileset URL**：`GET /api/blocks/{id}/tiles/tileset_url`
  - 返回 tileset.json 的完整 URL（用于 CesiumJS 加载）
- **恢复**：服务启动时扫描 DB 里 `tiles_status=RUNNING` 的任务并：
  - 若进程不存在且产物完整：标 COMPLETED
  - 否则标 FAILED 并给出 error_message

### 4.4 前端能力需求（V1）

- **Block 详情页新增 3D Tiles 转换面板**
  - 在"重建"标签页中，纹理阶段完成后显示转换入口
  - Start/Cancel、进度条、log tail、产物列表
- **CesiumJS Viewer**
  - 内嵌在 Block 详情页中（与 Three.js 可视化并列或切换）
  - 直接加载后端提供的 `tileset.json` URL
  - 基础交互：旋转/缩放/平移、重置视角

---

## 5. 数据模型（DB 扩展建议）

参照 `Block.recon_*`，新增：

- `tiles_status`：`NOT_STARTED/RUNNING/COMPLETED/FAILED/CANCELLED`
- `tiles_progress`：0–100
- `tiles_current_stage`：`obj_to_glb/glb_to_tiles/completed/...`
- `tiles_output_path`：`<recon_output_path>/tiles` 或 `<output_path>/tiles`
- `tiles_error_message`：失败摘要
- `tiles_statistics`：JSON（耗时、文件大小、瓦片数量等）

> 备注：保持命名与 OpenMVS 重建一致，有利于前端复用组件与后端复用恢复逻辑。

---

## 6. 验收标准（Acceptance Criteria）

### 6.1 功能验收（V1）

- **AC1**：OpenMVS 纹理阶段完成的 Block 能成功启动 3D Tiles 转换
- **AC2**：转换过程中 UI 可实时看到 stage/progress 与日志 tail
- **AC3**：可取消转换，状态变为 CANCELLED，日志保留
- **AC4**：转换完成后在文件列表中看到 `tileset.json` 和 `*.b3dm`，可下载
- **AC5**：在支持 WebGL 的浏览器上可预览 3D Tiles（旋转/缩放/平移正常）
- **AC6**：后端重启后，RUNNING 任务能被正确恢复为 COMPLETED/FAILED
- **AC7**：测试数据 `/root/work/aerotri-web/data/test_obj` 能成功转换并显示

### 6.2 性能/稳定性验收（V1）

- **AC8**：转换日志与状态写 DB，不依赖纯内存
- **AC9**：文件下载接口有路径穿越防护
- **AC10**：面对 100MB 级别 b3dm，前端给出清晰加载反馈与失败提示

### 6.3 增强验收（V1.5，暂不做）

- **AC11**：支持分层瓦片（LOD）生成，适合大型模型
- **AC12**：支持地理坐标转换（WGS84/UTM）

---

## 7. 风险与对策

- **R1：转换工具依赖复杂（obj2gltf/3d-tiles-tools）**
  - **对策**：后端仅做"调度"，工具通过全局安装的命令调用；提供健康检查（工具是否存在、版本）
- **R2：大文件 Web 加载慢/崩**
  - **对策**：V1 先支持单个 b3dm（适合中小型模型）；V1.5 增加分层瓦片与流式加载
- **R3：纹理路径解析失败**
  - **对策**：转换前校验 `.mtl` 文件中的纹理路径，确保纹理文件存在；使用 `obj2gltf` 的 `--secure` 选项限制文件访问
- **R4：CesiumJS 集成复杂度**
  - **对策**：优先使用 CDN 版本快速集成；后续可考虑本地构建以优化加载速度
- **R5：坐标系统不一致**
  - **对策**：V1 先使用模型本地坐标系；后续可扩展读取 COLMAP GPS 信息进行坐标转换

---

## 8. 里程碑建议（高层）

- **M1（V1）**：后端 3D Tiles 转换任务闭环 + 文件管理 API + 前端面板
- **M2（V1）**：集成 CesiumJS Viewer 加载 tileset.json
- **M3（V1.5，暂不做）**：分层瓦片与地理坐标转换

---

## 9. 技术选型

### 9.1 转换工具

- **obj2gltf**：OBJ → GLB 转换
  - 已全局安装：`obj2gltf`
  - 命令示例：`obj2gltf -i input.obj -o output.glb --binary`
- **3d-tiles-tools**：GLB → 3D Tiles 转换
  - 已全局安装：`3d-tiles-tools`
  - 命令示例：
    - 单个 b3dm：`3d-tiles-tools glbToB3dm -i input.glb -o output.b3dm`
    - 创建 tileset：`3d-tiles-tools createTilesetJson -i input.glb -o tileset.json`

### 9.2 前端渲染

- **CesiumJS**：3D Tiles 渲染引擎
  - CDN：`https://cesium.com/downloads/cesiumjs/releases/1.XX/Build/Cesium/Cesium.js`
  - 或本地构建：参考 CesiumJS 官方文档

### 9.3 测试数据

- 路径：`/root/work/aerotri-web/data/test_obj/`
- 文件：
  - `city1_scene_dense_texture.obj`（主模型文件）
  - `scene_dense_texture.mtl`（材质文件）
  - `scene_dense_texture_material_*.jpg`（纹理图片）

---

## 10. 数据流图

```
OpenMVS 纹理输出
  ├── scene_dense_texture.obj
  ├── scene_dense_texture.mtl
  └── scene_dense_texture_material_*.jpg
         │
         ▼
  [obj2gltf 转换]
         │
         ▼
      model.glb
         │
         ▼
  [3d-tiles-tools 转换]
         │
         ├── tileset.json
         └── *.b3dm
         │
         ▼
  [CesiumJS Viewer 加载]
         │
         ▼
    Web 端显示
```

---

## 11. API 设计（详细）

### 11.1 转换启动

```http
POST /api/blocks/{block_id}/tiles/convert
Content-Type: application/json

{
  "keep_glb": false,  // 是否保留中间产物 GLB
  "optimize": false    // 是否优化 GLB（可选）
}
```

### 11.2 状态查询

```http
GET /api/blocks/{block_id}/tiles/status

Response:
{
  "block_id": "...",
  "tiles_status": "COMPLETED",
  "tiles_progress": 100,
  "tiles_current_stage": "completed",
  "tiles_output_path": "/path/to/tiles",
  "tiles_error_message": null,
  "tiles_statistics": {
    "glb_size_bytes": 12345678,
    "b3dm_size_bytes": 12345678,
    "tileset_size_bytes": 1024,
    "conversion_time_seconds": 45.2
  }
}
```

### 11.3 文件列表

```http
GET /api/blocks/{block_id}/tiles/files

Response:
{
  "files": [
    {
      "name": "tileset.json",
      "type": "tileset",
      "size_bytes": 1024,
      "mtime": "2024-01-01T00:00:00",
      "preview_supported": true,
      "download_url": "/api/blocks/{id}/tiles/download?file=tileset.json"
    },
    {
      "name": "model.b3dm",
      "type": "tile",
      "size_bytes": 12345678,
      "mtime": "2024-01-01T00:00:00",
      "preview_supported": false,
      "download_url": "/api/blocks/{id}/tiles/download?file=model.b3dm"
    }
  ]
}
```

### 11.4 Tileset URL

```http
GET /api/blocks/{block_id}/tiles/tileset_url

Response:
{
  "tileset_url": "http://localhost:8000/api/blocks/{id}/tiles/download?file=tileset.json"
}
```

---

## 12. 前端组件设计

### 12.1 TilesConversionPanel.vue

- 位置：Block 详情页"重建"标签页中，纹理阶段完成后显示
- 功能：
  - 转换状态显示（NOT_STARTED/RUNNING/COMPLETED/FAILED）
  - 转换按钮（Start/Cancel）
  - 进度条 + 当前阶段
  - 日志 tail（可展开/收起）
  - 文件列表（tileset.json、b3dm 文件）
  - 预览按钮（打开 CesiumJS Viewer）

### 12.2 CesiumViewer.vue

- 位置：Block 详情页内嵌显示（与 Three.js 可视化并列或切换）
- 功能：
  - 初始化 CesiumJS Viewer
  - 加载 tileset.json
  - 交互控制（旋转/缩放/平移）
  - 重置视角按钮
  - 错误处理（WebGL 不支持、加载失败）

---

## 13. 测试计划

### 13.1 单元测试

- 后端：转换工具调用、文件路径解析、错误处理
- 前端：API 调用、状态管理、错误提示

### 13.2 集成测试

- 使用测试数据 `/root/work/aerotri-web/data/test_obj` 完整走通流程
- 验证：转换成功、文件生成、CesiumJS 加载显示

### 13.3 端到端测试

- 从 OpenMVS 纹理完成 → 转换 → CesiumJS 显示，完整用户流程

---

## 14. 后续扩展（V1.5+）

- **分层瓦片（LOD）**：使用 `3d-tiles-tools` 的 `createTilesetJson` 生成多级瓦片
- **地理坐标转换**：读取 COLMAP GPS 信息，转换为 WGS84/UTM
- **纹理优化**：压缩纹理、减少文件大小
- **批量转换**：支持多个 Block 批量转换为 3D Tiles
- **性能监控**：转换耗时、文件大小、加载性能统计

