# Case Study #002: 地理参考系统 (Georeferencing)

> **问题**: SfM 重建结果在真实地理位置中的定位
> **解决方案**: GPS → UTM → ENU 三步转换
> **关键决策**: pyproj 进行坐标系转换
> **技术亮点**: 自动注入 transform 到 3D Tiles

---

## 背景

### 问题陈述

SfM 重建的模型是基于局部坐标系的（任意原点和方向），无法直接用于地理信息系统（GIS）或真实场景可视化。

### 需求

1. 将模型对齐到真实地理位置
2. 支持 Cesium 等三维 GIS 平台
3. 保留重建精度

---

## 技术方案

### 三步转换流程

```
1. GPS (WGS84) → UTM (通用横轴墨卡托投影)
   - 使用 pyproj 进行坐标转换
   - 根据经纬度自动确定 UTM 分区

2. COLMAP model_aligner → sparse_utm/0
   - 使用参考图片对齐模型
   - 输出转换矩阵

3. UTM → ENU (局部东北天坐标系)
   - 平移原点到参考图片的平均位置
   - 生成 ENU → ECEF 变换矩阵
```

### 代码实现

**文件**: `aerotri-web/backend/app/services/task_runner.py`

```python
async def _run_georef_and_origin_shift(
    self,
    block: Block,
    image_dir: str,
    mapper_params: dict,
):
    """GPS → UTM → ENU 转换."""

    # 1. 提取 EXIF GPS
    cmd_exif = [
        "exiftool",
        "-csv",
        "-n",
        "-FileName",
        "-GPSLatitude",
        "-GPSLongitude",
        "-GPSAltitude",
        image_dir,
    ]

    # 2. GPS → UTM 转换
    from pyproj import Transformer

    lat_mean = sum(lats) / len(lats)
    lon_mean = sum(lons) / len(lons)

    zone = int(math.floor((lon_mean + 180.0) / 6.0) + 1)
    hemi = "N" if lat_mean >= 0 else "S"
    epsg_utm = (32600 + zone) if hemi == "N" else (32700 + zone)

    tr = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg_utm}", always_xy=True)
    for lon, lat in zip(lons, lats):
        E, N = tr.transform(lon, lat)
        E_list.append(float(E))
        N_list.append(float(N))

    # 3. COLMAP model_aligner
    cmd_align = [
        "colmap", "model_aligner",
        "--input_path", input_sparse,
        "--output_path", sparse_utm_root,
        "--ref_images_path", ref_images,
        "--merge_images",  # 合并而非分割
        "--robust_alignment", "1",  # 鲁棒对齐
    ]
```

---

## 经验总结

### 1. UTM 分区自动计算

```python
zone = int(math.floor((lon_mean + 180.0) / 6.0) + 1)
hemi = "N" if lat_mean >= 0 else "S"
epsg_utm = (32600 + zone) if hemi == "N" else (32700 + zone)
```

### 2. 3D Tiles transform 注入

在 3D Tiles 转换时，自动注入 `root.transform`：

```python
# tiles_runner.py
if geo_ref_path.exists():
    with open(geo_ref_path) as f:
        geo_ref = json.load(f)
        root_transform = geo_ref.get("enu_to_ecef")
        tileset_json["root"]["transform"] = root_transform
```

---

**相关文件**:
- `task_runner.py:571` - `_run_georef_and_origin_shift`
- `tiles_runner.py` - transform 注入

