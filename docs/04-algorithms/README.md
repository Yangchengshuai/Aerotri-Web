# 04-algorithms

AeroTri-Web 支持的摄影测量算法详细说明。

## 目录

- [算法概述](#算法概述)
- [COLMAP](#colmap)
- [GLOMAP](#glomap)
- [InstantSfM](#instantsfm)
- [OpenMVG](#openmvg)
- [OpenMVS](#openmvs)
- [3D Gaussian Splatting](#d-gaussian-splatting)
- [算法选择指南](#算法选择指南)

---

## 算法概述

### SfM 算法对比

| 算法 | 类型 | 速度 | GPU需求 | 规模 | 推荐场景 |
|------|------|------|---------|------|----------|
| **COLMAP** | 增量式 | 中 | 推荐 | 小-中 | 常规摄影测量 |
| **GLOMAP** | 全局式 | 快 | 推荐 | 大 | 大规模航拍 |
| **InstantSfM** | 全局式 | 很快 | 必需 | 小-中 | 实时可视化 |
| **OpenMVG** | 全局式 | 中 | 否 | 小-中 | CPU环境 |

### 密集重建对比

| 算法 | 输入 | 输出 | 质量 | 速度 |
|------|------|------|------|------|
| **OpenMVS** | 稀疏点云 | 密集点云+网格 | 高 | 中 |
| **3DGS** | 稀疏点云 | 3D高斯点云 | 很高 | 慢（训练）|

---

## COLMAP

### 简介

COLMAP 是一个通用的 Structure-from-Motion 和 Multi-View Stereo 管道，支持增量式重建。

### 特点

- ✅ 支持多种相机模型
- ✅ GPS prior 支持
- ✅ 成熟稳定
- ✅ 社区活跃

### 处理流程

1. **特征提取**
   - SIFT 特征检测
   - EXIF 信息提取
   - 相机模型估计

2. **特征匹配**
   - 顺序匹配（Sequential）
   - 空间匹配（Spatial）
   - 词汇树匹配（Vocabulary Tree）

3. **增量重建**
   - 初始化双视图
   - 逐步注册新图像
   - 局部 Bundle Adjustment
   - 全局 Bundle Adjustment

### 关键参数

#### 特征提取 (Feature Extraction)

```yaml
feature_params:
  # 相机模型
  camera_model: "SIMPLE_PINHOLE"  # SIMPLE_PINHOLE, PINHOLE, OPENCV, etc.

  # 图像处理
  max_image_size: 2048           # 最大图像尺寸（像素）
  max_num_features: 8192         # 每张图像最大特征数

  # 相机设置
  single_camera: true            # 单相机假设（航拍通常为true）
  camera_params:                 # 相机内参优先级
    - "EXIF"                     # 1. 优先使用EXIF
    - "PRIOR"                    # 2. 使用先验值

  # GPU设置
  use_gpu: true                  # 使用GPU加速
  gpu_index: 0                   # GPU编号
```

**参数说明**：

| 参数 | 效果 | 调优建议 |
|------|------|----------|
| `camera_model` | 影响后续3DGS | 3DGS需要PINHOLE/SIMPLE_PINHOLE |
| `max_image_size` | 提高可提升质量，但增加内存 | 高分辨率图像可增大到4096 |
| `max_num_features` | 特征点越多，重建越完整 | 复杂场景可增大到16384 |
| `single_camera` | 航拍为true，多相机为false | 根据实际采集方式设置 |

#### 特征匹配 (Feature Matching)

```yaml
matching_params:
  # 匹配方法
  method: "sequential"           # sequential, spatial, exhaustive, vocab_tree

  # 顺序匹配
  overlap: 10                    # 连续重叠图像数量
  loop_detection: false          # 循环检测

  # 空间匹配
  spatial_max_num_neighbors: 20  # 最大邻居数
  spatial_ignore_z: true         # 忽略高度信息

  # GPU设置
  use_gpu: true
  gpu_index: 0
```

**匹配方法选择**：

| 方法 | 适用场景 | 速度 | 内存 |
|------|----------|------|------|
| `sequential` | 有序图像序列 | 快 | 低 |
| `spatial` | GPS信息可用 | 中 | 中 |
| `exhaustive` | 小规模数据集 | 慢 | 高 |
| `vocab_tree` | 超大规模数据集 | 很快 | 低 |

#### Mapper（稀疏重建）

```yaml
mapper_params:
  # 重建策略
  mapper: "incremental"          # incremental, global

  # 最小匹配
  min_num_matches: 15            # 两视图最小匹配点数

  # 稠密重建
  dense_reconstruction: false    # 是否进行密集重建

  # Bundle Adjustment
  refine_extra_params: false     # 优化额外参数（焦距、畸变）

  # GPS Prior（如果有GPS信息）
  refine_gps: true               # 优化GPS位置
  gps_std: 1.0                   # GPS标准差（米）

  # 地理参考
  georef_enabled: false          # 启用地理参考
```

### 典型用例

#### 航拍重建

```yaml
algorithm: "COLMAP"
feature_params:
  camera_model: "SIMPLE_PINHOLE"
  single_camera: true
  max_num_features: 8192

matching_params:
  method: "sequential"
  overlap: 15

mapper_params:
  mapper: "incremental"
  min_num_matches: 15
  georef_enabled: true  # 启用GPS地理参考
```

#### 地面拍摄

```yaml
algorithm: "COLMAP"
feature_params:
  camera_model: "OPENCV"  # 支持畸变
  single_camera: false   # 多相机

matching_params:
  method: "spatial"  # 利用GPS信息

mapper_params:
  mapper: "incremental"
  refine_extra_params: true  # 优化畸变参数
```

---

## GLOMAP

### 简介

GLOMAP 是一个全局式 Structure-from-Motion 算法，通过全局优化快速恢复相机姿态。

### 特点

- ✅ 全局优化，速度快
- ✅ 适合大规模数据集
- ✅ 支持 mapper_resume 迭代优化
- ✅ 与 COLMAP 格式兼容

### 处理流程

1. **特征提取和匹配**
   - 使用 COLMAP 的特征提取器
   - 支持多种匹配策略

2. **全局旋转估计**
   - 基于旋转平均的初始化
   - 鲁棒的旋转估计

3. **全局位置估计**
   - 线性求解相机位置
   - 考虑尺度一致性

4. **精细化**
   - 局部 Bundle Adjustment
   - 全局 Bundle Adjustment

### 关键参数

```yaml
glomap_params:
  # 模式选择
  mode: "mapping"                # mapping, mapper_resume

  # 估计和细化
  estimate_refine: true          # 估计并细化相机姿态
  refine_relative_rotations: true # 细化相对旋转
  refine_relative_translations: true # 细化相对平移

  # 优化参数
  ba_refine_focal_length: false  # BA优化焦距
  ba_refine_extra_params: false  # BA优化额外参数

  # Mapper Resume（迭代优化）
  # 仅在 mode="mapper_resume" 时生效
  input_colmap_path: null        # 输入COLMAP模型路径
  output_colmap_path: null       # 输出COLMAP模型路径
```

### GLOMAP 模式

#### Mapping 模式

完整的 SfM 流程：
1. 特征提取和匹配
2. 全局旋转估计
3. 全局位置估计
4. 细化和 BA

适用于：首次重建

#### Mapper Resume 模式

迭代优化现有结果：
1. 加载已有的 COLMAP 模型
2. 重新优化相机姿态
3. 导出优化后的模型

适用于：
- COLMAP 结果不理想
- 需要进一步优化
- 调整参数重新运行

### 典型用例

#### 大规模航拍（1000+ 图像）

```yaml
algorithm: "GLOMAP"
feature_params:
  camera_model: "SIMPLE_PINHOLE"
  max_num_features: 8192

matching_params:
  method: "spatial"
  spatial_max_num_neighbors: 30

glomap_params:
  mode: "mapping"
  estimate_refine: true
```

#### 迭代优化 COLMAP 结果

```yaml
algorithm: "GLOMAP"
glomap_mode: "mapper_resume"
glomap_params:
  mode: "mapper_resume"
  input_colmap_path: "/path/to/original/sparse/0"
  estimate_refine: true
  ba_refine_focal_length: true
```

---

## InstantSfM

### 简介

InstantSfM 是一个快速的全局式 SfM 算法，支持实时 3D 可视化。

### 特点

- ⚡ 处理速度很快
- 🎨 实时 3D 可视化
- 🔧 支持交互式调整
- 📊 内置 Viser 可视化服务器

### 处理流程

1. **特征提取和匹配**
   - SuperPoint 特征检测
   - SuperGlue 匹配

2. **全局初始化**
   - 快速旋转估计
   - 线性位置求解

3. **实时可视化**
   - Viser 服务器
   - WebSocket 推送

### 关键参数

```yaml
instantsfm_params:
  # 可视化
  viser: true                    # 启用Viser可视化
  viser_port: 8080               # Viser服务器端口

  # 优化
  ba_refine_focal_length: true   # BA优化焦距
  ba_refine_extrinsics: true     # BA优化外参

  # 输出
  output_format: "colmap"        # 输出格式（colmap）
```

### 实时可视化

**访问 Viser**：
```bash
# 默认地址
http://localhost:8080

# 如果在不同端口
http://localhost:<viser_port>
```

**功能**：
- 实时查看相机姿态
- 查看稀疏点云
- 交互式 3D 导航

### 典型用例

#### 快速原型验证

```yaml
algorithm: "INSTANTSFM"
instantsfm_params:
  viser: true
  viser_port: 8080
```

---

## OpenMVG

### 简介

OpenMVG 是一个开源的多视图几何库，提供 CPU 友好的 SfM 实现。

### 特点

- 💻 纯 CPU 运行
- 🧠 智能线程/内存管理
- 🔧 灵活的参数配置
- 📊 支持多种描述子

### 处理流程

1. **特征提取**
   - SIFT, AKAZE, LIOP 等描述子
   - 自动调整图像尺寸

2. **特征匹配**
   - 最近邻匹配
   - 几何验证

3. **增量重建**
   - 类似 COLMAP 的增量式流程
   - 自动调整线程数

### 关键参数

```yaml
openmvg_params:
  # 描述子类型
  desc_type: "SIFT"             # SIFT, AKAZE, LIOP, BINARY_SIFT

  # 线程控制
  num_threads: "auto"           # auto, 或具体数字
  max_ram_mb: 8000             # 最大内存使用（MB）

  # 特征匹配
  force_flatten_match: false    # 强制平坦匹配
  ratio: 0.8                    # 最近邻比率
  geometric_model: "f"         # 几何模型（f=fundamental, h=homography)

  # 增量重建
  consecutive_match: true       # 连续匹配
  incremental_rotation: true    # 增量旋转估计
```

### 资源自适应

**线程数自动调整**：
```python
# OpenMVG 自动计算
num_threads = min(cpu_count, max(1, int(total_memory_gb / 2)))
```

**内存管理**：
- 系统会根据可用内存调整图像尺寸
- 避免内存溢出

### 典型用例

#### CPU 环境重建

```yaml
algorithm: "OPENMVG"
openmvg_params:
  desc_type: "SIFT"
  num_threads: "auto"
  max_ram_mb: 16000
```

#### 内存受限环境

```yaml
algorithm: "OPENMVG"
feature_params:
  max_image_size: 1024  # 降低图像尺寸
openmvg_params:
  max_ram_mb: 4000
```

---

## OpenMVS

### 简介

OpenMVS 是一个多视图立体重建库，从稀疏点云生成密集网格。

### 处理流程

1. **密集点云生成**（Densify）
   - PMVS/CMVS 算法
   - 从稀疏点云生成密集点云

2. **网格重构**（Meshing）
   - 泊松表面重建
   - 生成三角网格

3. **网格优化**（Refine）
   - 迭代优化网格质量
   - 去除噪声

4. **纹理映射**（Texture）
   - 投影纹理到网格
   - 生成纹理模型

### 质量预设

```yaml
# Low 质量预设（快速预览）
densify:
  resolution_level: 2
  number_views: 4
mesh:
  resolution_level: 2

# Medium 质量预设（推荐）
densify:
  resolution_level: 1
  number_views: 6
mesh:
  resolution_level: 1

# High 质量预设（最高质量）
densify:
  resolution_level: 0
  number_views: 9
mesh:
  resolution_level: 0
```

### 关键参数

```yaml
openmvs_params:
  # Densify
  densify:
    resolution_level: 1         # 图像分辨率级别（0=原始，1=1/2，2=1/4）
    number_views: 6             # 每个点使用的前视图数量
    min_image_size: 600         # 最小图像尺寸

  # Meshing
  mesh:
    resolution_level: 1         # 网格分辨率
    min_triangle_area: 0.0001   # 最小三角形面积

  # Refine
  refine:
    scale: 1.0                  # 优化尺度
    max_iterations: 100         # 最大迭代次数

  # Texture
  texture:
    resolution_level: 1         # 纹理分辨率
    color_spacing: 4            # 颜色采样间距
```

### 典型用例

#### 高质量网格

```yaml
quality_preset: "high"
openmvs_params:
  densify:
    resolution_level: 0
    number_views: 9
  refine:
    scale: 2.0                  # 更高精度
    max_iterations: 200
```

---

## 3D Gaussian Splatting

### 简介

3D Gaussian Splatting (3DGS) 是一种实时渲染的 3D 场景表示方法。

### 特点

- 🎨 实时渲染
- 📷 高质量重建
- 🔧 灵活的训练控制
- 📦 SPZ 压缩支持

### 训练流程

1. **数据准备**
   - COLMAP 格式稀疏点云
   - 图像和相机参数

2. **训练**
   - 初始化高斯点云
   - 迭代优化
   - 自适应密集化

3. **导出**
   - PLY 点云
   - SPZ 压缩格式
   - 3D Tiles 转换

### 关键参数

```yaml
gs_params:
  # 基础训练参数
  iterations: 30000             # 总迭代次数
  resolution: 1                 # 分辨率缩放（1=原始，2=1/2）

  # 密集化控制
  densify_until_iter: 15000     # 密集化截止迭代
  densify_from_iter: 500        # 密集化开始迭代
  opacity_reset_interval: 3000  # 不透明度重置间隔

  # 优化参数
  lr: 0.0001                   # 学习率
  position_lr_max_steps: 30000 # 位置LR衰减步数

  # 输出控制
  eval: false                   # 启用评估
  export_spz: true             # 导出SPZ压缩
```

### SPZ 压缩

**压缩效果**：
- 原始 PLY: ~180MB
- 压缩 SPZ: ~15MB
- 压缩比: ~90%

**用途**：
- 减少存储空间
- 加快网络传输
- 3D Tiles 优化

### 典型用例

#### 快速预览

```yaml
gs_params:
  iterations: 10000             # 减少迭代
  resolution: 2                 # 降低分辨率
  densify_until_iter: 5000
```

#### 高质量训练

```yaml
gs_params:
  iterations: 60000             # 增加迭代
  resolution: -1                # 全分辨率
  densify_until_iter: 30000
  export_spz: true
```

---

## 算法选择指南

### 决策树

```
是否有GPU？
├─ 否 → OpenMVG
└─ 是 → 数据规模？
    ├─ 小规模（<100图）→ COLMAP / InstantSfM
    ├─ 中规模（100-1000图）→ COLMAP / GLOMAP
    └─ 大规模（>1000图）→ GLOMAP
```

### 场景推荐

| 场景 | 推荐 | 备选 |
|------|------|------|
| 常规摄影测量 | COLMAP | GLOMAP |
| 大规模航拍 | GLOMAP | COLMAP (分区) |
| 快速验证 | InstantSfM | COLMAP |
| CPU环境 | OpenMVG | - |
| 实时可视化 | InstantSfM | - |
| 3DGS训练 | COLMAP (PINHOLE) | GLOMAP (PINHOLE) |

### 参数推荐

#### 新手（默认参数）

```yaml
algorithm: "COLMAP"
# 使用默认参数
```

#### 高质量（调整特征数）

```yaml
algorithm: "COLMAP"
feature_params:
  max_num_features: 16384      # 增加特征
  max_image_size: 4096         # 提高分辨率
matching_params:
  method: "exhaustive"         # 完全匹配
```

#### 大数据集（分区+全局优化）

```yaml
algorithm: "GLOMAP"
enable_partition: true         # 启用分区
partition_size: 500            # 每分区图像数
matching_params:
  method: "spatial"            # 空间匹配
```

---

## 下一步

- [用户指南](./03-user-guide/) - 如何使用算法
- [开发指南](./05-development/) - API 和扩展
- [配置指南](../CONFIGURATION.md) - 完整配置说明
