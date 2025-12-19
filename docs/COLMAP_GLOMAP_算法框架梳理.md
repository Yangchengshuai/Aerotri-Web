# COLMAP / GLOMAP 算法框架梳理（基于 `work/colmap/src/colmap`）

> 目的：对现有 COLMAP 与本仓库集成的 GLOMAP 全局式重建流程做一次“读代码级”的框架梳理，重点覆盖：  
> **COLMAP**：特征提取、特征匹配、增量式重建（Incremental SfM）  
> **GLOMAP**：Global Mapper 全局式重建（Global SfM）  
> 并解答增量式重建中 **Local/Global BA 调度、重三角化** 等疑惑点（含纠正）。

---

## 代码目录地图（你后续查源码最常用的入口）

- **特征提取/匹配控制器**：`work/colmap/src/colmap/controllers/feature_extraction.cc`、`feature_matching.cc`
- **增量式重建总控（调度 BA/重建循环）**：`work/colmap/src/colmap/controllers/incremental_pipeline.{h,cc}`
- **增量式重建核心算法（注册、三角化、Local/Global BA）**：`work/colmap/src/colmap/sfm/incremental_mapper.{h,cc}`
- **三角化与重三角化**：`work/colmap/src/colmap/sfm/incremental_triangulator.*`
- **BA（Ceres）建模与求解**：`work/colmap/src/colmap/estimators/bundle_adjustment.{h,cc}`
- **GLOMAP 全局式重建入口（与 COLMAP 数据互转）**：`work/colmap/src/colmap/controllers/global_pipeline.{h,cc}`

---

## COLMAP：从特征到增量式 SfM（Incremental Mapper）

### 1) 特征提取（Feature Extraction）

**目标**：对每张图生成关键点/描述子，并写入数据库（SQLite DB）。

典型路径：

```text
images/  ->  ImageReader  ->  SIFT(或其它 extractor)  ->  Database(features)
```

源码入口（控制器层）：
- `controllers/feature_extraction.cc`：组织读取图片、提取特征、写入 DB（并行、GPU/CPU 等选项在这里/OptionManager 汇总）。

---

### 2) 特征匹配（Feature Matching / Two-View Geometry）

**目标**：为图像对建立匹配，并对每对做几何验证（Two-view geometry / RANSAC），最终形成**视图图**/scene graph 相关信息（存数据库 + cache）。

典型路径：

```text
DB(features) -> Pairing(Exhaustive/Sequential/Vocab/Spatial/...) 
            -> DescriptorMatching
            -> TwoViewGeometry(RANSAC验证) 
            -> DB(matches + two_view_geometries)
```

源码入口（控制器层）：
- `controllers/feature_matching.cc`
- 选项汇总：`controllers/option_manager.{h,cc}`

---

### 3) 增量式重建（Incremental SfM）：总流程（ASCII）

下面这张图基本对应 `IncrementalPipeline::ReconstructSubModel()` 的结构：

```text
┌──────────────────────────────────────────────────────────────┐
│  IncrementalPipeline::ReconstructSubModel                     │
└──────────────────────────────────────────────────────────────┘
        │
        │  (A) 初始化：找初始对 -> 注册初始对 -> 三角化 -> Global BA
        ▼
  FindInitialImagePair / EstimateInitialTwoViewGeometry
        │
        ▼
  RegisterInitialImagePair
        │
        ▼
  TriangulateImage(image1 + image2)
        │
        ▼
  AdjustGlobalBundle  (初始对之后立刻做一次全局 BA)
        │
        ▼
  FilterPoints / FilterFrames
        │
        │  (B) 主循环：每次尝试注册一张新图
        ▼
  do {
       FindNextImages
       RegisterNextImage   (失败可 fallback: RegisterNextStructureLessImage)
       TriangulateImage(new)
       IterativeLocalRefinement   (Local BA + merge/complete + filter)
       if (CheckRunGlobalRefinement) {
            IterativeGlobalRefinement  (retriangulate + Global BA + normalize + filter)
       }
       if (注册卡住且上一轮成功) {
            IterativeGlobalRefinement  (尝试解卡一次)
       }
  } while (reg_next_success || prev_reg_next_success)

  (结束) 若最后一次增量 BA 不是 global，则再做一次 final global refinement
```

---

## 增量式重建的关键细节：注册 / 三角化 / BA / 重三角化

### 1) “每加多少张图触发一次 BA？”——真实答案是：Local 每张必做；Global 按阈值触发

#### Local BA（每成功注册一张新图都会触发）

在 `IncrementalPipeline::ReconstructSubModel()` 中，只要 `reg_next_success`，就会：

- `TriangulateImage(...)`
- `mapper.IterativeLocalRefinement(...)`

也就是说：**不是“每 N 张图才 BA”，而是“每张图注册成功后都会做 Local refinement（可多轮）”。**

#### Global BA（按“增长率/频率”阈值触发 + 解卡触发）

触发条件在 `IncrementalPipeline::CheckRunGlobalRefinement()`，核心是四个 OR：

- 注册帧数达到：`NumRegFrames >= ba_global_frames_ratio * prev_frames`
- 注册帧数达到：`NumRegFrames >= prev_frames + ba_global_frames_freq`
- 点数达到：`NumPoints3D >= ba_global_points_ratio * prev_points`
- 点数达到：`NumPoints3D >= prev_points + ba_global_points_freq`

默认值（见 `IncrementalPipelineOptions`）：
- `ba_global_frames_ratio = 1.1`（约 10% 增长）
- `ba_global_points_ratio = 1.1`（约 10% 增长）
- `ba_global_frames_freq = 500`（兜底：每新增 500 帧触发）
- `ba_global_points_freq = 250000`（兜底：每新增 25 万点触发）

另外还有一个非常实用的“解卡逻辑”：

```text
如果这轮没有任何图能注册成功，并且上一轮曾经成功过，
则强制跑一次 IterativeGlobalRefinement()，再继续尝试注册。
```

> 纠正你提到的 “点数每增加 20% 触发 BA”：在这份代码里是 **可配置的 ratio**，默认是 **10%**（1.1），不是写死 20%。

---

### 2) Local BA 是“局部”还是“全局”？优化范围/对象分别是什么？

#### Local BA（`IncrementalMapper::AdjustLocalBundle`）

**优化范围（scope）**：
- 以当前新注册的 `image_id` 为中心，找若干“共享 3D 点最多”的邻居图像形成 `local_bundle`  
- `local_bundle` 的规模由 `IncrementalMapper::Options::ba_local_num_images` 控制（默认 6）

**优化对象（variables）**：
- 这些图像（以及同一 frame 下的 images）的位姿（rig-from-world / sensor-from-rig 取决于配置）
- 部分相机内参（若某 camera 的“已注册图像没有全包含在 local bundle”则会固定内参，避免在局部窗口里把全局已稳定内参拉歪）
- **只优化“新点/短 track 点”**：对 `point3D_ids` 里 track 长度 \( \le 15 \) 或尚未有误差的点设为 variable  
  这是一个明确的加速策略：**长 track 点通常已稳定，放进 Local BA 反而拖慢且收益小**

**Local BA 后还会做什么？**
- MergeTracks（把 refined tracks 与其它点合并）
- CompleteTracks / CompleteImage（补全轨迹，帮助后续注册）
- 对受影响图像与点做 outlier filter（reproj error / tri-angle）

#### Global BA（`IncrementalMapper::AdjustGlobalBundle`）

**优化范围（scope）**：
- 默认把当前 reconstruction 的所有注册 frames/images 都加入 BA（属于全局）
- 可选启用 `ba_global_ignore_redundant_points3D`：先忽略冗余点做一遍，再固定其它参数只优化被忽略点（两阶段）

**优化对象（variables）**：
- 全部注册相机/rig 位姿（除非显式设为 constant）
- 内参（按 refine_* 选项）
- 3D 点（除忽略的冗余点策略外基本全量）
- 可选 **位置先验（Pose Prior / RTK）**：若 `use_prior_position=true` 且已注册图像数 > 2，会走 `CreatePosePriorBundleAdjuster(...)`

---

### 3) “重三角化 / Track completion / Local BA / Global BA 谁先谁后？”

**关键点**：在这份实现里，**重三角化（Retriangulate）是放在 Global refinement 里做的**，不是每次 Local BA 都做全局重三角化。

Global refinement（`IncrementalMapper::IterativeGlobalRefinement`）流程是：

```text
CompleteAndMergeTracks
Retriangulate
for i in refinements:
    AdjustGlobalBundle
    (可选 Normalize)
    CompleteAndMergeTracks
    FilterPoints
    if changed < threshold: break
```

---

## 你提的 4 个疑惑：逐条解答与纠正（对齐源码）

### 1) 增量式重建中，每增加多少张照片进行一次 BA？是否按新增点数/20% 触发？

- **Local BA**：每成功注册一张新图，都会跑 `IterativeLocalRefinement()`（“每张必做”，不是按张数阈值）。
- **Global BA**：不是“每 N 张图”，而是由 `CheckRunGlobalRefinement()` 用 **增长率 ratio** 与 **频率 freq** 共同控制。
  - 默认是 **约 10% 增长（1.1）**触发（帧或点都可触发），或达到 **500 帧 / 25 万点**的绝对增量触发。
- **重三角化**：发生在 `IterativeGlobalRefinement()` 里，每次 global refinement 都会先 `Retriangulate()`。

### 2) 增量 BA 是局部还是全局？Local BA / Global BA 的范围与对象是什么？

- **每新增图片**：先三角化，再跑 **Local refinement（局部 BA）**。
  - scope：新图 + 最相关的若干邻居图（由 `ba_local_num_images` 控制）
  - vars：局部窗口内的位姿 +（可选）内参 + “新/短 track 点”
- **Global BA**：按阈值触发的全局优化。
  - scope：全体注册 frames/images（全局）
  - vars：全局位姿 +（可选）内参 +（可选）点子集策略（忽略冗余点）+（可选）RTK/先验位置约束

> 纠正“点数增加 20% 才 global BA”：在本实现中是 ratio 参数（默认 1.1），不是写死 20%。

### 3) 耗时主要在 Global BA 还是 Local BA？Global BA 启动条件是什么？误差项怎么构建？RTK 初始位姿能减少 Global BA 吗？如何加速 SfM？

- **一般结论**：单次 **Global BA** 通常比单次 Local BA 更重（变量/残差规模更大）；但 **Local BA 是“每张图都做”**，累积耗时也可能显著，尤其在长序列/大量图像下。
- **Global BA 启动条件**：见前文 `CheckRunGlobalRefinement()` 的 ratio/freq 四条件 OR；另有“注册卡住时强制跑一次 global refinement 解卡”。
- **误差项（residual）**：
  - 基础项：每个观测（2D-3D）对应 **重投影误差**（2 维 residual），以 `ReprojErrorCostFunctor` 等 cost functor 加入 ceres problem。
  - 可选项：`use_prior_position=true` 时加入 **位置先验残差**（并可配置鲁棒核）。
- **RTK/先验位姿的影响**：
  - 代码里支持 `use_prior_position`，会走 `CreatePosePriorBundleAdjuster(...)`，通常能更稳、更快收敛（尤其尺度/漂移）。
  - 但**不会自动改变 Global BA 的触发频率**：触发频率仍由 ratio/freq 参数控制；你若希望“少跑 global”，需要调大 `ba_global_*` 阈值，或采用 global/hierarchical pipeline。
- **加速建议（从“这份代码暴露的旋钮”出发）**：
  - 调整 Global BA 触发：增大 `ba_global_frames_ratio/points_ratio`，或增大 `ba_global_*_freq`
  - 降低每次 BA 成本：降低 `ba_global_max_num_iterations` / `ba_local_max_num_iterations`
  - 减少 residual 规模：启用 `ba_global_ignore_redundant_points3D`（并调 `*_min_coverage_gain`）
  - 利用先验：开启 `use_prior_position`（若你的 DB 里有 pose priors），必要时配合鲁棒核
  - 工程层面：匹配策略（Sequential/Spatial）、降低特征数、并行线程等（由 feature/matching options 决定）
  - 算法层面：考虑直接走 **global mapper（GLOMAP）** 或 **hierarchical pipeline**（适合大规模）

### 4) 现在的 BA 是纯 CPU 吗？Ceres 有 GPU 版本吗？

**不是“纯 CPU 写死”。** 这份代码里 `BundleAdjustmentOptions` 和 `IncrementalPipelineOptions` 都支持 `use_gpu`：

- 当 `COLMAP_CUDA_ENABLED` 且 Ceres 编译启用 CUDA（并满足版本条件）时：
  - dense 线代库可切到 `ceres::CUDA`
  - sparse 线代库可切到 `ceres::CUDA_SPARSE`（cuDSS）
- 否则会打印 warning 并 **自动回退 CPU solver**。

也就是说：**“能否真正 GPU”取决于编译配置（COLMAP/Ceres/CUDA/cuDSS）+ 问题规模阈值（默认 `min_num_images_gpu_solver=50`）**。

---

## GLOMAP：Global SfM（Global Pipeline）在本仓库的接入方式

### 1) GlobalPipeline 的核心结构

入口在 `controllers/global_pipeline.cc`，流程非常清晰：

```text
Database -> ConvertDatabaseToGlomap -> (ViewGraph + rigs/cameras/frames/images)
         -> GlobalMapper::Solve(...)
         -> ConvertGlomapToColmap -> ReconstructionManager 输出
         -> (可选) ExtractColorsForAllImages(image_path)
```

重要实现点：
- 通过 `glomap::ConvertDatabaseToGlomap(...)` 把 COLMAP 的 database/caches 转为 glomap 的 `ViewGraph` 与数据容器
- `glomap::GlobalMapper global_mapper(options_); global_mapper.Solve(...)`
- 结果可能按 `cluster_id` 拆成多个 component 输出（largest_component_num 判断）
- 最终再 `glomap::ConvertGlomapToColmap(...)` 回写到 COLMAP 的 `Reconstruction`

> 注：本仓库路径下没有 glomap 的实现源码（仅 include 头文件），所以这里描述的是**接入与数据流**；glomap 内部的“旋转平均/平移求解/全局 BA/聚类”等算法细节需要去 glomap 上游项目进一步阅读。

---

## 附：最常用的“调参入口”速查

- 增量式 mapper 的 BA 调度阈值：`IncrementalPipelineOptions`（`controllers/incremental_pipeline.h`）
  - `ba_global_frames_ratio / ba_global_points_ratio`
  - `ba_global_frames_freq / ba_global_points_freq`
  - `ba_local_max_num_iterations / ba_global_max_num_iterations`
  - `ba_use_gpu / ba_gpu_index`
  - `use_prior_position / use_robust_loss_on_prior_position / prior_position_loss_scale`
- Local bundle 窗口大小：`IncrementalMapper::Options::ba_local_num_images`（`sfm/incremental_mapper.h`）


