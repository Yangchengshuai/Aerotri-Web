# 3DGS 参数默认值更新总结

## 更新目标
将工具中 3D GS 设置参数的默认值与 gaussian-splatting 源码默认值保持一致。

## 源码默认值参考
参考文件：`/root/work/gs_workspace/gaussian-splatting/arguments/__init__.py` 和 `train.py`

### ModelParams 默认值
- `sh_degree = 3`
- `data_device = "cuda"`
- `_resolution = -1` (使用原始分辨率)
- `_white_background = False`

### OptimizationParams 默认值
- `iterations = 30_000`
- `position_lr_init = 0.00016`
- `position_lr_final = 0.0000016`
- `position_lr_delay_mult = 0.01`
- `position_lr_max_steps = 30_000`
- `feature_lr = 0.0025`
- `opacity_lr = 0.025`
- `scaling_lr = 0.005`
- `rotation_lr = 0.001`
- `percent_dense = 0.01`
- `lambda_dssim = 0.2`
- `densification_interval = 100`
- `opacity_reset_interval = 3000`
- `densify_from_iter = 500`
- `densify_until_iter = 15_000`
- `densify_grad_threshold = 0.0002`
- `random_background = False`

### train.py 默认值
- `test_iterations = [7_000, 30_000]`
- `save_iterations = [7_000, 30_000]`
- `checkpoint_iterations = []`
- `quiet = False` (action="store_true")
- `disable_viewer = False` (action="store_true")

## 更新内容

### 1. 前端更新 (`frontend/src/components/GaussianSplattingPanel.vue`)

#### 更新前的默认值
```typescript
iterations: 7000,
resolution: 2,
data_device: 'cpu',
sh_degree: 3,
// 其他优化参数都是 undefined
```

#### 更新后的默认值
```typescript
iterations: 30000,  // 从 7000 改为 30000
resolution: -1,  // 从 2 改为 -1 (使用原始分辨率)
data_device: 'cuda',  // 从 'cpu' 改为 'cuda'
sh_degree: 3,  // 保持不变

// 所有优化参数都设置了默认值
position_lr_init: 0.00016,
position_lr_final: 0.0000016,
position_lr_delay_mult: 0.01,
position_lr_max_steps: 30000,
feature_lr: 0.0025,
opacity_lr: 0.025,
scaling_lr: 0.005,
rotation_lr: 0.001,
lambda_dssim: 0.2,
percent_dense: 0.01,
densification_interval: 100,
opacity_reset_interval: 3000,
densify_from_iter: 500,
densify_until_iter: 15000,
densify_grad_threshold: 0.0002,

// 高级参数
test_iterations: [7000, 30000],  // 新增
save_iterations: [7000, 30000],  // 新增
checkpoint_iterations: [],  // 新增
```

#### 代码修复
- 修复了参数过滤逻辑，正确处理数组类型参数
- 修复了 TypeScript 类型检查错误

### 2. 后端更新 (`backend/app/schemas.py`)

#### 更新内容
- 在 `GSTrainParams` 类的文档字符串中添加了默认值说明
- 为每个参数添加了注释，说明源码中的默认值
- 参数类型保持不变（都是 Optional），因为前端会发送所有定义的参数

### 3. 测试脚本更新 (`backend/test_gs_manual.py`)

#### 更新内容
- 将 `--resolution` 参数从 `2` 改为 `-1`，与源码默认值一致

## 主要变更对比

| 参数 | 更新前 | 更新后 | 源码默认值 |
|------|--------|--------|-----------|
| iterations | 7000 | 30000 | 30000 |
| resolution | 2 | -1 | -1 |
| data_device | 'cpu' | 'cuda' | 'cuda' |
| position_lr_init | undefined | 0.00016 | 0.00016 |
| position_lr_final | undefined | 0.0000016 | 0.0000016 |
| feature_lr | undefined | 0.0025 | 0.0025 |
| opacity_lr | undefined | 0.025 | 0.025 |
| ... | ... | ... | ... |

## 验证

### 前端验证
- ✅ 所有参数默认值已更新
- ✅ TypeScript 类型检查通过
- ✅ 参数过滤逻辑正确处理数组类型

### 后端验证
- ✅ schemas.py 添加了默认值注释
- ✅ 参数类型定义正确（Optional）
- ✅ 测试脚本已更新

## 注意事项

1. **resolution 参数**: 
   - 源码默认值是 `-1`，表示使用原始分辨率
   - 之前使用的 `2` 可能是一个缩放因子，现在改为 `-1` 以匹配源码

2. **data_device 参数**:
   - 源码默认值是 `"cuda"`
   - 如果系统没有 GPU 或需要 CPU 训练，用户可以在前端手动修改为 `'cpu'`

3. **数组参数**:
   - `test_iterations`, `save_iterations`, `checkpoint_iterations` 现在是数组类型
   - 前端代码已正确处理空数组的过滤

4. **向后兼容性**:
   - 所有参数都是 Optional，如果前端不发送某个参数，后端不会报错
   - 但建议前端始终发送所有参数，以确保使用正确的默认值

## 后续建议

1. 考虑在前端 UI 中添加 `test_iterations`, `save_iterations`, `checkpoint_iterations` 的输入控件
2. 考虑添加参数预设（如 "快速训练"、"高质量训练" 等）
3. 考虑添加参数验证，确保用户输入的值在合理范围内
