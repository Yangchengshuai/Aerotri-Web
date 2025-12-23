# AeroTri Web + 3DGS：开发计划（可执行）

## 0. 总览

### 0.1 交付目标

- **V1（MVP）**：在现有 Block（SfM 完成）基础上提供 3DGS 训练 + 产物管理 + Web 端 PLY 预览
- **V1.5（增强）**：压缩格式/迭代选择/体验增强（叠加与对比）

### 0.2 关键设计选择（与 PRD 对齐）

- **后端接入形态**：完全复用 OpenMVS 重建的“第二条 pipeline”范式：`GSRunner + gs_* 字段 + /gs/* API + outputs/{id}/gs`
- **训练实现**：调用 `work/gaussian-splatting/train.py`（外部环境），由后端负责组织 dataset、启动/取消、落盘日志与状态
- **Web 端渲染**：优先集成 `work/visionary` 的 three.js/webgpu 集成加载 `.ply`（V1）；不支持 WebGPU 则降级提示

---

## 1. 里程碑与范围

### M1：后端 3DGS 训练闭环（V1）

**产出**

- 新增 DB 字段：`gs_status/gs_progress/gs_current_stage/gs_output_path/gs_error_message/gs_statistics`
- 新增 API：train/status/cancel/files/download/log_tail
- 新增服务：`gs_runner.py`（启动训练、进度解析、取消、恢复）
- 新增目录规范：`data/outputs/{block_id}/gs/`（dataset + model + log）

### M2：前端 3DGS 面板 + PLY Viewer（V1）

**产出**

- Block 详情页新增 3DGS 面板：配置、启动/取消、进度、日志、文件列表
- 3DGS Viewer：可加载后端 `point_cloud.ply` URL 并交互浏览

### M3：性能与体验增强（V1.5）

**产出**

- 迭代选择（iteration_7000/iteration_30000/最新）
- 压缩格式（SPZ/KSplat/Splat）至少一种 + 后端生成/托管策略
- 叠加显示（相机轨迹/稀疏点/3DGS）与基础对比（同 Block 多次训练）

---

## 2. 详细任务拆解（可直接分配）

### 2.1 后端（FastAPI）任务

#### A. 数据库与模型

- **A1**：在 `Block` 模型新增 `gs_*` 字段（参考 `recon_*` 命名与类型）
- **A2**：在 `models/database.py` 的轻量迁移逻辑中加入 `gs_*` 列（保持可幂等）
- **A3**：在 `schemas.py` 中新增：
  - `GSTrainRequest`（gpu_index + train_params）
  - `GSStatusResponse`（status/progress/stage/output_path/error/statistics）
  - `GSFilesResponse`（files 列表：stage/type/name/size/mtime/preview_supported/download_url）

#### B. GSRunner 服务层

- **B1**：新增 `backend/app/services/gs_runner.py`
  - `start_training(block, gpu_index, db, train_params)`
  - `cancel_training(block_id)`
  - `get_log_tail(block_id, lines)`
  - `recover_orphaned_gs_tasks()`（启动时恢复 RUNNING）
- **B2**：dataset 准备逻辑（强制一致性）
  - 创建 `outputs/{id}/gs/dataset/images`（链接到 `working_image_path`）
  - 创建 `outputs/{id}/gs/dataset/sparse/0`（链接到 `output_path/sparse/0`）
  - 校验：图像数量>0、sparse/0 存在、关键 bin 存在（cameras/images/points3D）
- **B3**：训练启动逻辑
  - subprocess：`{GS_PYTHON} train.py -s <dataset> -m <model_path> ...`
  - GPU 选择：`CUDA_VISIBLE_DEVICES` 或训练脚本参数（视 3DGS 支持情况）
  - 标准输出重定向到 `run_gs.log`，并写入内存 ring buffer（供 log tail）
- **B4**：进度解析（V1 最小）
  - 从日志中解析 iteration（例如 `Training progress` 的 tqdm 行）→ 映射到 0–100
  - 或更保守：只用“阶段”与“running/complete”状态（先保证稳定）
- **B5**：产物发现与 files API
  - 识别 `model/point_cloud/iteration_*/point_cloud.ply`
  - 识别 `cfg_args/cameras.json/exposure.json`（可下载不预览）
- **B6**：安全下载（复用 reconstruction 的 path traversal 防护）

#### C. API 路由层

- **C1**：新增 `backend/app/api/gs.py` 并在 `main.py` 挂载
  - `POST /api/blocks/{id}/gs/train`
  - `GET /api/blocks/{id}/gs/status`
  - `POST /api/blocks/{id}/gs/cancel`
  - `GET /api/blocks/{id}/gs/files`
  - `GET /api/blocks/{id}/gs/download?file=...`
  - `GET /api/blocks/{id}/gs/log_tail?lines=...`
- **C2**：校验规则：Block 必须 SfM COMPLETED、gs_status != RUNNING

#### D. 配置与可运维

- **D1**：新增环境变量（settings）
  - `GS_REPO_PATH`（默认 `/root/work/gaussian-splatting`）
  - `GS_PYTHON`（默认空，要求用户配置）
- **D2**：健康检查端点（可选）：检查 `train.py` 是否存在、`GS_PYTHON` 可执行

---

### 2.2 前端（Vue3 + TS）任务

#### E. API 与类型

- **E1**：在 `frontend/src/api/index.ts` 增加 gs 相关请求封装
- **E2**：在 `frontend/src/types/index.ts` 增加 `GSTrainRequest/GSStatus/GSFileInfo`

#### F. UI：3DGS 面板

- **F1**：新增组件 `GaussianSplattingPanel.vue`
  - 训练参数表单（最小：iterations/resolution/data_device/sh_degree）
  - GPUSelector 复用
  - Start/Cancel 按钮（状态机：NOT_STARTED/RUNNING/…）
  - 进度条 + 当前阶段
  - log tail（复用现有 ProgressView 风格）
  - files 列表：下载/预览
- **F2**：BlockDetailView 增加 Tab 或折叠面板入口

#### G. Viewer：Visionary 集成（V1）

- **G1**：以“最小侵入”方式引入 Visionary：
  - 方案1：将 `visionary` 作为独立构建产物（iframe/静态页面）并通过 query 参数传 `ply_url`
  - 方案2：直接在 `aerotri-web/frontend` 以 npm workspace/本地依赖方式引入其 three-integration 模块
- **G2**：实现 `GaussianSplattingViewer.vue`
  - 输入：`plyUrl`
  - 生命周期：初始化 WebGPU renderer → loadPLY → render loop
  - 错误处理：WebGPU 不可用提示 + 下载入口
- **G3**：与现有 ThreeViewer 的交互一致（轨迹球控制、背景色、重置视角）

---

### 2.3 算法/工具链任务（与后端对接）

- **H1**：确定训练默认参数模板（不同数据规模的推荐 preset：fast/balanced/high）
- **H2（可选）**：增加 `render.py` 自动渲染验证图（作为“质量门槛”）
- **H3（V1.5）**：确定压缩格式路线
  - 优先推荐 **SPZ**（Visionary 原生支持、面向大模型效率）
  - 评估是否需要服务端转换工具（Python/Node）与产物大小目标

---

## 3. 排期建议（以 1 后端 + 1 前端 + 0.5 算法支持为例）

> 这里给的是“工程量级别”建议，实际以你们代码习惯与环境安装难度为准。

- **第 1 周**
  - 后端：A1–A3、B1–B3、C1（先跑通训练启动/取消/日志落盘）
  - 前端：E1–E2、F1（先展示状态与日志、文件下载）
- **第 2 周**
  - 后端：B5–B6、恢复逻辑（B1 的 recover）
  - 前端：Viewer 集成（G1–G2），完成 V1 验收
- **第 3 周（V1.5）**
  - 压缩格式与迭代选择（M3），体验增强与性能优化

---

## 4. 关键依赖与验收前置

- **训练环境可用**：`GS_PYTHON` 对应环境已成功安装并能在命令行跑 `python train.py -h`
- **数据一致性**：SfM 输出目录存在 `sparse/0`，图像可读且路径稳定（优先 working_image_path）
- **客户端能力**：建议 Chrome + WebGPU（Windows 独显最佳）；否则提供降级路径

---

## 5. 风险缓冲与技术决策点（建议尽早定）

- **进度解析策略**：先做保守（阶段+running），后续再做 iteration 解析与更精确进度
- **Viewer 接入方式**：优先 iframe 方案可快速落地，后续再做深度集成降低包体与耦合
- **压缩格式选择**：SPZ/KSplat/Splat 的取舍（压缩率、生成工具链、浏览器内存）


