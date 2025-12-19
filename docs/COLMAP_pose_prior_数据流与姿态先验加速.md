## 1. Pose Prior 在当前 @work/colmap 代码中的支持情况

### 1.1 是否包含你列出的 5 个 Pose Prior 相关改动？

从当前仓库代码可以明确看到：

- `PosePrior` 已经具备：
  - 通用传感器关联字段 `corr_data_id`（含 `sensor_id.type`，支持 CAMERA / 未来 IMU 等）
  - 位置、协方差、坐标系（WGS84 / CARTESIAN）
  - **重力向量 `gravity`** 字段  
  → 对应于：
  - **Associate … to generic sensor measurement data**
  - **Add gravity to pose prior**

- SQLite 数据库层：
  - 已有 `pose_priors` 表，列包括：`corr_data_id / corr_sensor_id / corr_sensor_type / position / position_covariance / gravity / coordinate_system`
  - 在 `PostMigrateTables()` 中实现了从旧表 `pose_priors_old(image_id, …)` 到新结构的迁移逻辑，并在迁移时自动填入 `corr_sensor_type=CAMERA`、`gravity` 默认值
  - 引入了 `MaybeThrowDeprecatedPosePriorError()`，阻止继续使用基于 image 的旧 API  
  → 对应于：
  - **Fix and simplify database pose prior migration**

- Synthetic / test 代码中已经支持对 pose prior 的噪声与重力的合成（`scene/synthetic.cc`、`pose_prior_test.cc` 等），并不再把“噪声合成”混在主算法路径中  
  → 对应于：
  - **Synthesize gravities and move pose prior noise synthesis**

- GLOMAP 全局管线：
  - 在 `GlobalPipeline::Run()` 中从数据库读出 `std::vector<PosePrior>`，并将其传入 `glomap::GlobalMapper::Solve(...)`
  - GLOMAP 不再有独立的“重力字段”，而是直接从 `PosePrior.gravity` 读取  
  → 对应于：
  - **Replace glomap gravity info with pose prior**

结合以上，可以认为当前 @work/colmap 仓库功能上已经包含了你列出的这几类改动（即使具体 commit SHA 无法在本地直接看到，也可以认为是在它们之后的版本，例如 CHANGELOG 中的 COLMAP 3.13.0）。

---

### 1.2 默认配置下：COLMAP 增量 SfM 会不会自动使用位置先验？

**结论：不会。**  
当前增量 SfM（`mapper`）默认并不会使用数据库中的 pose prior 位置约束，除非你显式启用。

关键点：

- `IncrementalPipelineOptions` / `IncrementalMapper::Options` 里有：

```text
bool use_prior_position = false;
bool use_robust_loss_on_prior_position = false;
```

- 普通 `colmap mapper` 命令行：
  - 默认不会修改 `use_prior_position`，因此增量管线只做“纯视几何”BA，不会读 `pose_priors`。

- 只有以下两种情况会“默认打开”先验：
  - 使用 CLI 命令：`colmap pose_prior_mapper`（内部在 `RunPosePriorMapper()` 中把 `options.mapper->use_prior_position = true;`）
  - GUI 中在 **Mapper Priors** 面板里勾选 `use_prior_position`。

**所以：如果你之前只是用 `colmap mapper` 或 aerotri-web 封装的“普通增量空三”，在没有额外配置的前提下，这些空三默认**没有**利用 pose prior。**

---

### 1.3 默认配置下：GLOMAP 会不会使用 pose prior？

GLOMAP pipeline（`glomap mapper`）的接口中直接接收 `std::vector<PosePrior>`：

- 只要数据库 `database.db` 中的 `pose_priors` 表有数据，且 GLOMAP 内部没有显式关掉相应模块，它就会使用这些先验（包括位置与重力）：
  - 全局定位（GlobalPositioning）时用来约束 / 初始化相机外参与尺度；
  - 全局 BA 时添加对应的先验残差。

不过，这取决于当前 GLOMAP 的 options 具体实现；从当前版本的代码来看，并没有一个像 `use_prior_position` 那样的全局“关掉先验”的 flag，因此**一般认为：GLOMAP 只要见到 pose prior 就会使用它们。**

---

## 2. Pose Prior 的完整数据流（从输入到 BA / GLOMAP）

下面这部分侧重“图像相机 position / gravity 先验”的数据流，以及它在 COLMAP / GLOMAP 中的使用方式。

### 2.1 总览 ASCII 图

```text
          +----------------------------+
          |   外部传感器/元数据来源    |
          |  - EXIF(GPS: lat/lon/alt) |
          |  - IMU(重力/姿态)         |
          |  - 自定义轨迹(JSON/CSV)   |
          +-------------+--------------+
                        |
                        v
          +----------------------------+
          |   ImageReader / Python API |
          |  - 从 EXIF 读 GPS          |
          |  - 或 Python 手动设置      |
          |  => 填充 PosePrior 对象    |
          +-------------+--------------+
                        |
                        v
          +----------------------------+
          |        Database / SQLite   |
          |  表: pose_priors           |
          |  - corr_data_id            |
          |  - corr_sensor_id/type     |
          |  - position / covariance   |
          |  - gravity                 |
          +-------------+--------------+
                        |
                        v
        +---------------+----------------------+
        |         DatabaseCache / 控制器       |
        |  - DatabaseCache::SetupPosePriors()  |
        |  - ReadAllPosePriors()               |
        +---------------+----------------------+
                        |
                        v
  +---------------------+-----------------------------+
  |       SfM / Mapper / GLOMAP 管线入口              |
  |  - IncrementalPipeline (mapper / pose_prior_mapper)|
  |  - GlobalPipeline (GLOMAP)                        |
  +---------------------+-----------------------------+
                        |
                        v
+-----------------------------------------------------------+
|              优化阶段（Ceres / GlobalMapper）             |
|                                                           |
|  1) 对齐重建到先验坐标系：AlignReconstructionToPosePriors |
|  2) 在 BA 中添加协方差加权的 Pose Prior 残差              |
|  3) 在 GLOMAP 中约束全局尺度 / 姿态 / 重力方向            |
+-----------------------------------------------------------+
```

---

### 2.2 从“图像/传感器”到 `PosePrior`

#### 2.2.1 ImageReader 自动读取 GPS 位置

在 `ImageReader::Next` 中，如果图像 EXIF 里有经纬高，就填充传入的 `PosePrior`：

```text
Eigen::Vector3d position_prior;
if (bitmap->ExifLatitude(&position_prior.x()) &&
    bitmap->ExifLongitude(&position_prior.y()) &&
    bitmap->ExifAltitude(&position_prior.z())) {
  pose_prior->position = position_prior;
  pose_prior->coordinate_system = PosePrior::CoordinateSystem::WGS84;
}
```

注意：

- 这里只设置了 `position` 与 `coordinate_system=WGS84`；
- `gravity` 需要你从 IMU / 其他传感器或脚本中单独写入。

#### 2.2.2 Python / 脚本写入 Pose Prior

常见做法：

- 在数据预处理阶段用 Python：
  - 从 GNSS / IMU 轨迹文件中读出**每帧**的位置 / 姿态 / 重力；
  - 将其写入 COLMAP 的 SQLite `database.db` 的 `pose_priors` 表（直接用 pycolmap 接口或 `scripts/python/database.py`）。

ASCII 示意：

```text
CSV / JSON 轨迹文件
       |
       v
   Python 脚本
   - 解析每帧 pose
   - 构造 PosePrior(position, cov, gravity)
   - 调用 db.WritePosePrior(...)
       |
       v
   database.db / pose_priors
```

---

### 2.3 数据库存储与迁移

#### 2.3.1 表结构（最终形态）

当前 `pose_priors` 表结构（逻辑）：

```text
pose_priors
-----------
pose_prior_id       INTEGER  PRIMARY KEY
corr_data_id        INTEGER           -- 通用数据 ID（如 image_id）
corr_sensor_id      INTEGER           -- 传感器 ID（如 camera_id）
corr_sensor_type    INTEGER           -- SensorType (CAMERA / future IMU)
position            BLOB (3x1 double)
position_covariance BLOB (3x3 double)
gravity             BLOB (3x1 double)
coordinate_system   INTEGER (WGS84 / CARTESIAN)
```

并有唯一索引：

```text
UNIQUE(corr_data_id, corr_sensor_id, corr_sensor_type)
```

#### 2.3.2 旧版本迁移（image_id → corr_data_id / corr_sensor_*）

迁移动机：

- 早期版本 pose prior 只挂在 `image_id` 上；
- 新版本要支持多传感器（rig / IMU），必须变为 `frame + sensor` 级别。

迁移步骤（在 DB 打开时自动执行）：

```text
1) 检查旧表是否存在：
   - 存在列 pose_priors.image_id → 重命名为 pose_priors_old

2) 用 SQL 从旧表 + images 表生成新表：
   - pose_prior_id      ← old.image_id
   - corr_data_id       ← old.image_id
   - corr_sensor_id     ← images.camera_id
   - corr_sensor_type   ← SensorType::CAMERA
   - position / position_covariance / coordinate_system 直接拷贝
   - gravity           ← 默认 PosePrior.gravity（NaN）

3) 删除 pose_priors_old
```

这部分逻辑在 `PostMigrateTables()` 中实现，用户只需要正常打开数据库即可。

---

### 2.4 在 SfM / Mapper 中如何使用 Pose Prior

#### 2.4.1 IncrementalMapper：是否启用 `use_prior_position`

在增量 SfM 中，是否使用 pose prior 由 `use_prior_position` 控制：

```text
// options 是 IncrementalMapper::Options
const bool use_prior_position =
    options.use_prior_position && ba_config.NumImages() > 2;

std::unique_ptr<BundleAdjuster> bundle_adjuster;
if (!use_prior_position) {
  // 使用默认 BundleAdjuster：只看重投影残差
  bundle_adjuster =
      CreateDefaultBundleAdjuster(ba_options, ba_config, *reconstruction_);
} else {
  // 使用 PosePriorBundleAdjuster：位置先验 + 视几何一起优化
  bundle_adjuster = CreatePosePriorBundleAdjuster(
      ba_options,
      prior_options,
      ba_config,
      pose_priors_from_database,
      *reconstruction_);
}
```

ASCII 决策流程：

```text
                    +---------------------+
                    | options.use_prior_  |
                    | position == true ?  |
                    +----------+----------+
                               |
                 +-------------+--------------+
       false / <3 imgs                    true / ≥3 imgs
                 |                                    |
                 v                                    v
       +--------------------+             +--------------------------+
       | DefaultBundle      |             | PosePriorBundleAdjuster  |
       | 仅重投影约束       |             | 重投影 + 位置先验        |
       +--------------------+             +--------------------------+
```

#### 2.4.2 PosePriorBundleAdjuster 的两大作用

1. **AlignReconstructionToPosePriors：对齐重建到先验坐标系（Sim3）**

   - 从 pose prior 中读取 position（及其协方差）；
   - 使用 RANSAC 求解一个 Sim3，把当前重建的投影中心对齐到先验位置；
   - 对成功对齐的情况，把重建整体变换到以先验为基准的坐标系。

2. **在 Ceres 中添加“协方差加权的位置先验残差”**

   - 对于每个带 position 的 pose prior：
     - 如果图像是 frame 的参考相机：对 `frame.RigFromWorld()` 加 `AbsolutePosePositionPrior`；
     - 如果是非参考相机：对 `cam_from_rig * rig_from_world` 加 `AbsoluteRigPosePositionPrior`；
   - 协方差：
     - 若 pose prior 自带 `position_covariance`，直接使用；
     - 否则使用兜底 `prior_position_fallback_stddev^2 * I`。

ASCII 残差示意（参考相机）：

```text
世界系下图像投影中心 C(frame,RigFromWorld)
        |
        v
  残差 r = C - position_prior
  cost = r^T * Sigma^{-1} * r

Sigma = position_covariance 或 fallback_stddev^2 * I
```

---

### 2.5 GLOMAP 中如何使用 Pose Prior

在 GLOMAP 的全局管线中：

1. 从 COLMAP 数据库读取视图图、rigs、cameras、frames、images。
2. 同时读出所有 `PosePrior`：

```text
std::vector<PosePrior> pose_priors = database->ReadAllPosePriors();
```

3. 把上述数据一起传入 `glomap::GlobalMapper::Solve`：

```text
global_mapper.Solve(
    *database,
    view_graph,
    rigs,
    cameras,
    frames,
    images,
    tracks,
    pose_priors);
```

4. 在 GlobalMapper 内部：
   - 使用 pose prior 的 position / covariance / gravity 约束各帧的位姿；
   - 在 global BA 中与 GLOMAP 的相对约束（两视几何、rig 约束等）一起优化。

ASCII 大致结构：

```text
database.db
  ├─ view_graph (image pairs + 两视几何)
  ├─ rigs / cameras / frames / images
  └─ pose_priors (position + gravity + cov)
          |
          v
 GLOMAP::GlobalMapper::Solve(...)
          |
          +--> 全局定位 / 初始化
          +--> 全局 BA (Ceres)
                  - 重投影残差
                  - 相对姿态/rig 约束
                  - Pose Prior 残差 (位置 + 重力)
```

---

## 3. 如何判断你已经跑过的空三是否使用了 Pose Prior？

你目前已经跑了几组增量空三，常见路径有：

- 直接 `colmap mapper`；
- 或通过 aerotri-web 调用 mapper；
- 以及可能已经跑过 GLOMAP。

下面分别给出检查方法。

### 3.1 检查数据库中是否有 Pose Prior

1. 确认你的 `database.db` 路径，比如：

```text
/root/work/aerotri-web/data/outputs/<run-id>/database.db
```

2. 用 sqlite3 查看 `pose_priors` 表的行数：

```bash
sqlite3 /path/to/database.db "SELECT COUNT(*) FROM pose_priors;"
```

- 返回 `0`：数据库里**根本没有** pose prior → 不可能被使用；
- 返回 `>0`：数据库中**存在** pose prior → 后续还要看 mapper/GLOMAP 是否启用。

### 3.2 检查 Incremental Mapper 是否启用了 `use_prior_position`

#### 3.2.1 从命令行参数判断

- 如果你是用 CLI：
  - **普通增量空三**：通常是

```bash
colmap mapper \
  --database_path ... \
  --image_path ... \
  --output_path ...
  # 一般没有 --Mapper.use_prior_position
```

  - **显式使用先验的空三**：

```bash
colmap mapper \
  ... \
  --Mapper.use_prior_position 1 \
  --Mapper.use_robust_loss_on_prior_position 1 \
  --Mapper.prior_position_loss_scale <值>
```

- 如果你是通过 `colmap pose_prior_mapper`：
  - 这个命令内部已经自动设置：

```text
options.mapper->use_prior_position = true;
```

→ **只有这两种方式才会在增量空三中用到位置先验。**

#### 3.2.2 从日志 / run.log 中判断

在 aerotri-web 生成的 `run.log` 里，你可以：

```bash
grep -n "use_prior_position" run.log
grep -ni "pose prior" run.log
grep -ni "AlignReconstructionToPosePriors" run.log
```

如果看不到任何类似：

- `MapperPriorsOptionsWidget: use_prior_position = 1`
- `AlignReconstructionToPosePriors`
- `Pose Prior Bundle adjustment report`

而只有普通的：

- `Bundle adjustment report`  

那基本可以认为：**这次增量空三没有使用 pose prior。**

### 3.3 检查 GLOMAP 是否使用了 Pose Prior

对于 GLOMAP：

1. 首先同样用 sqlite3 看 `pose_priors` 行数（见 3.1）。
2. 在 GLOMAP 的日志（例如 `glomap_mapper.log` 或 aerotri-web 的 run.log）中搜索：

```bash
grep -ni "pose prior" glomap_mapper.log
grep -ni "gravity" glomap_mapper.log
```

如果 GLOMAP 内部有专门打日志，一般会有：

- “Using X pose priors for global positioning”
- “Using gravity priors from pose_priors table”

否则，就需要直接看 GLOMAP 的源码或在本地打一些 debug log 来确认（当前版本接口已经把 `pose_priors` 传进去了，但具体选用策略由 GLOMAP 内部控制）。

---

## 4. 如何在你的工程中“显式地启用姿态先验加速”？

### 4.1 推荐路线 A：在 COLMAP 增量 SfM 中启用 Pose Prior

1. **准备 pose prior（位置 + 协方差 + 可选重力）：**
   - 用 Python 脚本读 GNSS/IMU 轨迹；
   - Map 到图像文件名 / frame / camera；
   - 写入 `database.db` 的 `pose_priors` 表。

2. **跑 `pose_prior_mapper`：**

```bash
colmap pose_prior_mapper \
  --database_path /path/to/database.db \
  --image_path /path/to/images \
  --output_path /path/to/sparse_with_prior \
  --Mapper.ba_use_gpu 1 \
  --Mapper.ba_gpu_index 0 \
  --prior_position_std_x 3.0 \
  --prior_position_std_y 3.0 \
  --prior_position_std_z 5.0 \
  --use_robust_loss_on_prior_position 1 \
  --prior_position_loss_scale 3.0
```

3. **观察效果：**
   - Iteration 数是否减少；
   - 收敛速度、尺度是否更稳定；
   - 有无大漂移 / 方向翻转情况。

### 4.2 推荐路线 B：在 GLOMAP 全局重建中利用 Pose Prior

1. 同样先在 `database.db` 中准备好 `pose_priors`。
2. 直接运行 GLOMAP：

```bash
glomap mapper \
  --database_path /path/to/database.db \
  --image_path /path/to/images \
  --output_path /path/to/glomap_out \
  --output_format bin \
  --GlobalPositioning.use_gpu 1 \
  --GlobalPositioning.gpu_index 0 \
  --BundleAdjustment.use_gpu 1 \
  --BundleAdjustment.gpu_index 0
```

3. 对比：
   - 有无 pose prior 时，位置 / 姿态的收敛速度与稳健性；
   - 大范围航测数据中，尺度与绝对位置的稳定性。

---

## 5. 小结（给你排查当前工程的 checklist）

- **是否包含相关 commit 功能？**  
  - 是的：`PosePrior.gravity`、DB 迁移、GLOMAP 使用 pose_prior 等都已经在当前代码中。

- **你之前的增量空三是否使用了位置先验？**  
  - 如果是“普通 `colmap mapper` / aerotri-web 默认配置”，**大概率没有**；
  - 除非你显式：
    - 用了 `pose_prior_mapper` 命令，或
    - 在 CLI 中指定 `--Mapper.use_prior_position 1`，或
    - 在 GUI 的 Mapper Priors 中开启 `use_prior_position`。

- **如何确认？**
  - `sqlite3 database.db "SELECT COUNT(*) FROM pose_priors;"` 看先验是否存在；
  - 在 run.log 中搜索 `use_prior_position` / `Pose Prior Bundle adjustment report`；
  - 在 GLOMAP 日志中搜索 `pose prior` / `gravity`。

如果你愿意，我也可以根据你实际的一份 `run.log` 和 `database.db` 路径，帮你“现场”判断那几次实验到底有没有用到 pose prior，并给出下一步优化建议。 



---

## 6. 附录：StonerLing/glomap `pose-position-prior-constraint` 分支做了哪些改动？与当前 @work/colmap 的 GLOMAP 对比

> 参考 compare 页面（GitHub 提示本地跑 `git diff main...feature/pose-position-prior-constraint`）：  
> `colmap/glomap/compare/main...StonerLing:glomap:feature/pose-position-prior-constraint`

### 6.1 该分支新增/修改的文件（按 diff 统计）

该分支的核心是 **“在 GLOMAP 中引入 Pose Position Prior（相机位置先验）的约束”**，并且在全局定位阶段对先验位置做了“归一化/对齐到 bounding box”的处理。

文件级别的变化（共 20 个文件，约 734 行新增、62 行删除）：

- **新增**
  - `glomap/processors/reconstruction_aligner.{h,cc}`：对齐重建到位置先验（Sim3 + 可选 RANSAC）
- **重点修改**
  - `glomap/io/colmap_converter.{h,cc}`：从 COLMAP DB 读取 pose prior，并把 WGS84 转到 CARTESIAN；把 prior 绑定到 frame/image
  - `glomap/controllers/global_mapper.{h,cc}`：增加 pose prior 相关开关与 BA 选择逻辑（普通 BA vs PosePriorBA）
  - `glomap/estimators/bundle_adjustment.{h,cc}`：新增 `PosePriorBundleAdjuster`（几乎是 COLMAP 的 pose prior BA 逻辑移植）
  - `glomap/estimators/global_positioning.{h,cc}`：引入 bbox 随机初始化范围，并在“使用先验位置”场景下对先验点集做 bbox 对齐/归一化
  - `glomap/types.h`：新增 `PosePriorOptions`
  - `glomap/controllers/option_manager.{h,cc}`：暴露一组 CLI 配置项：`PosePrior.*`

### 6.2 分支新增的 Pose Prior 配置项（CLI/配置文件）

该分支增加了一个新的 options struct：`PosePriorOptions`，并在 option manager 中注册了这些参数：

```text
PosePrior.use_prior_position
PosePrior.prior_position_stddev                      # 例如 "1.0,1.0,1.0"
PosePrior.overwrite_priors_covariance
PosePrior.use_robust_loss_on_prior_position
PosePrior.prior_position_loss_threshold
PosePrior.prior_position_scaled_loss_factor
PosePrior.alignment_ransac_max_error
```

设计意图：

- 允许 **开启/关闭位置先验**
- 允许在 covariance 不可用/不可信时，用 `prior_position_stddev` 覆盖（工程上常见）
- 允许对先验残差使用鲁棒损失并做整体缩放（`ScaledLoss`）
- 支持对齐阶段（Sim3）用 RANSAC 控制最大误差阈值

### 6.3 分支如何“把 pose prior 带进 GLOMAP 计算图”？

#### 6.3.1 DB → GLOMAP：在 `colmap_converter` 中读取/绑定 pose prior

分支把原本的 TODO 落地了：对每个 image 读取 `database.ReadPosePrior(image_id)`，并把 prior 挂到 frame 上：

```text
Frame.pose_prior = prior (std::optional<colmap::PosePrior>)
```

并且把 **WGS84 (lat/lon/alt)** 先转换到 **UTM**，再标记为 **CARTESIAN**，以便后续对齐/残差使用。

同时，它用 prior.position 初始化了 frame 的平移（仅初始化位置，旋转仍由 rotation averaging 给出）。

#### 6.3.2 对齐：新增 `reconstruction_aligner`

新增的 `AlignReconstructionToPosePositionPriors(...)` 会：

- 收集 `src_locations = image.Center()`
- 收集 `tgt_locations = pose_prior.position`
- 用 `EstimateSim3dRobust`（或非鲁棒）估计 Sim3
- 对所有注册相机与点云应用该 Sim3

**注意：它要求 pose prior 必须是 `CARTESIAN`，否则直接报 warning 并返回失败。**

#### 6.3.3 BA：新增 `PosePriorBundleAdjuster`（位置先验残差）

该分支几乎“移植”了 COLMAP 的 pose prior BA 思路：

- 先 `AlignReconstruction(...)`（Sim3）
- 再对重建做 `NormalizeReconstruction(..., fixed_scale=true)`
- 然后对每个 image 添加 **绝对位置先验残差**（协方差加权的 `AbsolutePosePositionPriorCostFunctor`）
- 最后 `DenormalizeReconstruction(...)` 还原坐标系

并提供鲁棒 loss + scaled loss 以增强抗 outlier。

#### 6.3.4 GlobalPositioning：对 prior 位置做 bbox 对齐/归一化

该分支对全局定位阶段还加了一层“归一化”：

- 支持配置 `cameras_bbox / points_bbox`
- 当“不生成随机位置 / 不优化位置”时，会把 prior frame center 点集对齐到 bbox（得到一个 `Sim3 cameras_bbox_from_prior_frame_`）
- 在 `ConvertResults` 里反向应用这个 Sim3，把求解后的 frame/track 再映射回 prior 坐标系

这点与 COLMAP 增量 pose prior BA 的“Normalize + fixed_scale + 加先验残差”思路相呼应：核心是 **控制数值尺度、让优化更稳定**。

### 6.4 与你当前 @work/colmap 内置 GLOMAP（`src/glomap`）的差异对照

你当前的 `@work/colmap/src/glomap` 已经能“读到 pose priors 向量”，但**主要用于重力/旋转相关**，还没有“位置先验约束”这条链路。

#### 6.4.1 当前 @work/colmap 的实际用法（现状）

- **GlobalPipeline 侧**确实读出了 pose priors 并传入 global mapper：
  - `std::vector<PosePrior> pose_priors = database->ReadAllPosePriors();`
  - `global_mapper.Solve(..., pose_priors);`
- **GLOMAP 内部当前主要用 pose priors 的 gravity：**
  - rotation averaging 时通过 `PosePrior.gravity` 做 1-DoF / gravity aligned 处理
  - gravity refinement 也会读取/更新 `PosePrior.gravity`
- **但 position prior 目前没有被用到：**
  - `glomap/io/colmap_converter.cc` 仍是 TODO（没有从 DB 把 prior 绑定到 frame/image）
  - `glomap/estimators/global_positioning.cc` 仍是随机初始化 `RandVector3d(-1,1)` + 常规约束
  - `glomap/estimators/bundle_adjustment.cc` 只有普通 BA，没有 position prior residual

#### 6.4.2 对照表（高信号差异）

```text
能力点                         feature/pose-position-prior-constraint     当前 @work/colmap/src/glomap
----------------------------  ------------------------------------------  -----------------------------------------
DB 中读取 pose prior position  ✅ colmap_converter 读取并绑定到 Frame       ❌ converter 里仍 TODO
WGS84 → CARTESIAN 转换         ✅ WGS84→UTM→CARTESIAN                      ❌（不使用 position，因此未实现）
重建对齐到 prior（Sim3）        ✅ reconstruction_aligner 新增              ❌
BA 中加入位置先验残差            ✅ PosePriorBundleAdjuster（协方差加权）     ❌（只有普通 BA）
全局定位阶段 bbox 归一化         ✅ cameras_bbox_from_prior_frame_           ❌
用 prior 禁止随机初始化          ✅ generate_random_positions = false        ❌（默认随机）
pose prior 在当前版本用途        位置先验为主（position）                   重力为主（gravity，用于旋转平均/精炼）
```

### 6.5 这条分支改动解决了什么问题？（为什么要做）

GLOMAP 社区里关于 pose prior 支持的需求/问题已经存在一段时间（例如：  
`colmap/glomap` 的 [Issue #19](https://github.com/colmap/glomap/issues/19)、[Issue #109](https://github.com/colmap/glomap/issues/109)、[Issue #142](https://github.com/colmap/glomap/issues/142)）。

这条分支的“Add pose position prior constraint feature”本质是在 GLOMAP 补齐：

- **position prior 的读取、坐标转换、绑定与约束**（全链路）
- **对齐 + 归一化**（数值稳定 + 更快收敛）
- **鲁棒损失**（对抗 GNSS outlier）

这也是你在 COLMAP 的 `PosePriorBundleAdjuster` 中已经看到的成熟套路：  
先对齐（Sim3）→ 再归一化（fixed_scale）→ 再加协方差加权残差 → 优化收敛更快更稳。

