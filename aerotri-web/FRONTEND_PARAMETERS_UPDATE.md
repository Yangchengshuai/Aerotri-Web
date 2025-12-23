# 前端参数更新说明

## 更新内容

根据后端修复后的参数，前端已同步更新以下内容：

### 1. 类型定义更新 (`src/types/index.ts`)

**移除的参数**：
- `GlomapMapperParams.global_positioning_min_num_images_gpu_solver` - 此参数在 GLOMAP 中不存在
- `GlomapMapperParams.bundle_adjustment_min_num_images_gpu_solver` - 此参数在 GLOMAP 中不存在

**更新后的 `GlomapMapperParams` 接口**：
```typescript
export interface GlomapMapperParams {
  use_pose_prior?: boolean
  global_positioning_use_gpu: boolean
  global_positioning_gpu_index: number
  bundle_adjustment_use_gpu: boolean
  bundle_adjustment_gpu_index: number
}
```

### 2. 参数表单更新 (`src/components/ParameterForm.vue`)

**移除的表单项**：
- "GPU Solver 最小图像数" (`global_positioning_min_num_images_gpu_solver`)
- 对应的 `BundleAdjustment` 最小图像数参数

**更新后的 GLOMAP 参数表单**：
- ✅ GlobalPositioning GPU 开关
- ✅ BundleAdjustment GPU 开关
- ❌ ~~GPU Solver 最小图像数~~ (已移除)

### 3. 默认参数更新

**更新后的默认 GLOMAP 参数**：
```typescript
const defaultGlomapParams: GlomapMapperParams = {
  use_pose_prior: false,
  global_positioning_use_gpu: true,
  global_positioning_gpu_index: 0,
  bundle_adjustment_use_gpu: true,
  bundle_adjustment_gpu_index: 0,
}
```

## 参数对应关系

### COLMAP 参数

前端参数 → 后端命令行参数：
- `feature_params.use_gpu` → `--SiftExtraction.use_gpu`
- `feature_params.gpu_index` → `--SiftExtraction.gpu_index`
- `matching_params.use_gpu` → `--SiftMatching.use_gpu`
- `matching_params.gpu_index` → `--SiftMatching.gpu_index`
- `mapper_params.ba_use_gpu` → `--Mapper.ba_use_gpu`
- `mapper_params.ba_gpu_index` → `--Mapper.ba_gpu_index`
- `mapper_params.use_pose_prior` → 选择 `pose_prior_mapper` 或 `mapper` 命令

### GLOMAP 参数

前端参数 → 后端命令行参数：
- `mapper_params.global_positioning_use_gpu` → `--GlobalPositioning.use_gpu`
- `mapper_params.global_positioning_gpu_index` → `--GlobalPositioning.gpu_index`
- `mapper_params.bundle_adjustment_use_gpu` → `--BundleAdjustment.use_gpu`
- `mapper_params.bundle_adjustment_gpu_index` → `--BundleAdjustment.gpu_index`
- `mapper_params.use_pose_prior` → 已移除（GLOMAP 不支持此参数）

## 注意事项

1. **GPU 索引**：
   - 前端传递的 `gpu_index` 会直接传递给后端
   - 后端会将其传递给 COLMAP/GLOMAP 的相应参数
   - `-1` 表示自动选择 GPU

2. **参数验证**：
   - 前端表单已移除不存在的参数
   - 后端已修复参数名称以匹配实际可执行文件
   - 前后端参数现在完全一致

3. **向后兼容**：
   - 如果数据库中仍存在旧的参数（包含 `min_num_images_gpu_solver`），它们会被忽略
   - 前端默认参数已更新，新创建的任务将使用正确的参数

## 测试建议

1. **创建新任务**：
   - 使用 GLOMAP 算法创建新任务
   - 验证参数表单中不再显示 "GPU Solver 最小图像数"
   - 验证任务可以正常启动

2. **参数传递**：
   - 检查后端日志，确认参数名称正确
   - 验证 GPU 加速功能正常工作

3. **旧任务兼容性**：
   - 如果存在使用旧参数的任务，验证它们仍能正常工作
   - 旧参数会被忽略，使用默认值

