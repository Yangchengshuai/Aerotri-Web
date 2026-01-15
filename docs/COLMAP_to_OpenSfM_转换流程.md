# COLMAP 到 OpenSfM 格式转换完整流程

本文档描述从 COLMAP 稀疏重建输出到 OpenSfM 格式的完整转换流程，包括地理对齐步骤。

## 目录

- [前置要求](#前置要求)
- [步骤 1: COLMAP 稀疏重建](#步骤-1-colmap-稀疏重建)
- [步骤 2: 地理对齐 (可选)](#步骤-2-地理对齐-可选)
- [步骤 3: 转换为 TXT 格式](#步骤-3-转换为-txt-格式)
- [步骤 4: 转换为 OpenSfM 格式](#步骤-4-转换为-opensfm-格式)
- [验证转换结果](#验证转换结果)
- [故障排查](#故障排查)

---

## 前置要求

### 必需工具

```bash
# COLMAP (已安装)
colmap --version

# Python 依赖
pip install numpy scipy pyproj
```

### 目录结构

```
project_root/
├── data/outputs/{block_id}/
│   └── sparse/
│       ├── 0/              # 原始重建结果
│       └── geo_model/      # 地理对齐后的结果
└── images/                 # 原始图像目录
```

---

## 步骤 1: COLMAP 稀疏重建

假设已经完成 COLMAP 稀疏重建，输出文件位于 `sparse/0/` 目录。

### 输出文件说明

```
sparse/0/
├── cameras.bin      # 相机内参 (二进制)
├── images.bin       # 图像外参 (二进制)
├── points3D.bin     # 3D 点云 (二进制)
└── (可选) cameras.txt, images.txt, points3D.txt
```

---

## 步骤 2: 地理对齐 (可选)

如果图像包含 EXIF GPS 数据，可以使用 `model_aligner` 进行地理对齐。

### 2.1 自动检测坐标类型

COLMAP 会自动检测坐标类型：
- **GPS 坐标**: WGS84 经纬度
- **笛卡尔坐标**: 局部坐标系

**无需手动设置 `--ref_is_gps` 参数**

### 2.2 执行地理对齐

#### 地理对齐原理

COLMAP 的 `model_aligner` 使用 `--alignment_type enu` 时：

1. **ENU 坐标系**: East-North-Up（东-北-天）
   - X 轴指向东
   - Y 轴指向北
   - Z 轴指向天

2. **原点选择**:
   - 通常选择最接近所有图像 GPS 中心的图像作为原点
   - 或选择第一张有 GPS 数据的图像
   - 原点的位置在 ENU 坐标系中为 (0, 0, 0)

3. **坐标转换流程**:
   ```
   GPS (WGS84) → UTM → ECEF → ENU
   ```
   - GPS: 经纬度坐标
   - UTM: 投影坐标系
   - ECEF: 地心地固坐标系
   - ENU: 局部切平面坐标系

```bash
# 进入工作目录
cd /root/work/aerotri-web/data/outputs/{block_id}

# 方法 1: 使用 EXIF GPS 数据进行对齐 (推荐)
colmap model_aligner \
  --input_path sparse/0 \
  --output_path sparse/geo_model \
  --ref_is_gps 1 \
  --alignment_type enu

# 方法 2: 使用外部参考图像文件
colmap model_aligner \
  --input_path sparse/0 \
  --output_path sparse/geo_model \
  --ref_images_path /path/to/reference_images.txt \
  --alignment_type enu

# 方法 3: 指定变换矩阵
colmap model_aligner \
  --input_path sparse/0 \
  --output_path sparse/geo_model \
  --transform_path /path/to/transformation.txt
```

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--input_path` | 输入模型目录 | - |
| `--output_path` | 输出模型目录 | - |
| `--ref_is_gps` | 参考坐标是否为 GPS (0/1) | 1 |
| `--alignment_type` | 对齐类型 | `custom` |
| `--merge_image_and_ref_origins` | 合并图像和参考原点 | 0 |

**对齐类型选项:**
- `plane`: 平面对齐
- `ecef`: 地心地固坐标系
- `enu`: 东-北-天坐标系 (推荐用于无人机数据)
- `enu-plane`: ENU + 平面约束
- `enu-plane-unscaled`: 未缩放的 ENU 平面
- `custom`: 自定义变换

### 2.3 验证对齐结果

```bash
# 检查输出文件
ls -lh sparse/geo_model/

# 应该包含:
# - cameras.bin, cameras.txt
# - images.bin, images.txt
# - points3D.bin, points3D.txt
```

---

## 步骤 3: 转换为 TXT 格式

如果输出只有二进制文件 (`.bin`)，需要转换为文本格式。

### 3.1 使用 model_converter

```bash
colmap model_converter \
  --input_path sparse/geo_model \
  --output_path sparse/geo_model \
  --output_type TXT
```

### 3.2 输出文件格式

**cameras.txt 格式:**
```
# Camera list with one line of data per camera:
#   CAMERA_ID, MODEL, WIDTH, HEIGHT, PARAMS[]
# Number of cameras: 1
1 OPENCV 5280 3956 3710.04 3711.2 2651.6 1991.5 -0.1006 -0.0197 -0.000392 0.0000468 0
```

**images.txt 格式:**
```
# Image list with two lines of data per image:
#   IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME
#   POINTS2D[] as (X, Y, POINT3D_ID)
Number of images: 441
1 0.123 -0.456 0.789 0.234 -0.134 -0.043 0.061 1 DJI_001.JPG
0.234 0.456 1 0.678 0.123 -1 0.345 0.567 2
...
```

**points3D.txt 格式:**
```
# 3D point list with one line of data per point:
#   POINT3D_ID, X, Y, Z, R, G, B, ERROR, TRACK[] as (IMAGE_ID, POINT2D_IDX)
Number of points: 494950
1 0.123 0.456 0.789 47 50 52 0.5 1 0 2 1 3 2
...
```

---

## 步骤 4: 转换为 OpenSfM 格式

### 4.1 使用直接转换脚本 (推荐)

```bash
# 进入项目根目录
cd /root/work/Aerotri-Web

# 执行转换 (自动提取 GPS 原点)
python3 tools/colmap2opensfm.py \
  /root/work/aerotri-web/data/outputs/{block_id}/sparse/geo_model \
  /root/work/aerotri-web/data/outputs/{block_id}/sparse/geo_model/opensfm_direct \
  /root/work/aerotri-web/data/blocks/{block_id}/images
```

**参数说明:**
- 第 1 个参数: COLMAP sparse 目录
- 第 2 个参数: OpenSfM 输出目录
- 第 3 个参数 (可选): 图像目录，用于自动提取 GPS 原点

**GPS 原点提取:**
- 脚本会自动查找最接近原点 (0,0,0) 的图像
- 从该图像的 EXIF 数据中提取 GPS 坐标
- 自动更新 `reference_lla.json` 文件

**示例输出:**
```
读取 COLMAP 数据...
读取到 1 个相机
读取到 441 张图像
读取到 494950 个 3D 点
转换为 OpenSfM 格式...
提取 GPS 原点...
  查找最接近原点的图像...
  尝试提取 GPS: DJI_20250805150313_0425_V.JPG
  ✅ 成功提取 GPS 原点:
     纬度: 30.77821561
     经度: 111.33132283
     高度: 217.007 米
转换完成！
```

### 4.2 输出文件结构

```
opensfm_direct/
├── camera_models.json      # 相机内参模型
├── reconstruction.json      # 重建数据 (shots + points)
├── reference_lla.json       # GPS 参考点
├── image_list.json          # 图像列表
└── tracks.csv              # 特征点跟踪数据
```

---

## 验证转换结果

### 检查文件完整性

```bash
# 检查文件大小
ls -lh sparse/geo_model/opensfm_direct/

# 应该看到:
# camera_models.json  (~400 bytes)
# reconstruction.json (~100-200 MB)
# reference_lla.json  (~50 bytes)
# image_list.json     (~10 KB)
# tracks.csv          (~300 MB)
```

### 验证数据一致性

```bash
# 使用 Python 检查
python3 << EOF
import json

# 读取重建数据
with open('sparse/geo_model/opensfm_direct/reconstruction.json') as f:
    data = json.load(f)[0]

print(f"相机数量: {len(data['cameras'])}")
print(f"图像数量: {len(data['shots'])}")
print(f"3D点数量: {len(data['points'])}")

# 检查第一张图像
first_shot = list(data['shots'].values())[0]
print(f"\n第一张图像:")
print(f"  图像名: {list(data['shots'].keys())[0]}")
print(f"  旋转: {first_shot['rotation'][:3]}")
print(f"  GPS位置: {first_shot['gps_position'][:3]}")
EOF
```

### 对比原始数据

| 项目 | COLMAP | OpenSfM | 状态 |
|------|--------|---------|------|
| 相机数量 | 1 | 1 | ✅ |
| 图像数量 | 441 | 441 | ✅ |
| 3D点数量 | 494,950 | 494,950 | ✅ |

---

## 故障排查

### 问题 1: reference_lla.json 原点为 0

**原因:**
- 旧版本脚本未提取 GPS 原点数据
- 或者未提供图像目录参数

**解决方法:**

方法 1: 使用更新后的脚本重新转换
```bash
python3 tools/colmap2opensfm.py \
  /path/to/sparse/geo_model \
  /path/to/opensfm_output \
  /path/to/images
```

方法 2: 使用独立工具提取 GPS 原点
```bash
python3 tools/extract_gps_origin.py \
  /path/to/sparse/geo_model \
  /path/to/images \
  /path/to/opensfm_output/reference_lla.json
```

方法 3: 手动从图像提取 GPS
```bash
# 提取第一张图像的 GPS
exiftool /path/to/images/*.jpg | grep GPSPosition
```

### 问题 2: 缺少 TXT 文件

**错误信息:**
```
FileNotFoundError: cameras.txt not found
```

**解决方法:**
```bash
# 转换为 TXT 格式
colmap model_converter \
  --input_path sparse/geo_model \
  --output_path sparse/geo_model \
  --output_type TXT
```

### 问题 2: 相机模型不支持

**错误信息:**
```
ValueError: Unsupported camera model: SIMPLE_PINHOLE
```

**解决方法:**
在 `tools/colmap2opensfm.py` 中添加对应该模型的解析代码，或使用 COLMAP 重新重建时指定 OPENCV 模型。

### 问题 3: 地理对齐失败

**错误信息:**
```
No GPS data found in images
```

**解决方法:**
```bash
# 检查 EXIF 数据
exiftool /path/to/images/*.jpg | grep GPS

# 如果没有 GPS，使用笛卡尔坐标系
colmap model_aligner \
  --input_path sparse/0 \
  --output_path sparse/geo_model \
  --ref_is_gps 0 \
  --alignment_type enu
```

### 问题 4: OpenSfM 格式验证失败

**检查清单:**
1. ✅ `camera_models.json` 包含所有必需字段
2. ✅ `reconstruction.json` 是一个数组 `[...]`
3. ✅ 每个 shot 包含 `rotation`, `translation`, `gps_position`
4. ✅ `tracks.csv` 格式正确 (制表符分隔)

---

## 附录

### A. 完整工作流示例

```bash
#!/bin/bash
# 完整的 COLMAP → OpenSfM 转换流程

BLOCK_ID="127ba3a2-dcc5-4090-801b-d1c2ba9b03e2"
WORK_DIR="/root/work/aerotri-web/data/outputs/${BLOCK_ID}"

# 1. 地理对齐
cd ${WORK_DIR}
colmap model_aligner \
  --input_path sparse/0 \
  --output_path sparse/geo_model \
  --ref_is_gps 1 \
  --alignment_type enu

# 2. 转换为 TXT 格式
colmap model_converter \
  --input_path sparse/geo_model \
  --output_path sparse/geo_model \
  --output_type TXT

# 3. 转换为 OpenSfM 格式
cd /root/work/Aerotri-Web
python3 tools/colmap2opensfm.py \
  ${WORK_DIR}/sparse/geo_model \
  ${WORK_DIR}/sparse/geo_model/opensfm_direct

# 4. 验证结果
ls -lh ${WORK_DIR}/sparse/geo_model/opensfm_direct/
```

### B. GPS 原点提取详解

#### 为什么 reference_lla.json 原点为 0？

**问题原因:**
1. COLMAP 的 `model_aligner` 只生成 ENU 坐标系的重建结果
2. 不会自动保存原点的 GPS 坐标到文件中
3. 旧版本的转换脚本没有提取 GPS 功能

#### GPS 原点提取原理

**方法 1: 从图像 EXIF 提取 (推荐)**

1. **查找最接近原点的图像**:
   ```python
   # 从 images.txt 计算每张图像的相机中心
   center = -R_wc.T @ t_wc
   distance = norm(center)
   # 找到距离最小的图像
   ```

2. **提取该图像的 EXIF GPS 数据**:
   ```python
   # 读取 EXIF
   GPSLatitude: 30° 46' 41.5762" N
   GPSLongitude: 111° 19' 52.7622" E
   GPSAltitude: 217.007 m

   # 转换为十进制
   latitude: 30.77821561
   longitude: 111.33132283
   altitude: 217.007
   ```

3. **保存到 reference_lla.json**:
   ```json
   {
     "latitude": 30.77821561111111,
     "longitude": 111.33132283333333,
     "altitude": 217.007
   }
   ```

**方法 2: 从 geo_ref.json 提取**

如果 COLMAP 后端生成了 `geo_ref.json`:
```json
{
  "utm_epsg": 32650,
  "origin": [123456.7, 3456789.0, 100.0],
  "ecef_to_enu": [[...], [...], [...]]
}
```

需要将 UTM 坐标转换为 GPS:
```python
from pyproj import Transformer
transformer = Transformer.from_crs(f"EPSG:{utm_epsg}", "EPSG:4326")
lon, lat = transformer.transform(origin[0], origin[1])
```

#### 使用工具自动提取

**工具 1: colmap2opensfm.py (内置)**
```bash
python3 tools/colmap2opensfm.py \
  /path/to/colmap/sparse \
  /path/to/opensfm/output \
  /path/to/images
```

**工具 2: extract_gps_origin.py (独立)**
```bash
python3 tools/extract_gps_origin.py \
  /path/to/colmap/sparse \
  /path/to/images \
  /path/to/reference_lla.json
```

输出示例:
```
================================================================================
从 COLMAP 空三结果提取 ENU 原点对应的 GPS 坐标
================================================================================

读取: /path/to/geo_model/images.txt
找到 441 张图像

查找位置最接近原点 (0,0,0) 的图像...

前 10 张最接近原点的图像:
排名    图像名                                                 X            Y            Z           距离
1     DJI_20250805150313_0425_V.JPG                   0.044       -0.146        0.014        0.154
2     DJI_20250805150317_0430_V.JPG                  -0.041       33.450        0.685       33.457
...

尝试从最接近原点的图像提取 GPS 数据...
✅ 成功提取 GPS 数据:
  纬度: 30.77821561
  经度: 111.33132283
  高度: 217.007 米

✅ GPS 数据已保存到 reference_lla.json
```

### C. 工具对比

| 工具 | 输入 | 输出 | 优势 | 劣势 |
|------|------|------|------|------|
| **colmap2opensfm.py** | COLMAP + images | OpenSfM | 直接、快速、精确、自动 GPS | 需要 PIL |
| **extract_gps_origin.py** | COLMAP + images | GPS 坐标 | 独立提取 GPS | - |
| colmap2cc.py + cc2odm.py | COLMAP → CC → OpenSfM | 兼容性好 | 两步、参数错误 |

**推荐使用**: `colmap2opensfm.py`

#### 工具特性对比

| 特性 | colmap2opensfm.py | extract_gps_origin.py |
|------|-------------------|----------------------|
| **自动 GPS 提取** | ✅ | ✅ |
| **完整转换** | ✅ | ❌ (仅 GPS) |
| **保留 fx/fy** | ✅ | - |
| **正确 p1/p2** | ✅ | - |
| **支持多相机模型** | ✅ | - |
| **生成所有文件** | ✅ | ❌ |

### D. 数据格式映射表

| COLMAP | OpenSfM | 说明 |
|--------|---------|------|
| `qw, qx, qy, qz` | `rotation[3]` | 四元数 → 旋转向量 |
| `tx, ty, tz` | `translation[3]` | 平移向量 |
| `fx, fy` | `focal_x, focal_y` | 焦距 (像素) |
| `cx, cy` | `c_x, c_y` | 主点 (归一化) |
| `k1, k2, k3` | `k1, k2, k3` | 径向畸变 |
| `p1, p2` | `p1, p2` | 切向畸变 |
| `points3D.txt` | `points` | 3D 点云 |
| `observations` | `tracks.csv` | 2D 观测 |

---

## 参考资源

- [COLMAP 官方文档](https://colmap.github.io/)
- [OpenSfM 文档](https://opensfm.org/docs/)
- [ContextCapture BlocksExchange 格式](https://www.bentley.com/

---

**文档版本:** 1.0
**最后更新:** 2025-01-15
**维护者:** AeroTri Team
