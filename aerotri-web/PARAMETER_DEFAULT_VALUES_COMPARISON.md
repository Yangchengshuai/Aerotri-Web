# 参数默认值对比报告

## 概述
本文档对比了前端、后端和 COLMAP/GLOMAP 源代码中的默认参数值，以检查它们是否一致。

## 1. 特征提取参数 (Feature Extraction)

### 1.1 max_image_size (最大图像尺寸)

| 来源 | 默认值 | 位置 |
|------|--------|------|
| **COLMAP 源代码** | `3200` | `colmap/feature/extractor.h:51` |
| **前端** | `2640` | `frontend/src/components/ParameterForm.vue:240` |
| **后端** | `2640` | `backend/app/services/task_runner.py:519` |

**状态**: ❌ **不一致**
- 前端和后端使用 `2640`，但 COLMAP 源代码默认是 `3200`
- 建议：统一使用 COLMAP 的默认值 `3200`，或明确说明为什么使用 `2640`

### 1.2 max_num_features (最大特征数)

| 来源 | 默认值 | 位置 |
|------|--------|------|
| **COLMAP 源代码** | `8192` | `colmap/feature/sift.h:39` |
| **前端** | `12000` | `frontend/src/components/ParameterForm.vue:241` |
| **后端** | `12000` | `backend/app/services/task_runner.py:520` |

**状态**: ❌ **不一致**
- 前端和后端使用 `12000`，但 COLMAP 源代码默认是 `8192`
- 建议：统一使用 COLMAP 的默认值 `8192`，或明确说明为什么使用 `12000`

### 1.3 camera_model (相机模型)

| 来源 | 默认值 | 位置 |
|------|--------|------|
| **COLMAP 源代码** | `"SIMPLE_RADIAL"` | `colmap/controllers/image_reader.h:63` |
| **前端** | `'SIMPLE_RADIAL'` | `frontend/src/components/ParameterForm.vue:242` |
| **后端** | `"SIMPLE_RADIAL"` | `backend/app/services/task_runner.py:516` |

**状态**: ✅ **一致**

### 1.4 single_camera (单相机模式)

| 来源 | 默认值 | 位置 |
|------|--------|------|
| **COLMAP 源代码** | `false` | `colmap/controllers/image_reader.h:70` |
| **前端** | `true` | `frontend/src/components/ParameterForm.vue:243` |
| **后端** | `1` (即 `true`) | `backend/app/services/task_runner.py:515` |

**状态**: ❌ **不一致**
- 前端和后端使用 `true`，但 COLMAP 源代码默认是 `false`
- 建议：统一使用 COLMAP 的默认值 `false`，或明确说明为什么使用 `true`

## 2. 特征匹配参数 (Feature Matching)

### 2.1 overlap (序列匹配重叠窗口)

| 来源 | 默认值 | 位置 |
|------|--------|------|
| **COLMAP 源代码** | `10` | `colmap/feature/pairing.h:88` |
| **前端** | `10` | `frontend/src/components/ParameterForm.vue:248` |
| **后端** | `20` | `backend/app/services/task_runner.py:542` |

**状态**: ❌ **不一致**
- 前端使用 `10`（与 COLMAP 一致），但后端使用 `20`
- 建议：统一使用 COLMAP 的默认值 `10`，或明确说明为什么后端使用 `20`

## 3. GLOMAP Mapper 参数

### 3.1 global_positioning_min_num_images_gpu_solver

| 来源 | 默认值 | 位置 |
|------|--------|------|
| **COLMAP 源代码** | `50` | `colmap/estimators/bundle_adjustment.h:157` |
| **前端** | `50` | `frontend/src/components/ParameterForm.vue:256` |
| **后端** | `50` | `backend/app/services/task_runner.py:609` |

**状态**: ✅ **一致**

### 3.2 bundle_adjustment_min_num_images_gpu_solver

| 来源 | 默认值 | 位置 |
|------|--------|------|
| **COLMAP 源代码** | `50` | `colmap/estimators/bundle_adjustment.h:157` |
| **前端** | `50` | `frontend/src/components/ParameterForm.vue:259` |
| **后端** | `50` | `backend/app/services/task_runner.py:613` |

**状态**: ✅ **一致**

## 4. 总结

### 一致的参数 ✅
- `camera_model`: 所有地方都使用 `"SIMPLE_RADIAL"`
- `global_positioning_min_num_images_gpu_solver`: 所有地方都使用 `50`
- `bundle_adjustment_min_num_images_gpu_solver`: 所有地方都使用 `50`

### 不一致的参数 ❌
1. **max_image_size**: 
   - COLMAP: `3200`
   - 前端/后端: `2640`
   
2. **max_num_features**: 
   - COLMAP: `8192`
   - 前端/后端: `12000`
   
3. **single_camera**: 
   - COLMAP: `false`
   - 前端/后端: `true`
   
4. **overlap**: 
   - COLMAP: `10`
   - 前端: `10` ✅
   - 后端: `20` ❌

## 5. 建议

### 5.1 立即修复
1. **修复后端 overlap 默认值**：将 `task_runner.py:542` 中的 `overlap` 默认值从 `20` 改为 `10`，与 COLMAP 和前端保持一致。

### 5.2 需要决策的参数
以下参数前端/后端与 COLMAP 源代码不一致，需要决定是否修改：

1. **max_image_size (2640 vs 3200)**
   - 如果 `2640` 是经过测试验证的更优值，可以保留，但建议在代码注释中说明原因
   - 如果希望与 COLMAP 保持一致，应改为 `3200`

2. **max_num_features (12000 vs 8192)**
   - 如果 `12000` 是经过测试验证的更优值，可以保留，但建议在代码注释中说明原因
   - 如果希望与 COLMAP 保持一致，应改为 `8192`

3. **single_camera (true vs false)**
   - 如果 `true` 是业务需求（所有图像使用相同相机参数），可以保留，但建议在代码注释中说明原因
   - 如果希望与 COLMAP 保持一致，应改为 `false`

### 5.3 代码位置

需要修改的文件：

1. **后端** (`backend/app/services/task_runner.py`):
   - 第 519 行: `max_image_size` 默认值
   - 第 520 行: `max_num_features` 默认值
   - 第 515 行: `single_camera` 默认值
   - 第 542 行: `overlap` 默认值（**必须修复**）

2. **前端** (`frontend/src/components/ParameterForm.vue`):
   - 第 240 行: `max_image_size` 默认值
   - 第 241 行: `max_num_features` 默认值
   - 第 243 行: `single_camera` 默认值

## 6. 参考代码位置

### COLMAP 源代码
- `colmap/feature/extractor.h:51` - `max_image_size = 3200`
- `colmap/feature/sift.h:39` - `max_num_features = 8192`
- `colmap/controllers/image_reader.h:63` - `camera_model = "SIMPLE_RADIAL"`
- `colmap/controllers/image_reader.h:70` - `single_camera = false`
- `colmap/feature/pairing.h:88` - `overlap = 10`
- `colmap/estimators/bundle_adjustment.h:157` - `min_num_images_gpu_solver = 50`

### 前端代码
- `frontend/src/components/ParameterForm.vue:237-279` - 所有默认参数定义

### 后端代码
- `backend/app/services/task_runner.py:499-523` - 特征提取参数
- `backend/app/services/task_runner.py:525-561` - 特征匹配参数
- `backend/app/services/task_runner.py:587-616` - GLOMAP mapper 参数

