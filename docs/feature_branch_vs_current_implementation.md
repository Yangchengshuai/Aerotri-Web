# Feature Branch vs Current Implementation Comparison

## 编译成功
Feature 分支的 glomap 已成功编译（支持 CUDA），位于：
- `/root/work/feature/glomap/build_feature/glomap/glomap`

## 关键差异分析

### 1. AddPosePositionPriorConstraints 实现

**Feature 分支** (`/root/work/feature/glomap/glomap/estimators/bundle_adjustment.cc:506-531`):
```cpp
void PosePriorBundleAdjuster::AddPosePositionPriorConstraints(
    const std::unordered_map<image_t, colmap::PosePrior>& pose_priors,
    const Sim3d& normalized_from_metric,
    std::unordered_map<image_t, Image>& images) {
  for (auto& [image_id, image] : images) {
    const colmap::PosePrior& pose_prior = pose_priors.at(image_id);
    ceres::CostFunction* cost_function = colmap::CovarianceWeightedCostFunctor<
        colmap::AbsolutePosePositionPriorCostFunctor>::
        Create(pose_prior.position_covariance,  // ✅ 直接使用原始协方差
               normalized_from_metric * pose_prior.position);  // ✅ 只归一化位置
    // ...
  }
}
```

**当前实现** (`/root/work/colmap/src/glomap/estimators/bundle_adjustment.cc:710-777`):
```cpp
void PosePriorBundleAdjuster::AddPosePositionPriorConstraints(...) {
  // ✅ 已修复：直接使用原始协方差，不进行归一化变换
  const Eigen::Matrix3d& cov = prior.position_covariance;
  const Eigen::Vector3d normalized_position = normalized_from_metric * prior.position;
  // ✅ 已添加：协方差有效性检查
  if (det <= 0.0 || trace <= 0.0 || !cov.allFinite()) {
    // skip invalid covariance
  }
}
```

**结论**：当前实现已与 feature 分支对齐，都直接使用原始协方差矩阵。

### 2. Solve 函数流程

**Feature 分支** (`/root/work/feature/glomap/glomap/estimators/bundle_adjustment.cc:375-456`):
```cpp
bool PosePriorBundleAdjuster::Solve(...) {
  // 1. 提取 pose priors
  pose_priors_ = ExtractsValidPosePriorsFromImgaes(images);
  
  // 2. 对齐重建到 pose priors（使用 RANSAC）
  const bool use_prior_position = AlignReconstruction(pose_priors_, images, tracks);
  
  // 3. 添加点约束
  AddPointToCameraConstraints(...);
  
  // 4. 归一化（fixed_scale=true）
  if (use_prior_position) {
    normalized_from_metric = NormalizeReconstruction(
        rigs, cameras, frames, images, tracks, /*fixed_scale=*/true);
    AddPosePositionPriorConstraints(pose_priors_, normalized_from_metric, images);
  }
  
  // 5. 求解器配置
  options_.solver_options.linear_solver_type = ceres::SPARSE_SCHUR;
  options_.solver_options.preconditioner_type = ceres::CLUSTER_TRIDIAGONAL;
  
  // 6. 求解
  ceres::Solve(...);
  
  // 7. 反归一化
  if (use_prior_position) {
    DenormalizeReconstruction(normalized_from_metric, images, tracks);
  }
  
  // 8. 检查结果（如果失败，直接返回 false，不 fallback）
  if (!summary.IsSolutionUsable()) {
    return false;
  }
}
```

**当前实现** (`/root/work/colmap/src/glomap/estimators/bundle_adjustment.cc:450-640`):
```cpp
bool PosePriorBundleAdjuster::Solve(...) {
  // 1. 归一化（fixed_scale=true）✅
  normalized_from_metric = NormalizeReconstruction(
      rigs, cameras, frames, images, tracks, /*fixed_scale=*/true);
  
  // 2. 添加点约束 ✅
  AddPointToCameraConstraints(...);
  
  // 3. 添加 pose prior 约束 ✅
  AddPosePositionPriorConstraints(normalized_from_metric, frames, images);
  
  // 4. 求解器配置 ✅
  options_.solver_options.linear_solver_type = ceres::SPARSE_SCHUR;
  options_.solver_options.preconditioner_type = ceres::CLUSTER_TRIDIAGONAL;
  
  // 5. 求解
  ceres::Solve(...);
  
  // 6. 如果失败，反归一化并 fallback 到普通 BA ✅
  if (!summary.IsSolutionUsable()) {
    DenormalizeReconstruction(...);
    return BundleAdjuster::Solve(...);  // Fallback
  }
  
  // 7. 反归一化 ✅
  DenormalizeReconstruction(...);
}
```

**关键差异**：
1. **对齐步骤**：Feature 分支在归一化**之前**进行对齐（`AlignReconstruction`），当前实现**没有**显式的对齐步骤
2. **失败处理**：Feature 分支失败时直接返回 false，当前实现会 fallback 到普通 BA

### 3. 对齐（Alignment）逻辑

**Feature 分支** (`/root/work/feature/glomap/glomap/estimators/bundle_adjustment.cc:461-504`):
- 使用 `AlignReconstructionToPosePositionPriors` 进行 Sim3 对齐
- 使用 RANSAC 进行鲁棒对齐（自动计算 max_error 基于协方差的 median RMS variance）
- 对齐在归一化之前进行

**当前实现**：
- 没有显式的对齐步骤
- 对齐可能在 GP 阶段完成，或者在 BA 阶段隐式完成

### 4. 数据提取方式

**Feature 分支**：
```cpp
std::unordered_map<image_t, colmap::PosePrior> ExtractsValidPosePriorsFromImgaes(
    const std::unordered_map<image_t, Image>& images) {
  // 直接从 images 中提取 frame_ptr->pose_prior
}
```

**当前实现**：
```cpp
std::unordered_map<frame_t, PosePrior> ExtractFramePositionPriors(
    const std::unordered_map<image_t, Image>& images,
    const std::vector<colmap::PosePrior>& pose_priors,
    const PosePriorOptions& options) {
  // 从数据库读取的 pose_priors vector 中提取，并处理 NaN 协方差
}
```

## 对齐（Alignment）实现对比

**Feature 分支**：
- 使用独立的 `AlignReconstructionToPosePositionPriors` 函数
- 自动计算 RANSAC max_error（基于协方差的 median RMS variance）
- 对齐在归一化之前进行

**当前实现** (`/root/work/colmap/src/glomap/estimators/bundle_adjustment.cc:648-697`):
- 在 `PosePriorBundleAdjuster::AlignReconstruction` 中实现
- 支持手动设置 `alignment_ransac_max_error`，如果未设置则使用非鲁棒估计
- ✅ 对齐也在归一化之前进行（第 521 行调用，第 530 行归一化）

**结论**：当前实现已有对齐逻辑，但可能缺少自动计算 RANSAC max_error 的功能。

## 可能的问题根源

1. **RANSAC max_error 计算**：Feature 分支自动基于协方差计算 max_error，当前实现需要手动设置或使用非鲁棒估计
2. **Ceres 求解器配置**：两者都使用 `SPARSE_SCHUR` + `CLUSTER_TRIDIAGONAL`，配置一致
3. **协方差处理**：✅ 已修复，都直接使用原始协方差

## 建议的修复

1. **添加对齐步骤**：在 `PosePriorBundleAdjuster::Solve` 开始时，添加 `AlignReconstruction` 调用
2. **对齐顺序**：确保对齐在归一化之前进行
3. **检查 GP 阶段对齐**：确认 GP 阶段是否已经进行了对齐，如果是，BA 阶段可能不需要再次对齐

