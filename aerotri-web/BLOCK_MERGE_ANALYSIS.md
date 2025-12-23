# 分块空三合并逻辑分析

本文档对比分析两个项目中分块空三（Block SfM）的合并策略：

1. **InstantSfM** (`block_sfm.py`) - 使用 Sim3（相似变换）对齐
2. **AeroTri-Web** (`sfm_merge_service.py`) - 使用刚性变换（Rigid Transform）对齐

---

## 一、InstantSfM 的合并逻辑 (`block_sfm.py`)

### 1.1 整体流程

```python
# 主流程：merge_blocks()
1. 以第一个块作为参考坐标系
2. 逐个合并后续块：
   - 找到重叠图像（common images）
   - 提取重叠图像的相机中心
   - 使用 Sim3 对齐（包含尺度、旋转、平移）
   - 应用变换到当前块的所有图像和点
   - 合并到全局结果中
```

### 1.2 Sim3 对齐算法 (`align_sim3`)

**核心思想**：估计相似变换 `T: P_target = s * R * P_source + t`

**步骤**：

1. **中心化点云**
   ```python
   mu_m = np.mean(model_points, axis=0)  # 目标点云中心
   mu_d = np.mean(data_points, axis=0)   # 源点云中心
   m_centered = model_points - mu_m
   d_centered = data_points - mu_d
   ```

2. **估计旋转矩阵 R**
   ```python
   H = d_centered.T @ m_centered  # 协方差矩阵
   U, S, Vt = np.linalg.svd(H)
   R = Vt.T @ U.T
   # 确保 det(R) = 1（右手坐标系）
   ```

3. **估计尺度 s**
   ```python
   # 方法1：基于奇异值
   s = np.trace(np.diag(S)) / ss_d
   
   # 方法2：基于最小二乘（最终使用）
   d_rotated = d_centered @ R.T
   s = np.sum(m_centered * d_rotated) / np.sum(d_rotated**2)
   ```

4. **估计平移 t**
   ```python
   t = mu_m - s * (mu_d @ R.T)
   ```

**特点**：
- ✅ 支持**尺度缩放**（适用于不同块可能有不同尺度的情况）
- ✅ 基于**相机中心**对齐（几何直观）
- ✅ 使用 SVD 分解保证最优旋转

### 1.3 应用变换 (`apply_sim3`)

**对图像姿态的变换**：
```python
# 相机中心变换
C_old = -R_old.T @ t_old  # 从 world2cam 提取相机中心
C_new = s * (R @ C_old) + t

# 更新 world2cam
R_new = R_old @ R.T
t_new = -R_new @ C_new
```

**对三维点的变换**：
```python
tracks.xyzs = s * (tracks.xyzs @ R.T) + t
```

### 1.4 合并策略

```python
# 重叠图像处理
- 如果图像已存在于全局结果中：保留全局结果中的姿态
- 如果图像是新的：添加并应用变换后的姿态

# 三维点处理
- 所有点都应用 Sim3 变换
- 直接追加到全局点云（不进行去重）
```

---

## 二、AeroTri-Web 的合并逻辑 (`sfm_merge_service.py`)

### 2.1 整体流程

```python
# 主流程：merge_partitions()
1. 读取所有分块的结果（支持 .bin 和 .txt 格式）
2. 以第一个分块作为参考
3. 逐个合并后续分块：
   - 找到与前一个分块的重叠图像
   - 提取重叠图像的姿态（旋转+平移）
   - 使用刚性变换对齐（仅旋转+平移，无尺度）
   - 应用变换到当前分块的所有图像和点
   - 合并到全局结果中
```

### 2.2 刚性变换对齐 (`estimate_rigid_transform`)

**核心思想**：估计刚性变换 `T: P_target = R * P_source + t`（无尺度）

**步骤**：

1. **提取相机中心**
   ```python
   # 从姿态矩阵提取相机中心
   source_centers = [-R.T @ t for R, t in source_poses]
   target_centers = [-R.T @ t for R, t in target_poses]
   ```

2. **中心化**
   ```python
   source_mean = source_centers.mean(axis=0)
   target_mean = target_centers.mean(axis=0)
   source_centered = source_centers - source_mean
   target_centered = target_centers - target_mean
   ```

3. **SVD 分解估计旋转**
   ```python
   H = source_centered.T @ target_centered
   U, S, Vt = np.linalg.svd(H)
   R_transform = Vt.T @ U.T
   # 确保 det(R) = 1
   ```

4. **估计平移**
   ```python
   t_transform = target_mean - R_transform @ source_mean
   ```

**特点**：
- ✅ **无尺度变换**（假设所有分块在同一尺度下）
- ✅ 基于**相机中心**对齐
- ✅ 使用 SVD 分解（与 InstantSfM 类似）

### 2.3 应用变换

**对图像姿态的变换**：
```python
# 从四元数转换为旋转矩阵
R = quaternion_to_rotation_matrix(qw, qx, qy, qz)
t = np.array([tx, ty, tz])

# 应用刚性变换
R_new = R_transform @ R
t_new = R_transform @ t + t_transform

# 转换回四元数
qw_new, qx_new, qy_new, qz_new = rotation_matrix_to_quaternion(R_new)
```

**对三维点的变换**：
```python
pt_3d_transformed = R_transform @ pt_3d + t_transform
```

### 2.4 合并策略

```python
# 重叠图像处理（rigid_keep_one 策略）
- 如果图像已存在于全局结果中：
  * 使用**后一个分块**的姿态（应用变换后）
  * 更新全局结果中的姿态
- 如果图像是新的：添加并应用变换后的姿态

# 三维点处理
- 所有点都应用刚性变换
- 使用新的点 ID（避免冲突）
- 注意：track 中的 image_id 需要重新映射（当前实现中简化处理）
```

---

## 三、两种方法的对比

### 3.1 变换类型对比

| 特性 | InstantSfM (Sim3) | AeroTri-Web (Rigid) |
|------|-------------------|---------------------|
| **变换类型** | 相似变换（7 DOF） | 刚性变换（6 DOF） |
| **包含尺度** | ✅ 是 | ❌ 否 |
| **适用场景** | 不同块可能有尺度差异 | 所有块在同一尺度下 |
| **计算复杂度** | 稍高（需要估计尺度） | 较低 |

### 3.2 对齐基准对比

| 特性 | InstantSfM | AeroTri-Web |
|------|------------|-------------|
| **对齐基准** | 相机中心 | 相机中心 |
| **重叠要求** | ≥ 3 个共同图像 | ≥ 3 个共同图像 |
| **对齐方法** | SVD + 尺度估计 | SVD |

### 3.3 合并策略对比

| 特性 | InstantSfM | AeroTri-Web |
|------|-----------|-------------|
| **重叠图像处理** | 保留全局结果中的姿态 | 使用后一个分块的姿态（变换后） |
| **三维点处理** | 直接追加（不重新分配 ID） | 重新分配 ID |
| **Track 更新** | 更新观测的 image_idx | 简化处理（track 中的 image_id 需要重新映射） |

### 3.4 优缺点分析

#### InstantSfM (Sim3) 的优点：
1. ✅ **支持尺度差异**：适用于不同块可能有不同尺度的情况
2. ✅ **更灵活**：能处理尺度不一致的重建结果
3. ✅ **理论更完善**：Sim3 是相似变换的标准形式

#### InstantSfM (Sim3) 的缺点：
1. ❌ **计算稍复杂**：需要估计尺度参数
2. ❌ **可能引入尺度误差**：如果尺度估计不准确，会累积误差

#### AeroTri-Web (Rigid) 的优点：
1. ✅ **计算简单**：不需要估计尺度
2. ✅ **假设合理**：如果所有分块使用相同的相机内参，尺度应该一致
3. ✅ **实现清晰**：代码逻辑更直观

#### AeroTri-Web (Rigid) 的缺点：
1. ❌ **不处理尺度差异**：如果分块间存在尺度不一致，会导致对齐误差
2. ❌ **Track 映射不完整**：当前实现中，track 的 image_id 重新映射是简化处理

---

## 四、实际应用建议

### 4.1 选择 Sim3 的场景

- 不同分块可能使用不同的相机内参
- 分块重建时可能存在尺度不一致
- 需要更鲁棒的对齐方法

### 4.2 选择 Rigid 的场景

- 所有分块使用相同的相机内参
- 分块重建在统一的尺度下进行
- 追求计算效率和实现简单

### 4.3 改进建议

#### 对于 AeroTri-Web：
1. **完善 Track 映射**：正确处理 track 中的 image_id 重新映射
2. **可选 Sim3 支持**：添加可选的 Sim3 对齐策略，用于处理尺度不一致的情况
3. **重叠图像策略**：提供更多选择（如：保留第一个、保留后一个、平均等）

#### 对于 InstantSfM：
1. **重叠图像策略**：当前实现保留全局结果中的姿态，可以考虑使用后一个分块的姿态（如果质量更好）
2. **点云去重**：考虑对重叠区域的三维点进行去重或融合

---

## 五、代码位置参考

### InstantSfM
- **合并函数**：`work/instantsfm/instantsfm/scripts/block_sfm.py::merge_blocks()`
- **Sim3 对齐**：`work/instantsfm/instantsfm/scripts/block_sfm.py::align_sim3()`
- **应用变换**：`work/instantsfm/instantsfm/scripts/block_sfm.py::apply_sim3()`

### AeroTri-Web
- **合并函数**：`backend/app/services/sfm_merge_service.py::merge_partitions()`
- **刚性变换**：`backend/app/services/sfm_merge_service.py::estimate_rigid_transform()`
- **调用位置**：`backend/app/services/task_runner.py::_run_merge_only()`

---

## 六、总结

两种方法都使用**基于重叠图像的对齐策略**，主要区别在于：

1. **InstantSfM** 使用 **Sim3（相似变换）**，支持尺度缩放，更灵活但计算稍复杂
2. **AeroTri-Web** 使用 **刚性变换**，假设尺度一致，计算简单但不够灵活

在实际应用中，如果所有分块使用相同的相机内参且在统一尺度下重建，**刚性变换**通常足够；如果存在尺度不一致的风险，**Sim3** 更可靠。

两种方法都基于**相机中心**进行对齐，这是合理的，因为相机中心是重建结果中最稳定的几何特征。


