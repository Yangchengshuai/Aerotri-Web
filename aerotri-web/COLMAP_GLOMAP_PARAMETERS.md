# COLMAP 3.11 和 GLOMAP 参数使用说明

## 一、可执行文件路径

根据 `task_runner.py` 中的配置：

```python
COLMAP_PATH = "/root/work/colmap3.11/colmap/build/src/colmap/exe/colmap"
GLOMAP_PATH = "/root/work/glomap/build/glomap/glomap"
```

**注意**：运行时需要设置 `LD_LIBRARY_PATH` 环境变量：
```bash
export LD_LIBRARY_PATH=/root/opt/ceres-2.3-cuda/lib:$LD_LIBRARY_PATH
```

## 二、COLMAP 3.11 参数

### 1. Feature Extraction (特征提取)

**命令**：`colmap feature_extractor`

**CUDA GPU 参数**：
- `--SiftExtraction.use_gpu` (默认: 1) - 是否使用 GPU
- `--SiftExtraction.gpu_index` (默认: -1) - GPU 索引

**其他重要参数**：
- `--SiftExtraction.max_image_size` (默认: 3200) - 最大图像尺寸
- `--SiftExtraction.max_num_features` (默认: 8192) - 最大特征点数

**代码中的使用**：
```python
cmd = [
    COLMAP_PATH, "feature_extractor",
    "--database_path", database_path,
    "--image_path", image_path,
    "--ImageReader.single_camera", str(params.get("single_camera", 0)),
    "--ImageReader.camera_model", params.get("camera_model", "SIMPLE_RADIAL"),
    "--SiftExtraction.use_gpu", str(params.get("use_gpu", 1)),
    "--SiftExtraction.gpu_index", str(gpu_index),
    "--SiftExtraction.max_image_size", str(params.get("max_image_size", 2640)),
    "--SiftExtraction.max_num_features", str(params.get("max_num_features", 12000)),
]
```

### 2. Feature Matching (特征匹配)

**命令**：
- `colmap sequential_matcher` - 顺序匹配
- `colmap exhaustive_matcher` - 穷举匹配
- `colmap vocab_tree_matcher` - 词汇树匹配

**CUDA GPU 参数**：
- `--SiftMatching.use_gpu` (默认: 1) - 是否使用 GPU
- `--SiftMatching.gpu_index` (默认: -1) - GPU 索引

**代码中的使用**：
```python
if method == "sequential":
    cmd = [
        COLMAP_PATH, "sequential_matcher",
        "--database_path", database_path,
        "--SequentialMatching.overlap", str(params.get("overlap", 10)),
        "--SiftMatching.use_gpu", str(params.get("use_gpu", 1)),
        "--SiftMatching.gpu_index", str(gpu_index),
    ]
elif method == "exhaustive":
    cmd = [
        COLMAP_PATH, "exhaustive_matcher",
        "--database_path", database_path,
        "--SiftMatching.use_gpu", str(params.get("use_gpu", 1)),
        "--SiftMatching.gpu_index", str(gpu_index),
    ]
else:  # vocab_tree
    cmd = [
        COLMAP_PATH, "vocab_tree_matcher",
        "--database_path", database_path,
        "--SiftMatching.use_gpu", str(params.get("use_gpu", 1)),
        "--SiftMatching.gpu_index", str(gpu_index),
    ]
```

### 3. Mapper (增量式重建)

**命令**：
- `colmap mapper` - 标准增量式重建
- `colmap pose_prior_mapper` - 使用位姿先验的增量式重建

**CUDA GPU 参数**：
- `--Mapper.ba_use_gpu` (默认: 0) - Bundle Adjustment 是否使用 GPU
- `--Mapper.ba_gpu_index` (默认: -1) - Bundle Adjustment GPU 索引

**代码中的使用**：
```python
use_pose_prior = _b(params.get("use_pose_prior", 0), 0) == 1
subcmd = "pose_prior_mapper" if use_pose_prior else "mapper"
cmd = [
    COLMAP_PATH, subcmd,
    "--database_path", database_path,
    "--image_path", image_path,
    "--output_path", output_path,
    "--Mapper.ba_use_gpu", str(_b(params.get("ba_use_gpu", 1), 1)),
    "--Mapper.ba_gpu_index", str(gpu_index),
]
```

## 三、GLOMAP 参数

### Mapper (全局式重建)

**命令**：`glomap mapper`

**CUDA GPU 参数**：
- `--GlobalPositioning.use_gpu` (默认: 1) - 全局定位是否使用 GPU
- `--GlobalPositioning.gpu_index` (默认: -1) - 全局定位 GPU 索引
- `--BundleAdjustment.use_gpu` (默认: 1) - Bundle Adjustment 是否使用 GPU
- `--BundleAdjustment.gpu_index` (默认: -1) - Bundle Adjustment GPU 索引

**其他重要参数**：
- `--output_format` (默认: bin) - 输出格式：`bin` 或 `txt`
- `--GlobalPositioning.max_num_iterations` (默认: 100) - 全局定位最大迭代次数
- `--BundleAdjustment.max_num_iterations` (默认: 200) - Bundle Adjustment 最大迭代次数

**代码中的使用**：
```python
cmd = [
    GLOMAP_PATH, "mapper",
    "--database_path", database_path,
    "--image_path", image_path,
    "--output_path", output_path,
    "--output_format", "bin",
    "--GlobalPositioning.use_gpu", str(_b(params.get("global_positioning_use_gpu", 1), 1)),
    "--GlobalPositioning.gpu_index", str(gpu_index),
    "--BundleAdjustment.use_gpu", str(_b(params.get("bundle_adjustment_use_gpu", 1), 1)),
    "--BundleAdjustment.gpu_index", str(gpu_index),
]
```

## 四、参数变化总结

### 已修复的参数不匹配问题

1. **COLMAP Feature Extraction**：
   - ❌ 旧参数：`--FeatureExtraction.use_gpu`, `--FeatureExtraction.gpu_index`
   - ✅ 新参数：`--SiftExtraction.use_gpu`, `--SiftExtraction.gpu_index`

2. **COLMAP Feature Matching**：
   - ❌ 旧参数：`--FeatureMatching.use_gpu`, `--FeatureMatching.gpu_index`
   - ✅ 新参数：`--SiftMatching.use_gpu`, `--SiftMatching.gpu_index`

3. **GLOMAP Mapper**：
   - ❌ 已移除不存在的参数：
     - `--GlobalPositioning.min_num_images_gpu_solver` (不存在)
     - `--BundleAdjustment.min_num_images_gpu_solver` (不存在)
     - `--PosePrior.use_prior_position` (不存在)

## 五、CUDA GPU 加速使用说明

### COLMAP 3.11

1. **Feature Extraction**：
   - 默认启用 GPU (`--SiftExtraction.use_gpu=1`)
   - 通过 `--SiftExtraction.gpu_index` 指定 GPU 设备

2. **Feature Matching**：
   - 默认启用 GPU (`--SiftMatching.use_gpu=1`)
   - 通过 `--SiftMatching.gpu_index` 指定 GPU 设备

3. **Bundle Adjustment**：
   - **默认禁用 GPU** (`--Mapper.ba_use_gpu=0`)
   - 需要显式设置 `--Mapper.ba_use_gpu=1` 来启用 GPU 加速
   - 通过 `--Mapper.ba_gpu_index` 指定 GPU 设备

### GLOMAP

1. **Global Positioning**：
   - 默认启用 GPU (`--GlobalPositioning.use_gpu=1`)
   - 通过 `--GlobalPositioning.gpu_index` 指定 GPU 设备

2. **Bundle Adjustment**：
   - 默认启用 GPU (`--BundleAdjustment.use_gpu=1`)
   - 通过 `--BundleAdjustment.gpu_index` 指定 GPU 设备

### 重要提示

1. **COLMAP Bundle Adjustment 默认不使用 GPU**：
   - 在 `task_runner.py` 中，代码默认设置 `ba_use_gpu=1`，这会覆盖 COLMAP 的默认值
   - 如果希望使用 CPU，需要显式设置 `ba_use_gpu=0`

2. **GPU 索引**：
   - `-1` 表示自动选择或使用默认 GPU
   - 非负整数表示使用指定的 GPU 设备索引（如 0, 1, 2...）

3. **运行时环境**：
   - 确保设置了正确的 `LD_LIBRARY_PATH` 以加载 Ceres 和其他依赖库
   - 确保 CUDA 驱动和运行时库已正确安装

## 六、查看完整参数列表

### COLMAP
```bash
export LD_LIBRARY_PATH=/root/opt/ceres-2.3-cuda/lib:$LD_LIBRARY_PATH
/root/work/colmap3.11/colmap/build/src/colmap/exe/colmap feature_extractor --help
/root/work/colmap3.11/colmap/build/src/colmap/exe/colmap sequential_matcher --help
/root/work/colmap3.11/colmap/build/src/colmap/exe/colmap mapper --help
```

### GLOMAP
```bash
export LD_LIBRARY_PATH=/root/opt/ceres-2.3-cuda/lib:$LD_LIBRARY_PATH
/root/work/glomap/build/glomap/glomap mapper --help
```

