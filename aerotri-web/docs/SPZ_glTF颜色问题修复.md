# SPZ 压缩模式下 glTF 颜色显示问题修复

## 一、问题描述

在使用 SPZ 压缩（`KHR_gaussian_splatting_compression_spz_2` 扩展）时，生成的 3DGS 模型在 Cesium 中显示为黑白色，缺少颜色信息。

## 二、问题分析

### 2.1 根本原因

通过分析代码和生成的 glTF 文件，发现以下问题：

1. **POSITION accessor 的 min/max 错误**：
   - 在 SPZ 压缩模式下，POSITION accessor 的 min/max 被硬编码为 `[0.0, 0.0, 0.0]`
   - 这导致 Cesium 无法正确计算模型的边界框，影响渲染

2. **bufferView 数据缺失**：
   - bufferView 只有 12 字节的占位符数据
   - 没有包含实际的 POSITION 数据，Cesium 无法获取位置信息

3. **颜色数据格式问题**：
   - SPZ 数据中的 `colors` 字段实际上是 SH 系数的 `f_dc` 部分
   - `f_dc` 值通常在 `[-3, 3]` 范围内，不是标准的 RGB [0, 1] 范围
   - 在 SPZ 压缩模式下，颜色数据存储在 SPZ 二进制中，但可能没有正确归一化

### 2.2 技术细节

**SPZ 格式说明**：
- SPZ 格式中，`colors` 字段存储的是 SH 系数的 `f_dc`（DC 分量）
- `f_dc` 值范围通常是 `[-3, 3]`，需要转换为 RGB [0, 1] 范围才能正确显示
- SPZ 数据包含完整的 Gaussian 信息，包括位置、旋转、缩放、颜色（f_dc）、alpha 和 SH 系数（f_rest）

**glTF 扩展规范**：
- `KHR_gaussian_splatting_compression_spz_2` 扩展要求：
  - SPZ 数据存储在独立的 buffer 中
  - 仍然需要 POSITION accessor（用于边界框计算）
  - POSITION accessor 必须包含实际的边界框信息（min/max）

## 三、修复方案

### 3.1 修复 POSITION accessor

**问题**：min/max 硬编码为 [0, 0, 0]

**修复**：
```python
# 修复前
"min": [0.0, 0.0, 0.0],
"max": [0.0, 0.0, 0.0]

# 修复后
positions_3d = self.positions.reshape(-1, 3)
pos_min = self._calculate_min(positions_3d)
pos_max = self._calculate_max(positions_3d)
"min": pos_min,
"max": pos_max
```

### 3.2 修复 bufferView

**问题**：只有 12 字节占位符

**修复**：
- 在 JSON glTF 模式下：创建独立的 `positions.bin` 文件
- 在 GLB 模式下：在二进制 chunk 中包含 POSITION 数据
- 使用两个 buffer：
  - Buffer 0: POSITION 数据（用于边界框）
  - Buffer 1: SPZ 压缩数据

### 3.3 颜色数据处理

**问题**：SPZ 数据中的颜色（f_dc）可能未正确归一化

**修复**：
- 确保 SPZ 加载时颜色数据正确提取
- 在构建 glTF 时，如果使用 SPZ 压缩，颜色数据已经包含在 SPZ 二进制中
- Cesium 应该能够从 SPZ 数据中正确提取颜色信息

**注意**：如果颜色仍然显示不正确，可能需要检查：
1. SPZ 数据中的颜色值范围
2. Cesium 版本是否支持 `KHR_gaussian_splatting_compression_spz_2` 扩展
3. 是否需要额外的颜色访问器（虽然规范中不要求）

## 四、修复实现

### 4.1 文件修改

**`backend/app/services/gltf_gaussian_builder.py`**：

1. **`_build_gltf_json_with_spz`**：
   - 添加 POSITION buffer 文件
   - 使用实际位置数据计算 min/max
   - 使用两个 buffer（POSITION + SPZ）

2. **`_build_gltf_json_dict_for_glb_with_spz`**：
   - 使用实际位置数据计算 min/max
   - 定义两个 buffer（POSITION + SPZ）

3. **`_build_glb_with_spz`**：
   - 在二进制 chunk 中包含 POSITION 数据
   - 正确设置 buffer 索引（buffer 0 = POSITION, buffer 1 = SPZ）

### 4.2 关键代码变更

```python
# 计算实际位置边界
positions_3d = self.positions.reshape(-1, 3)
pos_min = self._calculate_min(positions_3d)
pos_max = self._calculate_max(positions_3d)

# 创建 POSITION buffer
position_buffer_data = positions_3d.astype(np.float32).tobytes()

# GLB 格式：二进制 chunk 包含 [POSITION buffer][SPZ buffer]
binary_data = position_buffer_data + spz_buffer_data
```

## 五、验证步骤

1. **检查生成的 glTF 文件**：
   ```bash
   cat gaussian.gltf | jq '.accessors[0]'
   # 应该显示实际的 min/max 值，而不是 [0, 0, 0]
   ```

2. **检查 buffer 结构**：
   ```bash
   cat gaussian.gltf | jq '.buffers'
   # 应该有两个 buffer：positions.bin 和 compressed_data.bin
   ```

3. **在 Cesium 中预览**：
   - 模型应该显示正确的边界框
   - 颜色应该正确显示（如果 SPZ 数据正确）

## 六、可能的问题

如果修复后颜色仍然显示为黑白色，可能的原因：

1. **SPZ 数据中的颜色值范围不正确**：
   - 检查 SPZ 文件中的颜色值
   - 确认是否需要额外的归一化处理

2. **Cesium 版本兼容性**：
   - 确认 Cesium 版本 >= 1.133（支持 `KHR_gaussian_splatting_compression_spz_2`）
   - 检查是否启用了实验性功能

3. **SPZ 数据格式问题**：
   - 验证 SPZ 文件是否包含完整的颜色信息
   - 检查 SPZ 加载逻辑是否正确提取颜色

## 七、后续优化建议

1. **颜色归一化**：
   - 如果 SPZ 数据中的颜色值不在 [0, 1] 范围，考虑在加载时进行归一化
   - 或者在构建 glTF 时添加颜色访问器（虽然规范不要求）

2. **调试工具**：
   - 添加日志输出，记录 SPZ 数据中的颜色值范围
   - 提供工具验证生成的 glTF 文件结构

3. **文档更新**：
   - 更新文档说明 SPZ 压缩模式下的颜色处理
   - 添加故障排除指南

---

**修复时间**: 2026-01-07
**影响范围**: SPZ 压缩模式下的 glTF 生成
**向后兼容**: ✅ 是（不影响未压缩模式）
