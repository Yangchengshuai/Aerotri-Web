# 合并逻辑分析报告

## 1. 各分区空三结果检查

### Partition 0
- **3D点数量**: 269,975个
- **图像数量**: 270张
- **相机数量**: 1个
- **相机参数**: 
  - fx=3710.46, fy=3708.55
  - k1=-0.101865, k2=-0.017146
  - 分辨率: 5280x3956

### Partition 1
- **3D点数量**: 265,225个
- **图像数量**: 251张
- **相机数量**: 1个
- **相机参数**:
  - fx=3710.39, fy=3708.16
  - k1=-0.102296, k2=-0.016267
  - 分辨率: 5280x3956

**结论**: 各分区都有3D点，空三结果正常。

## 2. 相机参数不一致问题

### 问题描述
两个分区估计的相机参数有微小差异：
- fx差异: 0.07 (3710.46 vs 3710.39)
- fy差异: 0.39 (3708.55 vs 3708.16)
- k1差异: 0.000431
- k2差异: 0.000879

### 原因分析
1. **独立估计**: 每个分区独立进行空三，相机参数是独立估计的
2. **数据子集差异**: 不同分区使用的图像子集不同，导致估计结果略有差异
3. **数值精度**: 优化过程中的数值精度和收敛条件可能导致微小差异

### 当前合并逻辑
代码在 `sfm_merge_service.py` 第693-696行通过**完全相等**比较来判断是否是同一个相机：
```python
if (merged_cam_data["model"] == cam_data["model"] and
    merged_cam_data["width"] == cam_data["width"] and
    merged_cam_data["height"] == cam_data["height"] and
    merged_cam_data["params"] == cam_data["params"]):
```

**问题**: 由于参数有微小差异，会被认为是不同的相机，导致创建多个相机实例。

### 解决方案

#### 方案1: 容差比较（推荐）
对于相同model、width、height的相机，使用容差比较参数：
```python
def camera_params_equal(cam1, cam2, tolerance=1e-3):
    """比较两个相机参数是否相等（考虑容差）"""
    if (cam1["model"] != cam2["model"] or
        cam1["width"] != cam2["width"] or
        cam1["height"] != cam2["height"]):
        return False
    
    params1 = cam1["params"]
    params2 = cam2["params"]
    if len(params1) != len(params2):
        return False
    
    for p1, p2 in zip(params1, params2):
        if abs(p1 - p2) > tolerance:
            return False
    return True
```

#### 方案2: 平均参数
对于相同相机，合并时使用平均参数：
```python
# 如果找到相同相机，使用平均参数
if found_existing:
    # 平均参数
    merged_cam_data["params"] = [
        (p1 + p2) / 2 for p1, p2 in zip(merged_cam_data["params"], cam_data["params"])
    ]
```

#### 方案3: 使用参考分区的参数
对于重叠图像，使用参考分区（partition 0）的相机参数。

## 3. 重叠图像处理

### 当前逻辑
代码第712行：对于重叠图像，保留**后一个分区**的位姿（`keep_one`策略）。

### 问题
1. **位姿合并**: ✅ 正确 - 只保留一个位姿
2. **2D points合并**: ⚠️ 需要检查 - 应该合并两个分区的2D points
3. **3D点合并**: ⚠️ 需要检查 - 重叠区域的3D点可能重复

## 4. 3D点合并检查

### 预期结果
- Partition 0: 269,975个点
- Partition 1: 265,225个点
- **预期合并后**: 535,200个点（如果无重叠）或更少（如果有重叠）

### 实际检查
需要验证：
1. 重叠区域的3D点是否被正确去重？
2. 非重叠区域的3D点是否都被保留？
3. 3D点的track是否正确更新？

## 5. 修复建议

### 优先级1: 修复相机参数比较
使用容差比较，避免创建重复相机。

### 优先级2: 验证3D点合并
检查合并后的3D点数量是否合理，track是否正确。

### 优先级3: 完善2D points合并
确保重叠图像的2D points正确合并，point3d_id引用正确。


