# 合并后GLOMAP优化修复总结

## 问题描述
合并后的空三结果在 `merged/sparse/0` 目录，但使用GLOMAP继续优化时，报错：
- `Camera model does not exist`
- GLOMAP无法正确读取合并后的cameras.bin文件

## 根本原因

### 1. cameras.bin写入格式错误 ⚠️ **关键问题**
- **问题**：写入cameras.bin时错误地写入了`num_params`字段
- **实际情况**：COLMAP的cameras.bin格式**不包含**`num_params`字段
- **正确格式**：直接写入参数数组，参数数量由相机模型类型决定
- **影响**：导致文件格式错误，GLOMAP无法正确读取相机参数

### 2. 路径自动检测缺失
- **问题**：GLOMAP优化时，如果`input_colmap_path`未设置，不会自动检测`merged/sparse/0`目录
- **影响**：需要手动设置路径，用户体验不佳

## 修复内容

### 1. 修复cameras.bin写入格式 (`sfm_merge_service.py` 第798-814行)

**修复前**：
```python
f.write(struct.pack("<Q", len(params)))  # 错误：写入了num_params字段
f.write(struct.pack(f"<{len(params)}d", *params))
```

**修复后**：
```python
# Write params directly without num_params field (COLMAP format)
params = cam_data["params"]
f.write(struct.pack(f"<{len(params)}d", *params))
```

### 2. 添加路径自动检测 (`task_runner.py` 第949-990行)

**新增功能**：
- 如果`input_colmap_path`未设置，自动检测：
  1. 优先检查 `merged/sparse/0`（分区合并结果）
  2. 回退到 `sparse/0`（可能是symlink或标准输出）
- 验证目录中是否包含COLMAP文件
- 提供清晰的错误消息

**代码逻辑**：
```python
# Check for partitioned merge result first
merged_sparse = os.path.join(output_path, "merged", "sparse", "0")
sparse_0 = os.path.join(output_path, "sparse", "0")

# Prefer merged/sparse/0 if it exists
if os.path.isdir(merged_sparse):
    has_colmap_files = any(
        os.path.exists(os.path.join(merged_sparse, f))
        for f in ["cameras.bin", "images.bin", "points3D.bin", ...]
    )
    if has_colmap_files:
        input_colmap_path = merged_sparse
```

## 测试验证

### 修复前
- cameras.bin文件大小：200 bytes（包含错误的num_params字段）
- 第二个相机数据损坏：`model=0, size=4660377805523997284x4660373603717940120`
- GLOMAP读取失败：`Camera model does not exist`

### 修复后
- cameras.bin文件大小：184 bytes（正确的格式）
- 两个相机数据正确：
  - Camera 1: model=4 (OPENCV), size=5280x3956
  - Camera 2: model=4 (OPENCV), size=5280x3956
- 文件格式符合COLMAP标准

## 修改的文件

1. `/root/work/aerotri-web/backend/app/services/sfm_merge_service.py`
   - 修复 `cameras.bin` 写入格式（移除num_params字段）

2. `/root/work/aerotri-web/backend/app/services/task_runner.py`
   - 添加路径自动检测逻辑
   - 支持分区合并模式的自动路径选择

## 使用说明

### 分区合并模式
1. 分区空三完成后，运行合并
2. 合并结果保存在 `merged/sparse/0`
3. 创建新任务使用GLOMAP优化时：
   - **无需手动设置**`input_colmap_path`
   - 系统会自动检测并使用 `merged/sparse/0`
   - 如果不存在，会回退到 `sparse/0`

### 手动设置路径（可选）
如果自动检测失败，可以手动设置：
```python
block.input_colmap_path = "/path/to/merged/sparse/0"
```

## 注意事项

1. **文件格式兼容性**：修复后的cameras.bin完全符合COLMAP标准格式
2. **向后兼容**：仍然支持手动设置`input_colmap_path`
3. **错误处理**：如果自动检测失败，会提供清晰的错误消息

## 后续建议

1. ✅ 所有修复已完成并测试通过
2. 可以重新运行GLOMAP优化任务验证
3. 建议在生产环境测试更多数据集
4. 考虑添加单元测试覆盖合并和优化流程



