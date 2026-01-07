# AeroTri Web + 3D Tiles 倾斜模型显示：开发计划

## 0. 总览

### 0.1 交付目标

- **V1（MVP）**：在 OpenMVS 纹理阶段完成后提供 3D Tiles 转换 + 产物管理 + Web 端 CesiumJS 预览
- **测试先行**：先用测试数据 `/root/work/aerotri-web/data/test_obj` 走通完整流程，再集成到后端

### 0.2 关键设计选择（与 PRD 对齐）

- **后端接入形态**：完全复用 OpenMVS 重建的"第二条 pipeline"范式：`TilesRunner + tiles_* 字段 + /tiles/* API + outputs/{id}/tiles`
- **转换实现**：调用全局安装的 `obj2gltf` 和 `3d-tiles-tools`（外部工具），由后端负责组织输入文件、启动/取消、落盘日志与状态
- **Web 端渲染**：集成 CesiumJS（CDN 或本地构建）加载 `tileset.json`，内嵌在 Block 详情页中

---

## 1. 里程碑与范围

### M0：测试数据验证（前置）

**产出**

- 使用测试数据手动验证转换流程
- 确认工具链可用性（obj2gltf、3d-tiles-tools）
- 生成测试用的 tileset.json 和 b3dm 文件
- 在独立 HTML 页面验证 CesiumJS 加载显示

### M1：后端 3D Tiles 转换闭环（V1）

**产出**

- 新增 DB 字段：`tiles_status/tiles_progress/tiles_current_stage/tiles_output_path/tiles_error_message/tiles_statistics`
- 新增 API：convert/status/cancel/files/download/log_tail/tileset_url
- 新增服务：`tiles_runner.py`（启动转换、进度解析、取消、恢复）
- 新增目录规范：`data/outputs/{block_id}/tiles/`（glb + tileset.json + b3dm + log）

### M2：前端 3D Tiles 面板 + CesiumJS Viewer（V1）

**产出**

- Block 详情页新增 3D Tiles 转换面板：配置、启动/取消、进度、日志、文件列表
- CesiumJS Viewer：可加载后端 `tileset.json` URL 并交互浏览

---

## 2. 详细任务拆解（可直接分配）

### 2.1 前置：测试数据验证（M0）

#### T0.1 手动转换测试

- **T0.1.1**：使用测试数据手动执行转换流程
  ```bash
  # OBJ → GLB
  cd /root/work/aerotri-web/data/test_obj
  obj2gltf -i city1_scene_dense_texture.obj -o model.glb --binary
  
  # GLB → 3D Tiles（单个 b3dm）
  3d-tiles-tools glbToB3dm -i model.glb -o model.b3dm
  
  # 或创建 tileset（推荐）
  3d-tiles-tools createTilesetJson -i model.glb -o tileset.json
  ```
- **T0.1.2**：验证转换产物
  - 检查 `model.glb` 是否存在且可读
  - 检查 `tileset.json` 和 `*.b3dm` 是否存在
  - 检查 `tileset.json` 内容是否正确（boundingVolume、content 等）
- **T0.1.3**：记录转换参数与耗时
  - 文件大小统计
  - 转换耗时
  - 工具版本信息

#### T0.2 CesiumJS 独立验证

- **T0.2.1**：创建独立 HTML 页面测试 CesiumJS 加载
  - 使用 CesiumJS CDN
  - 加载本地 `tileset.json`（通过 HTTP 服务）
  - 验证交互功能（旋转/缩放/平移）
- **T0.2.2**：记录集成要点
  - CesiumJS 版本选择
  - 初始化参数
  - 错误处理方式

---

### 2.2 后端（FastAPI）任务

#### A. 数据库与模型

- **A1**：在 `Block` 模型新增 `tiles_*` 字段（参考 `recon_*` 命名与类型）
  - 文件：`backend/app/models/block.py`
  - 字段：
    - `tiles_status`：String（NOT_STARTED/RUNNING/COMPLETED/FAILED/CANCELLED）
    - `tiles_progress`：Float（0-100）
    - `tiles_current_stage`：String（obj_to_glb/glb_to_tiles/completed）
    - `tiles_output_path`：String（输出目录路径）
    - `tiles_error_message`：String（错误信息）
    - `tiles_statistics`：JSON（统计信息）
- **A2**：在 `models/database.py` 的轻量迁移逻辑中加入 `tiles_*` 列（保持可幂等）
- **A3**：在 `schemas.py` 中新增：
  - `TilesConvertRequest`（可选参数：keep_glb、optimize）
  - `TilesStatusResponse`（status/progress/stage/output_path/error/statistics）
  - `TilesFilesResponse`（files 列表：name/type/size/mtime/preview_supported/download_url）
  - `TilesetUrlResponse`（tileset_url）

#### B. TilesRunner 服务层

- **B1**：新增 `backend/app/services/tiles_runner.py`
  - `start_conversion(block, db, convert_params)`
  - `cancel_conversion(block_id)`
  - `get_log_tail(block_id, lines)`
  - `recover_orphaned_tiles_tasks()`（启动时恢复 RUNNING）
- **B2**：输入文件准备逻辑（强制一致性）
  - 查找 OpenMVS 纹理输出目录：`recon_output_path/texture/`
  - 查找 `.obj` 文件：`scene_dense_texture.obj` 或 `scene_dense_mesh_refine_texture.obj`
  - 查找对应的 `.mtl` 文件
  - 校验：`.obj` 存在、`.mtl` 存在、纹理图片存在（通过解析 `.mtl` 文件）
- **B3**：转换启动逻辑
  - **阶段1：OBJ → GLB**
    - subprocess：`obj2gltf -i {obj_path} -o {glb_path} --binary`
    - 工作目录：`texture/` 目录（确保纹理路径解析正确）
    - 标准输出重定向到 `run_tiles.log`，并写入内存 ring buffer（供 log tail）
  - **阶段2：GLB → 3D Tiles**
    - subprocess：`3d-tiles-tools createTilesetJson -i {glb_path} -o {tileset_path}`
    - 或：`3d-tiles-tools glbToB3dm -i {glb_path} -o {b3dm_path}` + 手动创建 `tileset.json`
  - 更新 DB：`tiles_status=RUNNING`、`tiles_current_stage`、`tiles_progress`
- **B4**：进度解析（V1 最小）
  - 从日志中解析阶段（obj_to_glb/glb_to_tiles）
  - 或更保守：只用"阶段"与"running/complete"状态（先保证稳定）
  - 进度估算：obj_to_glb 50%，glb_to_tiles 100%
- **B5**：产物发现与 files API
  - 识别 `tileset.json`（必需）
  - 识别 `*.b3dm` 文件（必需）
  - 识别 `model.glb`（可选，根据 `keep_glb` 参数）
- **B6**：安全下载（复用 reconstruction 的 path traversal 防护）
  - 文件：`backend/app/api/tiles.py` 的 `download_tiles_file`
  - 路径解析：`(tiles_output_path / file).resolve()`
  - 校验：`str(resolved).startswith(str(tiles_output_path.resolve()))`
- **B7**：Tileset URL 生成
  - 文件：`backend/app/api/tiles.py` 的 `get_tileset_url`
  - 返回：`/api/blocks/{id}/tiles/download?file=tileset.json` 的完整 URL

#### C. API 路由层

- **C1**：新增 `backend/app/api/tiles.py` 并在 `main.py` 挂载
  - `POST /api/blocks/{id}/tiles/convert`
  - `GET /api/blocks/{id}/tiles/status`
  - `POST /api/blocks/{id}/tiles/cancel`
  - `GET /api/blocks/{id}/tiles/files`
  - `GET /api/blocks/{id}/tiles/download?file=...`
  - `GET /api/blocks/{id}/tiles/log_tail?lines=...`
  - `GET /api/blocks/{id}/tiles/tileset_url`
- **C2**：校验规则
  - Block 必须存在
  - 重建状态必须 COMPLETED 或纹理阶段已完成（`recon_status=COMPLETED` 或存在 `recon_output_path/texture/`）
  - `tiles_status != RUNNING`（避免重复启动）

#### D. 配置与可运维

- **D1**：新增环境变量（settings）
  - `OBJ2GLTF_PATH`（默认 `obj2gltf`，从 PATH 查找）
  - `3DTILES_TOOLS_PATH`（默认 `3d-tiles-tools`，从 PATH 查找）
- **D2**：健康检查端点（可选）：检查工具是否存在、可执行

---

### 2.3 前端（Vue3 + TS）任务

#### E. API 与类型

- **E1**：在 `frontend/src/api/index.ts` 增加 tiles 相关请求封装
  - `convertTiles(blockId, params)`
  - `getTilesStatus(blockId)`
  - `cancelTilesConversion(blockId)`
  - `getTilesFiles(blockId)`
  - `downloadTilesFile(blockId, file)`
  - `getTilesLogTail(blockId, lines)`
  - `getTilesetUrl(blockId)`
- **E2**：在 `frontend/src/types/index.ts` 增加类型定义
  - `TilesConvertRequest`
  - `TilesStatus`
  - `TilesFileInfo`
  - `TilesetUrlResponse`

#### F. UI：3D Tiles 转换面板

- **F1**：新增组件 `TilesConversionPanel.vue`
  - 位置：Block 详情页"重建"标签页中，纹理阶段完成后显示
  - 功能：
    - 转换状态显示（NOT_STARTED/RUNNING/COMPLETED/FAILED）
    - 转换按钮（Start/Cancel）
    - 进度条 + 当前阶段
    - log tail（可展开/收起，复用现有 ProgressView 风格）
    - files 列表：下载/预览
  - 样式：参考 `ReconstructionPanel.vue` 的设计
- **F2**：在 `ReconstructionPanel.vue` 中集成
  - 纹理阶段完成后显示"转换为 3D Tiles"按钮或独立面板
  - 或新增"3D Tiles"标签页（与"重建"标签页并列）

#### G. Viewer：CesiumJS 集成（V1）

- **G1**：引入 CesiumJS
  - 方案1（推荐）：使用 CDN
    ```html
    <script src="https://cesium.com/downloads/cesiumjs/releases/1.XX/Build/Cesium/Cesium.js"></script>
    <link href="https://cesium.com/downloads/cesiumjs/releases/1.XX/Build/Cesium/Widgets/widgets.css" rel="stylesheet">
    ```
  - 方案2：本地构建（后续优化）
- **G2**：实现 `CesiumViewer.vue`
  - 输入：`tilesetUrl`（从 API 获取）
  - 生命周期：
    - `onMounted`：初始化 Cesium Viewer
    - `loadTileset`：加载 tileset.json
    - `onUnmounted`：销毁 Viewer
  - 交互控制：
    - 鼠标旋转/缩放/平移（Cesium 默认）
    - 重置视角按钮
    - 显示/隐藏 UI 控件（Cesium 默认工具栏）
  - 错误处理：
    - WebGL 不支持：提示"浏览器不支持 WebGL"
    - 加载失败：显示错误信息 + 下载入口
- **G3**：与现有 ThreeViewer 的交互一致
  - 可切换显示（Three.js 可视化 ↔ CesiumJS 可视化）
  - 或并列显示（左右分栏）

---

### 2.4 测试任务

#### H. 单元测试

- **H1**：后端单元测试
  - `tiles_runner.py`：转换工具调用、文件路径解析、错误处理
  - `api/tiles.py`：API 路由、参数校验、错误响应
- **H2**：前端单元测试
  - `TilesConversionPanel.vue`：状态显示、按钮交互
  - `CesiumViewer.vue`：Viewer 初始化、错误处理

#### I. 集成测试

- **I1**：使用测试数据完整流程测试
  - 路径：`/root/work/aerotri-web/data/test_obj`
  - 验证：转换成功、文件生成、CesiumJS 加载显示
- **I2**：端到端测试
  - 从 OpenMVS 纹理完成 → 转换 → CesiumJS 显示，完整用户流程

---

## 3. 排期建议（以 1 后端 + 1 前端为例）

> 这里给的是"工程量级别"建议，实际以你们代码习惯与环境安装难度为准。

### 第 1 周：测试数据验证 + 后端基础

- **M0（前置）**：测试数据验证（T0.1-T0.2）
  - 手动转换测试数据
  - CesiumJS 独立验证
  - 确认工具链可用性
- **后端**：A1-A3、B1-B3、C1（先跑通转换启动/取消/日志落盘）
- **前端**：E1-E2、F1（先展示状态与日志、文件下载）

### 第 2 周：后端完善 + 前端 Viewer

- **后端**：B5-B7、恢复逻辑（B1 的 recover）、D1-D2
- **前端**：G1-G3（CesiumJS Viewer 集成），完成 V1 验收

### 第 3 周：测试与优化

- **测试**：H1-H2、I1-I2
- **优化**：错误处理完善、性能优化、用户体验改进

---

## 4. 关键依赖与验收前置

- **工具链可用**：
  - `obj2gltf` 已全局安装，可通过 `obj2gltf` 命令调用
  - `3d-tiles-tools` 已全局安装，可通过 `3d-tiles-tools` 命令调用
  - 工具版本兼容性确认
- **测试数据可用**：
  - `/root/work/aerotri-web/data/test_obj` 目录存在
  - `city1_scene_dense_texture.obj`、`.mtl`、纹理图片完整
- **客户端能力**：
  - 建议 Chrome/Edge/Firefox 最新版本（支持 WebGL）
  - CesiumJS CDN 可访问（或本地构建版本）

---

## 5. 风险缓冲与技术决策点（建议尽早定）

- **转换工具调用方式**：
  - 优先：直接调用全局安装的命令（`obj2gltf`、`3d-tiles-tools`）
  - 备选：通过环境变量指定工具路径
- **CesiumJS 集成方式**：
  - 优先：CDN 版本快速集成（V1）
  - 后续：本地构建以优化加载速度
- **Viewer 布局方式**：
  - 优先：与 Three.js 可视化切换显示（标签页切换）
  - 备选：并列显示（左右分栏）
- **进度解析策略**：
  - 先做保守（阶段+running），后续再做更精确进度（文件大小估算）

---

## 6. 文件清单（新增/修改）

### 6.1 后端文件

**新增**：
- `backend/app/services/tiles_runner.py`：转换服务
- `backend/app/api/tiles.py`：API 路由

**修改**：
- `backend/app/models/block.py`：新增 `tiles_*` 字段
- `backend/app/models/database.py`：数据库迁移逻辑
- `backend/app/schemas.py`：新增 schemas
- `backend/app/main.py`：挂载 tiles 路由
- `backend/app/settings.py`：新增环境变量

### 6.2 前端文件

**新增**：
- `frontend/src/components/TilesConversionPanel.vue`：转换面板
- `frontend/src/components/CesiumViewer.vue`：CesiumJS Viewer

**修改**：
- `frontend/src/api/index.ts`：新增 tiles API
- `frontend/src/types/index.ts`：新增类型定义
- `frontend/src/views/BlockDetailView.vue`：集成转换面板
- `frontend/src/components/ReconstructionPanel.vue`：添加转换入口（可选）

### 6.3 测试文件

**新增**：
- `backend/tests/test_tiles_runner.py`：后端单元测试
- `frontend/src/tests/components/TilesConversionPanel.test.ts`：前端单元测试

---

## 7. 开发顺序建议

### 阶段 1：测试数据验证（M0）

1. 手动执行转换命令，验证工具链
2. 创建独立 HTML 页面测试 CesiumJS
3. 记录转换参数与集成要点

### 阶段 2：后端基础（M1 部分）

1. 数据库字段与模型（A1-A3）
2. TilesRunner 基础功能（B1-B3）
3. API 路由基础（C1）

### 阶段 3：前端基础（M2 部分）

1. API 与类型（E1-E2）
2. 转换面板 UI（F1-F2）

### 阶段 4：后端完善（M1 完成）

1. 产物发现与文件管理（B5-B7）
2. 恢复逻辑（B1 的 recover）
3. 配置与健康检查（D1-D2）

### 阶段 5：前端 Viewer（M2 完成）

1. CesiumJS 集成（G1-G3）
2. 与现有可视化集成

### 阶段 6：测试与优化

1. 单元测试（H1-H2）
2. 集成测试（I1-I2）
3. 用户体验优化

---

## 8. 验收检查清单

### 8.1 功能验收

- [ ] 测试数据能成功转换为 3D Tiles
- [ ] 转换过程中 UI 可实时看到进度与日志
- [ ] 可取消转换，状态正确更新
- [ ] 转换完成后文件列表正确显示
- [ ] CesiumJS Viewer 能正确加载 tileset.json
- [ ] Viewer 交互功能正常（旋转/缩放/平移）
- [ ] 后端重启后 RUNNING 任务能正确恢复

### 8.2 性能/稳定性验收

- [ ] 转换日志与状态正确写入 DB
- [ ] 文件下载接口有路径穿越防护
- [ ] 大文件加载时有清晰反馈
- [ ] 错误处理完善（工具不存在、文件缺失等）

### 8.3 用户体验验收

- [ ] UI 布局合理，与现有设计一致
- [ ] 错误提示清晰，有修复建议
- [ ] 加载过程有进度提示
- [ ] Viewer 交互流畅

---

## 9. 后续扩展（V1.5+，暂不做）

- **分层瓦片（LOD）**：使用 `3d-tiles-tools` 的 `createTilesetJson` 生成多级瓦片
- **地理坐标转换**：读取 COLMAP GPS 信息，转换为 WGS84/UTM
- **纹理优化**：压缩纹理、减少文件大小
- **批量转换**：支持多个 Block 批量转换为 3D Tiles
- **性能监控**：转换耗时、文件大小、加载性能统计

