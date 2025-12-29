# 合并功能修复总结

## 修复日期
2025-12-29

## 问题描述
在使用GLOMAP进行空三时，开启分区模式后，各分区成功空三，但在合并时报错：
- 前端页面报错：`cannot fit 'int' into an index-sized integer`

## 根本原因分析

### 1. COLMAP cameras.bin 格式理解错误 ⚠️ **关键问题**
- **问题**：代码错误地尝试从文件读取 `num_params` 字段
- **实际情况**：COLMAP的 `cameras.bin` 格式**不包含** `num_params` 字段
- **正确格式**：参数数量由相机模型类型决定，不同模型有固定数量的参数
- **影响**：导致读取 `num_params` 时读取到了错误的字节（实际上是第一个参数值），产生巨大的无效数值

### 2. 变量作用域错误
- **问题**：`partition_camera_id_to_global` 和 `partition_image_id_to_global` 在使用前未定义
- **位置**：在合并循环中，这些变量在第658行和680行被使用，但直到第693行和684行才定义
- **影响**：导致 `NameError` 或使用未初始化的变量

### 3. 重叠图像映射缺失
- **问题**：处理重叠图像时，未将其添加到 `partition_image_id_to_global` 映射
- **影响**：后续处理points时无法正确映射重叠图像的ID

## 修复内容

### 1. 修复 cameras.bin 读取逻辑 (`sfm_merge_service.py` 第103-151行)

**修复前**：
```python
# 错误：尝试从文件读取 num_params
num_params = struct.unpack("<Q", f.read(8))[0]
params = struct.unpack(f"<{num_params}d", f.read(8 * num_params))
```

**修复后**：
```python
# 根据相机模型确定参数数量
MODEL_PARAM_COUNTS = {
    0: 3,   # SIMPLE_PINHOLE
    1: 4,   # PINHOLE
    2: 4,   # SIMPLE_RADIAL
    3: 5,   # RADIAL
    4: 8,   # OPENCV
    5: 8,   # OPENCV_FISHEYE
    6: 12,  # FULL_OPENCV
    7: 4,   # FOV
    8: 4,   # SIMPLE_RADIAL_FISHEYE
    9: 5,   # RADIAL_FISHEYE
    10: 12, # THIN_PRISM_FISHEYE
}
num_params = MODEL_PARAM_COUNTS.get(model, 4)
params_bytes = f.read(8 * int(num_params))
params = struct.unpack(f"<{int(num_params)}d", params_bytes)
```

### 2. 修复变量作用域问题 (`sfm_merge_service.py` 第621-644行)

**修复前**：
- 变量在使用后才定义

**修复后**：
- 在处理图像**之前**初始化所有映射字典
- `partition_camera_id_to_global` 在第623行初始化
- `partition_image_id_to_global` 在第644行初始化

### 3. 完善重叠图像映射 (`sfm_merge_service.py` 第680-681行)

**修复后**：
```python
# 处理重叠图像时，添加到映射
partition_image_id_to_global[img_data["image_id"]] = merged_images[img_name]["image_id"]
```

### 4. 改进类型检查和转换 (`sfm_merge_service.py` 第744-757行, 第872-881行)

**改进**：
- 添加 `point2d_idx` 和 `image_id` 的类型转换
- 添加范围检查和负数检查
- 确保写入时使用正确的整数类型

## 测试验证

### 手动测试结果
- ✅ 成功合并2个分区
- ✅ 生成441张图像、2个相机、535,200个3D点
- ✅ 所有输出文件正确生成：
  - `cameras.bin` (200 bytes)
  - `images.bin` (44,990 bytes)
  - `points3D.bin` (51,881,960 bytes)
  - 对应的 `.txt` 文件

### 测试脚本
创建了 `test_merge_manual.py` 用于手动测试合并功能，可以用于：
- 调试合并问题
- 验证修复效果
- 测试新的数据集

## 修改的文件

1. `/root/work/aerotri-web/backend/app/services/sfm_merge_service.py`
   - 修复 `read_cameras_bin()` 方法
   - 修复变量作用域问题
   - 完善重叠图像映射
   - 改进类型检查和转换

2. `/root/work/aerotri-web/backend/test_merge_manual.py` (新增)
   - 手动测试脚本

## 代码调用路径

### 后端合并流程
1. `task_runner.py::_run_partitioned_sfm()` (第1764行)
   - 运行分区空三流程
   - 完成后设置 `current_stage = "partitions_completed"`

2. `task_runner.py::_run_merge_only()` (第1932行)
   - 检查分区是否全部完成
   - 调用 `SFMMergeService.merge_partitions()`

3. `sfm_merge_service.py::merge_partitions()` (第430行)
   - 读取所有分区的空三结果
   - 合并图像、相机和3D点
   - 写入合并后的结果

## 注意事项

1. **相机模型支持**：当前支持COLMAP标准的所有11种相机模型
2. **ID溢出检查**：添加了32位和64位整数溢出检查
3. **错误处理**：改进了错误消息，便于调试
4. **兼容性**：同时生成 `.bin` 和 `.txt` 格式，确保兼容性

## 后续建议

1. ✅ 所有修复已完成并测试通过
2. 可以重新运行前端合并任务验证
3. 建议在生产环境测试更多数据集
4. 考虑添加单元测试覆盖合并逻辑



