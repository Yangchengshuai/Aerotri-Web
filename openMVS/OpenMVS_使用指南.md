# OpenMVS 使用指南

## 1. OpenMVS 功能模块介绍

OpenMVS (Open Multi-View Stereo) 是一个开源的多视图立体重建库，用于从稀疏点云生成密集三维模型。

### 1.1 核心处理模块

#### DensifyPointCloud - 点云密集化

**功能**: 从稀疏点云和相机参数生成密集点云

**主要用途**:
- 将 SfM（Structure from Motion）生成的稀疏点云密集化
- 支持多种深度估计算法（PatchMatch、SGM）
- 利用 GPU 加速深度图计算
- 可处理大规模场景

**典型输入**: 
- `.mvs` 场景文件（包含相机参数和稀疏点云）
- 原始图像

**输出**:
- 密集点云（`.ply` 格式）
- 深度图和法线图（可选）

---

#### ReconstructMesh - 网格重建

**功能**: 从密集点云重建三角网格表面

**主要用途**:
- 将点云转换为连续的三角网格表面
- 支持 Poisson 表面重建
- 支持 Delaunay 四面体化
- 自动填补孔洞和平滑表面

**典型输入**:
- 密集点云（`.ply` 格式）
- `.mvs` 场景文件

**输出**:
- 三角网格（`.ply` 或 `.obj` 格式）
- 包含顶点、面和法线信息

---

#### RefineMesh - 网格细化

**功能**: 优化和细化网格质量

**主要用途**:
- 基于原始图像细化网格几何
- 优化网格顶点位置以提高精度
- 移除噪声和异常值
- 改善网格拓扑结构

**典型输入**:
- 粗略网格（`.ply` 格式）
- `.mvs` 场景文件
- 原始图像

**输出**:
- 细化后的网格（`.ply` 格式）
- 改进的几何精度

---

#### TextureMesh - 网格纹理映射

**功能**: 为三维网格添加照片级真实感纹理

**主要用途**:
- 从原始图像提取纹理
- 多视图纹理融合
- 自动接缝优化
- 生成高质量纹理图集

**典型输入**:
- 细化网格（`.ply` 格式）
- `.mvs` 场景文件
- 原始图像

**输出**:
- 带纹理的网格（`.ply` 或 `.obj` + 纹理图）
- UV 坐标映射
- 纹理图集（`.png` 或 `.jpg`）

---

### 1.2 接口转换工具

#### InterfaceCOLMAP - COLMAP 接口

**功能**: 在 COLMAP 和 OpenMVS 格式之间转换

**主要用途**:
- 导入 COLMAP 重建结果
- 将 COLMAP 的稀疏重建转换为 `.mvs` 格式
- 支持所有 COLMAP 输出格式

**使用示例**:
```bash
InterfaceCOLMAP \
  -i /path/to/colmap/sparse/0 \
  -o scene.mvs \
  --image-folder /path/to/images
```

---

#### InterfaceMetashape - Metashape 接口

**功能**: 导入 Agisoft Metashape（原 PhotoScan）项目

**主要用途**:
- 读取 Metashape XML 格式
- 转换相机参数和稀疏点云
- 兼容商业摄影测量软件

---

#### InterfaceMVSNet - MVSNet 接口

**功能**: 与深度学习 MVS 方法集成

**主要用途**:
- 导入 MVSNet 风格的数据
- 支持深度学习生成的深度图
- 融合传统和深度学习方法

---

#### InterfacePolycam - Polycam 接口

**功能**: 导入 Polycam 移动端扫描数据

**主要用途**:
- 处理手机/平板扫描数据
- 支持 LiDAR 和摄影测量融合
- 移动端 3D 重建工作流

---

### 1.3 辅助工具

#### TransformScene - 场景变换

**功能**: 对场景进行几何变换

**主要用途**:
- 缩放、旋转、平移场景
- 坐标系转换
- 对齐多个场景
- 单位换算

---

#### Tests - 单元测试

**功能**: 验证 OpenMVS 功能正确性

**主要用途**:
- 开发调试
- 性能基准测试
- 功能验证

---

## 2. 关键参数说明

### 2.1 DensifyPointCloud 参数

#### 核心参数

| 参数 | 说明 | 默认值 | 推荐值 |
|------|------|--------|--------|
| `--resolution-level` | 图像分辨率层级 | 1 | 0-2（0=原始分辨率） |
| `--max-resolution` | 最大图像分辨率 | 3200 | 2048-4096 |
| `--min-resolution` | 最小图像分辨率 | 640 | 320-1024 |
| `--number-views` | 每个深度图使用的视图数 | 5 | 3-7 |
| `--number-views-fuse` | 深度图融合时的视图数 | 3 | 2-5 |
| `--estimate-colors` | 估计点云颜色 | true | true |
| `--estimate-normals` | 估计点云法线 | false | true（网格重建时需要） |

#### GPU 相关参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--cuda-device` | CUDA 设备 ID | -1（自动选择） |
| `--max-threads` | 最大线程数 | 0（自动） |

#### 质量控制参数

| 参数 | 说明 | 推荐值 |
|------|------|--------|
| `--geometric-iters` | 几何一致性迭代次数 | 3-5 |
| `--filter-point-cloud` | 过滤噪声点 | 1-2 |

**参数调优建议**:
- **高质量**: `--resolution-level 0 --number-views 7 --estimate-normals 1`
- **平衡模式**: `--resolution-level 1 --number-views 5`（默认）
- **快速模式**: `--resolution-level 2 --number-views 3 --max-resolution 1600`

---

### 2.2 ReconstructMesh 参数

#### 核心参数

| 参数 | 说明 | 默认值 | 推荐值 |
|------|------|--------|--------|
| `--thickness-factor` | 表面厚度因子 | 1.0 | 0.5-2.0 |
| `--quality-factor` | 网格质量因子 | 1.0 | 1.0-2.0 |
| `--decimate` | 网格简化比例 | 1.0 | 0.5-1.0 |
| `--remove-spurious` | 移除虚假面 | 20 | 10-50 |
| `--remove-spikes` | 移除尖刺 | true | true |
| `--close-holes` | 填补孔洞 | 30 | 10-100 |
| `--smooth` | 平滑迭代次数 | 2 | 0-5 |

**参数调优建议**:
- **精细网格**: `--quality-factor 2.0 --decimate 1.0 --smooth 0`
- **平衡网格**: `--quality-factor 1.0 --remove-spurious 20`（默认）
- **简化网格**: `--decimate 0.5 --smooth 3`

---

### 2.3 RefineMesh 参数

#### 核心参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--resolution-level` | 图像分辨率层级 | 0 |
| `--max-face-area` | 最大面片面积 | 64 |
| `--scales` | 优化尺度数 | 3 |
| `--gradient-step` | 梯度下降步长 | 45.05 |
| `--reduce-memory` | 降低内存使用 | true |

**参数调优建议**:
- 大规模场景: `--reduce-memory 1 --max-face-area 128`
- 高精度: `--resolution-level 0 --scales 5`

---

### 2.4 TextureMesh 参数

#### 核心参数

| 参数 | 说明 | 默认值 | 推荐值 |
|------|------|--------|--------|
| `--resolution-level` | 纹理分辨率层级 | 0 | 0-1 |
| `--min-resolution` | 最小纹理分辨率 | 640 | 1024-2048 |
| `--outlier-threshold` | 异常值阈值 | 6e-2 | 4e-2 - 8e-2 |
| `--cost-smoothness-ratio` | 成本平滑比 | 0.1 | 0.05-0.2 |
| `--empty-color` | 空白区域颜色 | 0 | 0-255 |
| `--orthographic-image-resolution` | 正射影像分辨率 | 0 | 0（禁用） |

**参数调优建议**:
- **高质量纹理**: `--resolution-level 0 --min-resolution 2048`
- **快速纹理**: `--resolution-level 1 --min-resolution 1024`
- **接缝优化**: `--cost-smoothness-ratio 0.15`

---

## 3. 输入输出格式

### 3.1 MVS 场景文件格式 (`.mvs`)

OpenMVS 的核心数据格式，包含完整场景信息：

**内容结构**:
```
- 平台信息（相机内外参）
- 图像列表及路径
- 点云数据（稀疏或密集）
- 网格数据（可选）
```

**创建方式**:
- 通过接口工具从其他格式转换
- OpenMVS 各模块自动生成和更新

---

### 3.2 点云格式 (`.ply`)

**支持的 PLY 属性**:
- 顶点位置: `x, y, z`
- 顶点颜色: `red, green, blue`（可选）
- 顶点法线: `nx, ny, nz`（可选）
- 自定义属性

**读取方式**:
```bash
# OpenMVS 可直接读取
DensifyPointCloud -i scene.mvs -o dense.ply

# 其他工具（CloudCompare、MeshLab）也可打开
```

---

### 3.3 网格格式

#### PLY 格式

**包含信息**:
- 顶点坐标和法线
- 面片索引（三角形）
- 顶点颜色（可选）
- 纹理坐标（带纹理时）

#### OBJ 格式（带纹理）

**文件组成**:
- `.obj` - 几何数据和 UV 坐标
- `.mtl` - 材质定义
- `.png/.jpg` - 纹理图集

**优势**: 
- 广泛支持
- 易于编辑
- 兼容大多数 3D 软件

---

### 3.4 图像格式

**支持的格式**:
- JPEG (`.jpg`, `.jpeg`)
- PNG (`.png`)
- TIFF (`.tif`, `.tiff`)
- BMP (`.bmp`)

**推荐格式**:
- 原始图像: JPEG（文件小）或 TIFF（无损）
- 纹理输出: PNG（无损，支持透明）

---

## 4. 典型工作流程

### 4.1 完整处理流程：稀疏点云 → 纹理网格

#### 步骤 1: 准备数据（使用 COLMAP SfM 结果）

```bash
# 从 COLMAP 导入
InterfaceCOLMAP \
  -i /path/to/colmap/sparse/0 \
  -o scene.mvs \
  --image-folder /path/to/images
```

---

#### 步骤 2: 点云密集化

```bash
# 高质量密集化
DensifyPointCloud scene.mvs \
  -w /path/to/working_dir \
  --resolution-level 0 \
  --number-views 5 \
  --number-views-fuse 3 \
  --estimate-colors 1 \
  --estimate-normals 1 \
  -v 3
```

**输出**: `scene_dense.mvs`（包含密集点云）

**验证**:
```bash
# 查看点云统计
tail -20 DensifyPointCloud.log

# 导出点云查看
# 密集点云已保存在 scene_dense.ply
```

---

#### 步骤 3: 网格重建

```bash
# 从密集点云重建网格
ReconstructMesh scene_dense.mvs \
  -w /path/to/working_dir \
  --thickness-factor 1.0 \
  --quality-factor 1.0 \
  --decimate 1.0 \
  -v 3
```

**输出**: `scene_dense_mesh.mvs`（包含网格）

---

#### 步骤 4: 网格细化（可选但推荐）

```bash
# 细化网格几何
RefineMesh scene_dense_mesh.mvs \
  -w /path/to/working_dir \
  --resolution-level 0 \
  --max-face-area 64 \
  --scales 3 \
  -v 3
```

**输出**: `scene_dense_mesh_refine.mvs`

---

#### 步骤 5: 纹理映射

```bash
# 添加纹理
TextureMesh scene_dense_mesh_refine.mvs \
  -w /path/to/working_dir \
  --resolution-level 0 \
  --min-resolution 1024 \
  --export-type obj \
  -v 3
```

**输出**: 
- `scene_dense_mesh_refine_texture.obj`
- `scene_dense_mesh_refine_texture.mtl`
- `scene_dense_mesh_refine_texture_material_0_map_Kd.png`（纹理图）

---

### 4.2 快速处理模式

```bash
# 一键式处理（适合快速预览）
DensifyPointCloud scene.mvs -w . --resolution-level 1
ReconstructMesh scene_dense.mvs -w . --decimate 0.5
TextureMesh scene_dense_mesh.mvs -w . --resolution-level 1
```

---

### 4.3 高质量处理模式

```bash
# 最高质量设置
DensifyPointCloud scene.mvs \
  --resolution-level 0 \
  --max-resolution 4096 \
  --number-views 7 \
  --number-views-fuse 5 \
  --estimate-normals 1

ReconstructMesh scene_dense.mvs \
  --quality-factor 2.0 \
  --decimate 1.0 \
  --remove-spurious 10 \
  --smooth 0

RefineMesh scene_dense_mesh.mvs \
  --resolution-level 0 \
  --scales 5 \
  --max-face-area 32

TextureMesh scene_dense_mesh_refine.mvs \
  --resolution-level 0 \
  --min-resolution 2048 \
  --cost-smoothness-ratio 0.15
```

---

### 4.4 大规模场景处理

```bash
# 内存优化设置
DensifyPointCloud scene.mvs \
  --resolution-level 1 \
  --max-resolution 2048 \
  --number-views 5 \
  --max-threads 64

ReconstructMesh scene_dense.mvs \
  --decimate 0.7 \
  --remove-spurious 30

RefineMesh scene_dense_mesh.mvs \
  --reduce-memory 1 \
  --max-face-area 128

TextureMesh scene_dense_mesh_refine.mvs \
  --resolution-level 0 \
  --min-resolution 1024
```

---

## 5. 命令行使用示例

### 5.1 基础用法

```bash
# 查看帮助
DensifyPointCloud --help

# 指定工作目录
DensifyPointCloud scene.mvs -w /path/to/output

# 设置详细度
DensifyPointCloud scene.mvs -v 3  # 0=静默, 1=错误, 2=警告, 3=信息
```

---

### 5.2 配置文件使用

```bash
# 使用配置文件
DensifyPointCloud scene.mvs --config-file my_config.cfg

# 生成默认配置文件
DensifyPointCloud --help > DensifyPointCloud_default.cfg
```

**配置文件示例** (`densify_config.cfg`):
```ini
# 密集化配置
resolution-level=0
number-views=5
max-resolution=3200
estimate-normals=1
cuda-device=0
```

---

### 5.3 多 GPU 使用

```bash
# 指定 GPU
DensifyPointCloud scene.mvs --cuda-device 0

# 使用多个 GPU（分别处理不同场景）
DensifyPointCloud scene1.mvs --cuda-device 0 &
DensifyPointCloud scene2.mvs --cuda-device 1 &
DensifyPointCloud scene3.mvs --cuda-device 2 &
wait
```

---

### 5.4 批处理脚本

```bash
#!/bin/bash
# batch_process.sh - OpenMVS 批处理脚本

WORK_DIR="/path/to/working_dir"
SCENES=(scene1.mvs scene2.mvs scene3.mvs)

for scene in "${SCENES[@]}"; do
    echo "Processing $scene..."
    
    # 密集化
    DensifyPointCloud "$scene" -w "$WORK_DIR" --resolution-level 1 -v 2
    
    # 重建
    ReconstructMesh "${scene%.mvs}_dense.mvs" -w "$WORK_DIR" -v 2
    
    # 细化
    RefineMesh "${scene%.mvs}_dense_mesh.mvs" -w "$WORK_DIR" -v 2
    
    # 纹理
    TextureMesh "${scene%.mvs}_dense_mesh_refine.mvs" -w "$WORK_DIR" -v 2
    
    echo "Completed $scene"
done
```

---

## 6. Python API 使用

### 6.1 基础用法

```python
import sys
sys.path.insert(0, '/usr/local/lib')
import pyOpenMVS

# 设置工作目录
pyOpenMVS.set_working_folder("/path/to/working_dir")

# 创建场景
scene = pyOpenMVS.Scene()

# 加载场景
if not scene.load("scene.mvs"):
    print("ERROR: Could not load scene")
    exit(1)

# 密集重建
if not scene.dense_reconstruction():
    print("ERROR: Dense reconstruction failed")
    exit(1)

# 保存点云
scene.save_pointcloud("dense_pointcloud.ply")

# 网格重建
if not scene.reconstruct_mesh():
    print("ERROR: Mesh reconstruction failed")
    exit(1)

scene.save_mesh("mesh.ply")

# 网格细化
if not scene.refine_mesh():
    print("ERROR: Mesh refinement failed")
    exit(1)

scene.save_mesh("refined_mesh.ply")

# 纹理映射
if not scene.texture_mesh():
    print("ERROR: Mesh texturing failed")
    exit(1)

scene.save_mesh("textured_mesh.ply")
```

---

### 6.2 高级用法

```python
import pyOpenMVS

# 设置密集化参数
dense_options = pyOpenMVS.DenseReconstructionOptions()
dense_options.resolution_level = 0
dense_options.number_views = 5
dense_options.estimate_normals = True

scene = pyOpenMVS.Scene()
scene.load("scene.mvs")
scene.dense_reconstruction(dense_options)

# 设置网格重建参数
mesh_options = pyOpenMVS.MeshReconstructionOptions()
mesh_options.thickness_factor = 1.0
mesh_options.quality_factor = 1.5

scene.reconstruct_mesh(mesh_options)
```

---

## 7. 性能优化建议

### 7.1 GPU 优化

- **使用 CUDA**: 确保编译时启用 `OpenMVS_USE_CUDA=ON`
- **选择合适的 GPU**: 密集化阶段最依赖 GPU 性能
- **显存管理**: 大场景可能需要 24GB+ 显存

### 7.2 CPU 优化

- **多线程**: 启用 OpenMP (`OpenMVS_USE_OPENMP=ON`)
- **线程数**: `--max-threads` 设置为 CPU 核心数

### 7.3 内存优化

- **降低分辨率**: `--resolution-level 1` 可减少 50% 内存
- **减少视图数**: `--number-views 3` 降低内存占用
- **启用内存优化**: RefineMesh 使用 `--reduce-memory 1`

### 7.4 质量与速度平衡

| 模式 | resolution-level | number-views | 速度 | 质量 |
|------|------------------|--------------|------|------|
| 快速 | 2 | 3 | 快 | 中 |
| 平衡 | 1 | 5 | 中 | 高 |
| 高质量 | 0 | 7 | 慢 | 极高 |

---

## 8. 故障排查

### 8.1 常见错误

#### 错误 1: CUDA out of memory

**解决方案**:
```bash
# 降低分辨率
--resolution-level 1 --max-resolution 2048

# 减少视图数
--number-views 3
```

#### 错误 2: 网格质量差

**解决方案**:
```bash
# 提高点云质量
DensifyPointCloud --number-views 7 --estimate-normals 1

# 调整网格参数
ReconstructMesh --quality-factor 2.0 --smooth 2
```

#### 错误 3: 纹理接缝明显

**解决方案**:
```bash
TextureMesh --cost-smoothness-ratio 0.15
```

---

### 8.2 性能监控

```bash
# 查看 GPU 使用率
watch -n 1 nvidia-smi

# 查看内存使用
htop

# 查看进程 IO
iotop
```

---

## 9. 输出文件说明

### 9.1 DensifyPointCloud 输出

- `scene_dense.mvs` - 包含密集点云的场景文件
- `scene_dense.ply` - 密集点云（可选导出）
- `depth_XXXX.dmap` - 深度图缓存文件
- `normal_XXXX.dmap` - 法线图缓存文件

### 9.2 ReconstructMesh 输出

- `scene_dense_mesh.mvs` - 包含网格的场景文件
- `scene_dense_mesh.ply` - 三角网格

### 9.3 RefineMesh 输出

- `scene_dense_mesh_refine.mvs` - 细化后的场景文件
- `scene_dense_mesh_refine.ply` - 细化网格

### 9.4 TextureMesh 输出

**PLY 格式**:
- `scene_dense_mesh_refine_texture.ply` - 带颜色的网格

**OBJ 格式** (推荐):
- `scene_dense_mesh_refine_texture.obj` - 几何和 UV 数据
- `scene_dense_mesh_refine_texture.mtl` - 材质定义
- `scene_dense_mesh_refine_texture_material_0_map_Kd.png` - 纹理图集

---

## 10. 与其他软件集成

### 10.1 COLMAP 工作流

```bash
# 1. COLMAP 特征提取和匹配
colmap feature_extractor --database_path database.db --image_path images/
colmap exhaustive_matcher --database_path database.db

# 2. COLMAP 稀疏重建
colmap mapper --database_path database.db --image_path images/ --output_path sparse/

# 3. 转换到 OpenMVS
InterfaceCOLMAP -i sparse/0 -o scene.mvs --image-folder images/

# 4. OpenMVS 密集重建
DensifyPointCloud scene.mvs
ReconstructMesh scene_dense.mvs
RefineMesh scene_dense_mesh.mvs
TextureMesh scene_dense_mesh_refine.mvs
```

---

### 10.2 Metashape 工作流

```bash
# 导出 Metashape 项目为 XML
# 在 Metashape 中: File -> Export -> Export Cameras

# 转换到 OpenMVS
InterfaceMetashape -i project.xml -o scene.mvs

# 继续 OpenMVS 处理流程
...
```

---

### 10.3 CloudCompare 可视化

```bash
# 在 CloudCompare 中打开结果
cloudcompare.CloudCompare \
  scene_dense.ply \
  scene_dense_mesh.ply \
  scene_dense_mesh_refine_texture.obj
```

---

## 11. 参考资源

- **官方文档**: https://github.com/cdcseacave/openMVS/wiki
- **论文**: https://github.com/cdcseacave/openMVS#cite
- **示例数据**: https://github.com/openMVS/openMVS_sample
- **问题讨论**: https://github.com/cdcseacave/openMVS/issues

---

## 附录 A: 完整示例脚本

```bash
#!/bin/bash
# complete_mvs_pipeline.sh
# OpenMVS 完整处理流程

set -e  # 遇到错误立即退出

# 配置
COLMAP_SPARSE="/path/to/colmap/sparse/0"
IMAGES="/path/to/images"
WORK_DIR="/path/to/output"
SCENE_NAME="scene"

echo "=== OpenMVS 完整处理流程 ==="
echo "工作目录: $WORK_DIR"

mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

# 1. COLMAP 转 MVS
echo "[1/5] 转换 COLMAP 数据..."
InterfaceCOLMAP \
  -i "$COLMAP_SPARSE" \
  -o "${SCENE_NAME}.mvs" \
  --image-folder "$IMAGES" \
  -v 2

# 2. 密集化
echo "[2/5] 点云密集化..."
DensifyPointCloud "${SCENE_NAME}.mvs" \
  -w "$WORK_DIR" \
  --resolution-level 1 \
  --number-views 5 \
  --estimate-normals 1 \
  -v 2

# 3. 网格重建
echo "[3/5] 网格重建..."
ReconstructMesh "${SCENE_NAME}_dense.mvs" \
  -w "$WORK_DIR" \
  --quality-factor 1.0 \
  -v 2

# 4. 网格细化
echo "[4/5] 网格细化..."
RefineMesh "${SCENE_NAME}_dense_mesh.mvs" \
  -w "$WORK_DIR" \
  --resolution-level 0 \
  -v 2

# 5. 纹理映射
echo "[5/5] 纹理映射..."
TextureMesh "${SCENE_NAME}_dense_mesh_refine.mvs" \
  -w "$WORK_DIR" \
  --resolution-level 0 \
  --export-type obj \
  -v 2

echo "=== 处理完成 ==="
echo "输出文件:"
ls -lh "${SCENE_NAME}_dense_mesh_refine_texture."*
```

---

**文档版本**: 1.0  
**最后更新**: 2025-12-16  
**适用 OpenMVS 版本**: v2.3.0
