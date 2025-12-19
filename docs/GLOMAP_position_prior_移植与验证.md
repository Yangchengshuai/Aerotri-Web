## GLOMAP 移植 Position Prior（WGS84→UTM、GP 初始化/归一化、BA 先验残差）开发记录与验证

### 1. 背景与目标

本次开发目标：将 COLMAP 增量 mapper 中“位置先验（position prior）”的核心思路，以**最小侵入**的方式移植到 `src/glomap`，让 GLOMAP 在全局定位（Global Positioning, GP）和全局 BA 阶段真正利用 GPS/RTK 等位置先验，从而提升：

- **收敛速度**：更好的初值 + 更稳定的尺度/平移；
- **稳定性**：减少随机初始化带来的发散/局部最优；
- **可控性**：可配置 robust loss、先验权重、对齐 RANSAC 阈值等。

### 2. 功能总览（你现在拿到的能力）

- **WGS84 → UTM（CARTESIAN）转换**：将 EXIF/GPS 的经纬高先验统一转换到 UTM 米制坐标，便于 GP/BA 使用。
- **GP 使用 position prior 初始化**：
  - 将 frame 的平移按先验位置初始化（保持旋转不变）；
  - **禁用随机初始化**；
  - 通过 bounding box 归一化（对相机中心/点云）提升数值稳定性，最终再反变换回原坐标系。
- **BA 引入 position prior 约束**：
  - 在 BA 前先做 **Sim3 对齐**（可选 RANSAC）将当前重建对齐到先验坐标系；
  - BA 内加入 **position prior residual**（可选 robust loss + scaled loss）；
  - BA 内部做 fixed-scale normalize，提升求解稳定性，最后再 denormalize 回米制坐标。
- **CLI 开关**：默认不启用，显式 `--PosePrior.use_prior_position 1` 才生效。

### 3. 数据流与执行链路（ASCII）

```text
EXIF/GPS (WGS84: lat, lon, alt)
    |
    |  (COLMAP image_reader 写入 database.pose_priors)
    v
database.db : pose_priors (WGS84)
    |
    | glomap mapper: ReadAllPosePriors()
    v
GLOMAP::GlobalMapper::Solve(..., pose_priors)
    |
    | if PosePrior.use_prior_position:
    |   1) WGS84 -> UTM (meters), set coordinate_system=CARTESIAN
    |   2) GP: 初始化 frame translation（由 prior position 推导 t）
    |   3) GP: 禁用随机初始化 + bbox 归一化 + 求解 + 反变换
    |   4) BA: 选择 PosePriorBundleAdjuster
    |      - Sim3 对齐(可 RANSAC)
    |      - fixed-scale normalize
    |      - reprojection + position prior residual
    |      - solve + denormalize
    v
output_path/0/{cameras,frames,images,points3D,rigs}.{bin/txt}
```

### 4. 关键实现点（设计说明）

#### 4.1 坐标系统统一：WGS84 → UTM

```text
WGS84 (lat, lon, alt)
   |
   | GPSTransform::EllipsoidToUTM(...)
   v
UTM (E, N, H)  [meters]
   |
   v
PosePrior.coordinate_system = CARTESIAN
```

实现要点：
- 仅对 `prior.HasPosition()==true` 且 `coordinate_system==WGS84` 的先验转换；
- 输出仍写回同一个 `pose_priors` vector（后续 GP/BA 使用同一份数据）。

#### 4.2 GP：用 position prior 初始化 + bbox 归一化

核心思想：GP 里相机位姿优化通常非常依赖初值。启用先验时：
- 把 frame 的平移设置成“使相机中心等于 prior.position”的形式；
- 关闭随机初始化；
- 对“中心点集合”做 bounding-box 对齐（将点云/相机中心拉到一个较小、稳定的尺度范围），求解后再反变换回先验坐标系。

#### 4.3 BA：Sim3 对齐 + position prior residual

位置先验 BA 的关键步骤：

1) **对齐（Sim3）**  
将当前重建（frame centers + tracks）对齐到 prior positions：
- 有 `alignment_ransac_max_error>0` 时使用 `EstimateSim3dRobust`（RANSAC）
- 否则使用 `EstimateSim3d`（非鲁棒）

2) **fixed-scale normalize**  
BA 内做归一化以改善数值尺度，但固定尺度（`fixed_scale=true`），避免破坏米制尺度。

3) **先验残差**  
对每个 frame 的 ref image 位置先验添加约束，形式可理解为：

\[
r = \mathbf{L}^{-1}(\mathbf{C}-\mathbf{C}_{prior})
\]

其中 \(\mathbf{C}\) 为相机中心，\(\mathbf{L}\) 来自先验协方差（或由 `prior_position_stddev` 覆盖生成）。

4) **robust loss（可选）**  
通过 CauchyLoss（再叠加 ScaledLoss）降低异常 prior 对整体优化的破坏。

### 5. 具体代码文件与改动点（以最终集成状态为准）

说明：当前工作区 `git diff` 没有显示 `src/glomap/*` 的未提交修改（说明这些 glomap 改动已在此前合入/提交到当前代码基线）。因此下面按**“最终集成后的关键文件/关键职责”**来整理。

#### 5.1 `colmap/src/glomap/sfm/global_mapper.cc` / `.h`

- **新增/集成**：
  - `ConvertPosePriorsWgs84ToUtm(...)`：WGS84→UTM 转换并打日志；
  - `ExtractFramePositionPriors(...)`：将 `PosePrior(corr_data_id=image_id)` 映射到 `frame_id`（仅 ref image）；
  - `InitTranslationsFromPositionPriors(...)`：GP 前初始化 translation（保持旋转不变）；
  - 启用先验时：
    - `gp_engine.GetOptions().generate_random_positions = false;`
    - 跳过 GP 阶段的 `NormalizeReconstruction(...)`（避免破坏米制尺度）；
    - BA 阶段选择 `PosePriorBundleAdjuster` 作为引擎。

#### 5.2 `colmap/src/glomap/estimators/global_positioning.h` / `.cc`

- **新增/集成 Options**：
  - `generate_random_positions / generate_random_points / cameras_bbox / points_bbox`
- **新增/集成逻辑**：
  - `AlignPointsToBoundingBox(...)`：将点集对齐到 bounding box，得到 `Sim3` 变换；
  - 初始化随机位置关闭时，用当前 centers 做 bbox 对齐；
  - `ConvertBackResults(...)`：求解后用 `Inverse(cameras_bbox_from_prior_frame_)` 把 frame/tracks 反变换回先验坐标系，并将“center 表示”还原为 COLMAP 的 `RigFromWorld().translation` 表达。

#### 5.3 `colmap/src/glomap/processors/reconstruction_normalizer.cc`

- `NormalizeReconstruction(...)` 增强：
  - 支持 `fixed_scale`（在 BA 中固定尺度，仅做平移归一化）；
  - 使用分位数（`p0/p1`）构建鲁棒 bbox，降低离群点影响。

#### 5.4 `colmap/src/glomap/estimators/bundle_adjustment.h` / `.cc`

- **新增类**：`PosePriorBundleAdjuster`
- **关键步骤**：
  - 提取 frame position priors（可覆盖协方差）；
  - `AlignReconstruction(...)`：Sim3（可 RANSAC）对齐 frames/tracks；
  - `NormalizeReconstruction(..., fixed_scale=true)`；
  - `AddPosePositionPriorConstraints(...)`：向 Ceres Problem 增加 prior residual；
  - Ceres GPU 求解配置输出（dense + sparse/cuDSS）。

#### 5.5 `colmap/src/glomap/types.h`

- **新增结构体**：`PosePriorOptions`
  - `use_prior_position`
  - `prior_position_stddev`
  - `overwrite_position_priors_covariance`
  - `use_robust_loss_on_prior_position`
  - `prior_position_loss_threshold`
  - `prior_position_scaled_loss_factor`
  - `alignment_ransac_max_error`

#### 5.6 `colmap/src/glomap/controllers/option_manager.cc` / `.h`

- **新增 CLI 注册**（与 `glomap mapper -h` 对齐）：
  - `PosePrior.use_prior_position`
  - `PosePrior.prior_position_stddev`
  - `PosePrior.overwrite_priors_covariance`
  - `PosePrior.use_robust_loss_on_prior_position`
  - `PosePrior.prior_position_loss_threshold`
  - `PosePrior.prior_position_scaled_loss_factor`
  - `PosePrior.alignment_ransac_max_error`

### 6. 使用方式（命令行）

#### 6.1 关键开关（默认关闭）

- **启用位置先验**：`--PosePrior.use_prior_position 1`

推荐组合（示例）：

```bash
mkdir -p /root/data/test_output/result/glomap_poseprior_sparse

/root/work/colmap/build_poseprior_ceres23_cudss_nocgal/src/glomap/glomap mapper \
  --log_to_stderr 1 --log_level 0 \
  --database_path /root/data/test_output/result/database.db \
  --image_path /root/data/test \
  --output_path /root/data/test_output/result/glomap_poseprior_sparse \
  --output_format txt \
  --PosePrior.use_prior_position 1 \
  --PosePrior.use_robust_loss_on_prior_position 1 \
  --PosePrior.alignment_ransac_max_error 10 \
  2>&1 | tee /root/data/test_output/result/glomap_poseprior.log
```

注意：
- **必须保证 `--output_path` 父目录存在**（否则最后写盘会触发 `std::filesystem::filesystem_error`）。

### 7. 测试验证（本次实际跑通的证据）

#### 7.1 数据与产物

- **图片**：`/root/data/test`（76 张 DJI JPG）
- **数据库**：`/root/data/test_output/result/database.db`
  - 已包含：`images=76, keypoints=76, matches=405, two_view_geometries=405, pose_priors=76`
- **输出模型**：`/root/data/test_output/result/glomap_poseprior_sparse/0/*.bin`
- **日志**：`/root/data/test_output/result/glomap_poseprior.log`

#### 7.2 关键日志证据（直接证明“链路生效”）

以下三行是本次验证的核心证据（行号来自 `glomap_poseprior.log`）：

- **WGS84→UTM 转换发生**（line 81）
  - `Converted 76 pose prior positions WGS84->UTM`
- **GP 使用先验初始化位置**（line 167）
  - `Initialized 76 frame translations from position priors`
- **BA 使用 PosePriorBundleAdjuster**（line 178 起多次出现）
  - `GLOMAP: PosePriorBundleAdjustment using Ceres CUDA ...`

#### 7.3 输出目录检查

已成功写出：

```text
/root/data/test_output/result/glomap_poseprior_sparse/0/
  cameras.bin
  frames.bin
  images.bin
  points3D.bin
  rigs.bin
```

### 8. 过程问题与修复记录

#### 8.1 输出路径不存在导致崩溃

第一次运行因 `--output_path` 的父目录不存在，最终写盘阶段异常退出：

```text
filesystem error: cannot create directory: No such file or directory [.../glomap_poseprior_sparse/0]
```

解决：在运行前 `mkdir -p /root/data/test_output/result/glomap_poseprior_sparse`。

失败日志已保留：
- ` /root/data/test_output/result/glomap_poseprior.fail.log`

### 9. 后续可选优化

- **更强的 prior 质量控制**：基于先验协方差/RTK 指标/速度约束过滤异常 priors。
- **支持 gravity prior**：在 rotation averaging 或 gravity refinement 阶段融合重力先验（如果数据具备）。
- **更细粒度的 prior 使用策略**：只对部分 frame 使用 priors（例如每 N 帧、或 RTK 有效帧）。


