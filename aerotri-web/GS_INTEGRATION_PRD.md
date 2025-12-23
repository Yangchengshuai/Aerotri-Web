# AeroTri Web + 3D Gaussian Splatting（3DGS）建模与 Web 端查看：PRD

## 0. 文档信息

- **产品**：AeroTri Web（空三 + 倾斜建模）扩展：3D Gaussian Splatting 建模链路
- **目标版本**：V1（可用）+ V1.5（性能/体验增强）
- **相关仓库**：
  - `work/aerotri-web`：现有 Block/任务/重建/Three.js 可视化
  - `work/gaussian-splatting`：3DGS 训练/渲染（PyTorch+CUDA）
  - `work/visionary`：WebGPU 高斯渲染与多格式加载（PLY/SPLAT/KSplat/SPZ/SOG）
- **本文输出**：
  - 以 4 个角色视角的讨论纪要（算法/后端/前端/产品）
  - 收敛后的 PRD：范围、流程、数据流、接口、验收、风险

---

## 1. 背景与机会

现有 AeroTri Web 已支持：

- Block 管理、图像工作目录、安全删除、SfM（COLMAP/GLOMAP/InstantSfM）任务调度与 WS 进度
- SfM 结果（相机 + 稀疏点）Three.js 可视化
- OpenMVS 重建（undistort → densify → mesh → refine → texture）作为第二条 pipeline（状态字段、文件列表/下载、log tail、取消、恢复）

新增 3DGS 的价值：

- 相比传统 mesh 贴图，3DGS 具备更强的视角相关效果与实时渲染潜力，适合 Web 端“快速查看/漫游/对比”
- 3DGS 训练天然复用 SfM 输出（相机位姿 + 稀疏点 + 图像），易于接入到现有 Block 生命周期

---

## 2. 目标（Goals）与非目标（Non-goals）

### 2.1 Goals（V1）

- **G1：在现有 Block 上，一键启动 3DGS 训练**（基于该 Block 的 SfM 输出）
- **G2：训练过程可观测**：状态/阶段/进度/日志 tail/取消/（服务重启后）恢复
- **G3：产物可管理**：列出关键产物（至少：`point_cloud.ply`），支持下载
- **G4：Web 端可加载查看 3DGS 模型**：在 Block 详情页以“3DGS Viewer”方式预览

### 2.2 Goals（V1.5）

- **G5：大模型可用性**：提供至少一种“压缩/加速加载”格式（例如 `.splat/.ksplat/.spz`）
- **G6：体验增强**：相机轨迹/稀疏点/3DGS 叠加显示、对比（不同迭代/不同参数）

### 2.3 Non-goals（暂不做）

- N1：浏览器端在线训练/增量训练（重训练仍在服务端 GPU）
- N2：多租户/权限体系的完整 RBAC（先按单机/内网工具假设）
- N3：分布式训练调度（先单机多 GPU、串行/有限并行）

---

## 3. 角色模拟讨论纪要（四视角）

### 3.1 重建算法专家视角（算法正确性/可解释性）

- **输入契约**：3DGS 训练必须绑定“同一套相机参数与图像路径”，优先使用 Block 的 `working_image_path`（稳定、可控）
- **数据组织**：推荐为每个 Block 生成一个“3DGS source dataset”目录，内部满足 `gaussian-splatting` 的预期结构：
  - `images/`：软/硬链接到 `data/blocks/{id}/images`（或源图像目录）
  - `sparse/0/`：链接到 `data/outputs/{id}/sparse/0`
- **训练产物选型**：
  - V1：直接输出 `point_cloud/iteration_x/point_cloud.ply` 并提供“选择迭代”能力
  - V1.5：对 web 端做压缩（`.spz/.ksplat/.splat`），否则大 PLY 加载慢/内存高
- **质量评估**：
  - 最小：训练曲线（loss/psnr）、可选渲染验证图（train/test render）
  - 若要严谨：支持 `render.py` 输出对比图与 PSNR/SSIM（可选）
- **风险点**：SfM 输出若不一致（旧路径、图像缺失）会导致训练失败；需要明确前置校验与友好报错。

### 3.2 高级后端工程师视角（可运维/可恢复/资源管理）

- **复用现有模式**：参考 OpenMVS 的 `recon_*` 字段与 `/reconstruction/*` API，新增一套 `gs_*` 字段与 `/gs/*` API。
- **任务生命周期**：RUNNING/COMPLETED/FAILED/CANCELLED + stage/progress + log tail + cancel + orphan recovery。
- **GPU/并发**：训练占满 GPU，必须显式选择 GPU（沿用 `/api/gpu/status` 与前端 GPUSelector）。
- **环境隔离**：3DGS 训练依赖 CUDA/PyTorch/C++ 扩展，建议以环境变量配置可执行：
  - `GS_REPO_PATH=/root/work/gaussian-splatting`
  - `GS_PYTHON=/path/to/conda/env/bin/python`
- **文件服务**：复用 reconstruction 的“列出文件/下载文件”方式，对 `outputs/{id}/gs` 做安全的相对路径下载。

### 3.3 高级前端工程师视角（集成成本/体验/兼容性）

- **UI 入口**：Block 详情页新增 “3DGS” Tab 或在现有 `ReconstructionPanel` 类似位置新增 `GaussianSplattingPanel`：
  - 训练配置（iterations/resolution/data_device/…）+ GPU 选择 + Start/Cancel
  - 状态展示：stage/progress + log tail + 文件卡片（下载/预览）
- **Viewer 方案**：
  - V1：优先集成 `work/visionary` 的 three.js/webgpu integration，直接加载 `.ply`
  - 兼容性：Visionary 文档提示 Ubuntu WebGPU/FP16 的问题主要在 ONNX fp16 管线；V1 只加载 PLY，可做 feature detect：
    - 支持 WebGPU：启用 Visionary viewer
    - 不支持：降级提示“浏览器/显卡不支持，建议 Chrome + WebGPU；可下载离线查看”
- **性能策略**：大 PLY 可能导致首屏慢/崩溃，V1 先可用；V1.5 引入压缩格式并做进度条与分段加载（如 SPZ）。

### 3.4 产品经理视角（用户价值/范围控制/验收）

- **用户故事**：
  - 作为测绘/重建用户：SfM 完成后想一键生成 3DGS 并在浏览器里快速查看效果
  - 作为算法调参者：想对比不同训练参数/不同迭代的观感差异，并能导出结果
- **MVP 定义（V1）**：只做“能跑起来 + 能看见 + 可下载 + 可取消 + 可恢复”
- **清晰边界**：不做在线编辑/拼接/大规模批量训练调度；先把单 Block 的闭环做稳

---

## 4. 产品方案（收敛版）

### 4.1 总体流程

1. 用户创建 Block → 上传/选择图像 → 运行空三（SfM）
2. SfM COMPLETED 后，用户进入 Block 详情页 “3DGS”
3. 配置训练参数 + 选择 GPU → 点击“开始训练”
4. 后端创建 `outputs/{block_id}/gs/`，准备 dataset（links）并启动 `gaussian-splatting/train.py`
5. 前端轮询/WS 获取进度 + log tail
6. 训练产物生成 → 文件列表中出现 `point_cloud.ply` → 点击“预览”在 Web 端打开 3DGS Viewer

### 4.2 目录与产物规范（建议）

在 `data/outputs/{block_id}/gs/` 下：

- `run_gs.log`：训练日志（stdout/stderr 持久化）
- `dataset/`：训练输入（链接构建）
  - `images/`（links）
  - `sparse/0/`（links）
- `model/`：训练输出（对应 `-m`）
  - `cfg_args`
  - `cameras.json`（gaussian-splatting 会生成）
  - `point_cloud/iteration_XXXX/point_cloud.ply`
  - `chkpntXXXX.pth`（可选）
- `renders/`（可选）：`render.py` 的输出（用于质量验证）

### 4.3 后端能力需求（V1）

- **训练启动**：`POST /api/blocks/{id}/gs/train`
  - 入参：`gpu_index` + `train_params`（iterations/resolution/data_device/sh_degree/…）
  - 前置校验：
    - Block SfM 状态必须 COMPLETED
    - `output_path/sparse/0` 存在且可读
    - 图像目录存在（优先 `working_image_path`）
- **状态查询**：`GET /api/blocks/{id}/gs/status`
- **取消训练**：`POST /api/blocks/{id}/gs/cancel`
- **日志 tail**：`GET /api/blocks/{id}/gs/log_tail?lines=200`
- **文件列表**：`GET /api/blocks/{id}/gs/files`
  - 返回：迭代列表、可预览文件（`point_cloud.ply`）、下载 URL
- **下载**：`GET /api/blocks/{id}/gs/download?file=...`（相对路径防穿越）
- **恢复**：服务启动时扫描 DB 里 `gs_status=RUNNING` 的任务并：
  - 若进程不存在且产物完整：标 COMPLETED
  - 否则标 FAILED 并给出 error_message

### 4.4 前端能力需求（V1）

- **Block 详情页新增 3DGS 面板**
  - Start/Cancel、配置表单、进度条、log tail、产物列表
- **3DGS Viewer**
  - 直接加载后端提供的 `point_cloud.ply` 下载 URL
  - 基于 `visionary` 的 three.js/webgpu 集成（优先）
  - WebGPU 不可用时：提示与降级策略

---

## 5. 数据模型（DB 扩展建议）

参照 `Block.recon_*`，新增：

- `gs_status`：`NOT_STARTED/RUNNING/COMPLETED/FAILED/CANCELLED`
- `gs_progress`：0–100
- `gs_current_stage`：`initializing/dataset_prepare/training/rendering/completed/...`
- `gs_output_path`：`<output_path>/gs`
- `gs_error_message`：失败摘要
- `gs_statistics`：JSON（耗时、参数、迭代、关键指标）

> 备注：保持命名与 OpenMVS 重建一致，有利于前端复用组件与后端复用恢复逻辑。

---

## 6. 验收标准（Acceptance Criteria）

### 6.1 功能验收（V1）

- **AC1**：SfM 完成的 Block 能成功启动 3DGS 训练（可选 GPU）
- **AC2**：训练过程中 UI 可实时看到 stage/progress 与日志 tail
- **AC3**：可取消训练，状态变为 CANCELLED，日志保留
- **AC4**：训练完成后在文件列表中看到至少一个 `point_cloud.ply`，可下载
- **AC5**：在支持 WebGPU 的 Chrome 上可预览 `point_cloud.ply`（旋转/缩放/平移正常）
- **AC6**：后端重启后，RUNNING 任务能被正确恢复为 COMPLETED/FAILED

### 6.2 性能/稳定性验收（V1）

- **AC7**：训练日志与状态写 DB，不依赖纯内存
- **AC8**：文件下载接口有路径穿越防护
- **AC9**：面对 100MB 级别 PLY，前端给出清晰加载反馈与失败提示（不要求一定流畅）

### 6.3 增强验收（V1.5）

- **AC10**：提供压缩格式（例如 `.spz`）并显著提升加载速度/内存
- **AC11**：支持按迭代选择加载（iteration_7000 / iteration_30000）

---

## 7. 风险与对策

- **R1：训练环境复杂（CUDA/扩展编译）**
  - **对策**：后端仅做“调度”，训练环境通过 `GS_PYTHON/GS_REPO_PATH` 配置；提供健康检查（版本/可执行存在）
- **R2：大文件 Web 加载慢/崩**
  - **对策**：V1 先支持 PLY；V1.5 增加压缩格式（SPZ/KSplat）与 CDN/Range（可选）
- **R3：WebGPU 兼容性差异**
  - **对策**：特性检测 + 明确推荐浏览器/平台；不支持则降级为下载/离线查看
- **R4：SfM 输出与图像路径不一致导致训练失败**
  - **对策**：训练前严格校验：图像存在性、数量一致性、sparse 可读；错误信息明确指向修复方法

---

## 8. 里程碑建议（高层）

- **M1（V1）**：后端 3DGS 训练任务闭环 + 文件管理 API + 前端面板
- **M2（V1）**：集成 Visionary Viewer 加载 PLY
- **M3（V1.5）**：压缩格式与迭代选择 + 体验增强（叠加显示/对比）


