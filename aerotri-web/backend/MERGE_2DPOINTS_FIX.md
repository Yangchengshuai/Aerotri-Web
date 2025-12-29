# 合并后2D Points数据修复总结

## 问题描述
合并后的空三结果中，`images.bin`文件的所有图像2D points数据都是0，导致GLOMAP优化时崩溃（SIGSEGV）。

## 根本原因
合并逻辑在写入`images.bin`时，跳过了2D points数据，只写入了0：
```python
# Write empty 2D points (simplified)
f.write(struct.pack("<Q", 0))
```

但GLOMAP在`AddTrackToProblem()`时需要访问这些2D points数据，导致段错误。

## 临时解决方案

### 修复脚本
创建了 `fix_merged_images_2dpoints.py` 脚本，可以从原始分区重建2D points数据：

1. **从原始分区读取2D points**
   - 遍历所有分区（partition_0, partition_1, ...）
   - 从每个分区的`images.bin`中读取完整的2D points数据
   - 2D points格式：`(x, y, point3d_id)`

2. **修复合并后的images.bin**
   - 读取合并后的`images.bin`
   - 为每个图像从原始分区恢复2D points数据
   - 写入修复后的`images.bin`

3. **输出到新目录**
   - 修复后的文件保存在 `merged/sparse/0_fixed/`
   - 包含完整的2D points数据

### 使用方法
```bash
cd /root/work/aerotri-web/backend
python3 fix_merged_images_2dpoints.py
```

修复后的目录：`/root/work/aerotri-web/data/outputs/b156bd90-2725-409d-862a-166c0cb0096a/merged/sparse/0_fixed/`

## 永久解决方案（需要实现）

### 修改合并逻辑
需要在`sfm_merge_service.py`中修改合并逻辑：

1. **读取时包含2D points**
   ```python
   images = SFMMergeService.read_images_bin(images_bin, include_points2d=True)
   ```

2. **合并时保留2D points**
   - 从每个分区读取2D points数据
   - 在合并图像时保留这些数据
   - 更新point3d_id引用（因为point ID会重新映射）

3. **写入时包含2D points**
   ```python
   # Write 2D points
   points2d = img_data.get("points2d", [])
   f.write(struct.pack("<Q", len(points2d)))
   for x, y, point3d_id in points2d:
       f.write(struct.pack("<2d", x, y))
       f.write(struct.pack("<Q", point3d_id))
   ```

### 注意事项
- **point3d_id映射**：合并时point ID会重新映射，需要更新2D points中的point3d_id引用
- **重叠图像**：如果图像在多个分区中出现，需要合并2D points数据
- **性能**：读取和写入大量2D points数据可能较慢

## 当前状态

### 已完成的修复
1. ✅ 修复了`cameras.bin`写入格式（移除num_params字段）
2. ✅ 添加了路径自动检测（支持merged/sparse/0）
3. ✅ 创建了临时修复脚本（从原始分区重建2D points）

### 待完成的改进
1. ⏳ 完善合并逻辑，在合并时正确保留2D points数据
2. ⏳ 处理point3d_id的重新映射
3. ⏳ 测试GLOMAP优化是否能正常工作

## 测试验证

### 修复脚本验证
- ✅ 成功从2个分区读取2D points数据
- ✅ 为441个图像恢复了9,703,596个2D points
- ✅ 修复后的images.bin格式正确

### GLOMAP优化测试
- ⏳ 需要在实际环境中测试（当前有库依赖问题）
- ⏳ 使用修复后的目录：`merged/sparse/0_fixed/`

## 使用建议

### 临时方案
1. 运行合并任务
2. 运行修复脚本：`python3 fix_merged_images_2dpoints.py`
3. 使用修复后的目录进行GLOMAP优化：
   - 设置`input_colmap_path`为`merged/sparse/0_fixed/`

### 永久方案（待实现）
1. 完善合并逻辑，自动保留2D points数据
2. 合并后直接可以使用，无需额外修复步骤



