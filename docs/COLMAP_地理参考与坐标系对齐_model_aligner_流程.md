# COLMAP 地理参考与坐标系对齐（`model_aligner`）流程梳理

本文整理 COLMAP 重建模型为什么默认在**任意局部坐标系**、以及如何基于图像 EXIF GPS（或外部参考坐标）将稀疏模型对齐到**地理/投影坐标系**（如 UTM），并给出一套可复用的命令与关键参数说明。

---

## 1. 背景：为什么 COLMAP 的位姿/点云默认不是地理坐标

COLMAP 的 SfM（稀疏重建）在没有外部约束时，只能恢复到一个**相似变换不确定**的坐标系：

- **原点不确定**：整体可任意平移
- **方向不确定**：整体可任意旋转
- **尺度不确定**：整体可任意缩放（尤其是纯单目）

因此输出的相机位姿与稀疏点云通常处于一个“随机”的局部坐标系（但内部几何一致）。

要进入地理坐标系，需要提供**外部参考**（图像 GPS、控制点 GCP、参考模型等），并估计一个全局变换将模型对齐过去。

---

## 2. 总体思路：EXIF 经纬高 → 投影坐标（UTM）→ 对齐

以“图像含 GPS 先验信息”为例，推荐工程化流程：

- 使用 `exiftool` 批量导出每张图的 **经纬度/高程**
- 使用 Python + `pyproj` 将 **WGS84 (lat/lon/alt)** 转为 **UTM (E/N/H, 米)**
- 生成 `ref_images.txt`（每行：`IMAGE_NAME X Y Z`）
- 运行 `colmap model_aligner`，生成对齐后的稀疏模型（`cameras.bin/images.bin/points3D.bin`）

为什么建议转 UTM：

- UTM 为**米单位**，几何意义更直观；更适合后续测量、与工程数据融合
- 避免把经纬度当平面坐标导致的尺度/角度失真

---

## 3. 数据与目录（示例）

本次示例使用的数据路径：

- 原始影像（含 EXIF GPS）：
  - `/root/data/city1-CQ02-441-bagcp-riggcp-adj - export`
- COLMAP 稀疏模型（输入）：
  - `/root/work/aerotri-web/data/outputs/bb38656b-33cc-4c21-9e29-ff94844e9e6d/sparse/0`
- 对齐后模型（输出）：
  - `/root/work/aerotri-web/data/outputs/bb38656b-33cc-4c21-9e29-ff94844e9e6d/sparse_aligned`
- 参考文件与中间文件：
  - `/root/work/aerotri-web/data/geo/city1-CQ02/`

---

## 4. 第一步：导出 EXIF GPS（`exiftool`）

建议使用 `-n` 输出纯数字（不要度分秒字符串）：

```bash
mkdir -p /root/work/aerotri-web/data/geo/city1-CQ02

exiftool -csv -n \
  -SourceFile \
  -FileName \
  -GPSLatitude \
  -GPSLongitude \
  -GPSAltitude \
  "/root/data/city1-CQ02-441-bagcp-riggcp-adj - export" \
  > /root/work/aerotri-web/data/geo/city1-CQ02/gps_raw.csv
```

输出文件 `gps_raw.csv` 典型列：

- `FileName`：图片文件名（应与 COLMAP 模型中的图片名一致）
- `GPSLatitude/GPSLongitude/GPSAltitude`：WGS84 经纬高（单位：度/米）

---

## 5. 第二步：经纬高 → UTM（Python + `pyproj`，自动选带号/EPSG）

我们提供一个通用脚本：**自动根据平均经纬度计算 UTM Zone / EPSG**，并把输出写到输入 CSV 同目录。

脚本位置（示例）：

- `/root/work/aerotri-web/tools/make_ref_images_from_gps.py`

用法：

```bash
pip install pyproj pandas

python3 /root/work/aerotri-web/tools/make_ref_images_from_gps.py \
  /root/work/aerotri-web/data/geo/city1-CQ02/gps_raw.csv
```

输出：

- `/root/work/aerotri-web/data/geo/city1-CQ02/gps_raw_ref_images.txt`
- 每行格式：

```text
IMAGE_NAME X Y Z
```

其中 `X/Y` 是 UTM 的 Easting/Northing（米），`Z` 为高程（米）。

脚本运行时会打印自动选择结果，例如：

```text
[INFO] 平均经纬度: lat=..., lon=...
[INFO] 自动选择 UTM Zone: 49N, EPSG:32649
```

---

## 6. 第三步：`model_aligner` 对齐到 UTM（COLMAP 3.14 dev 参数）

先查看当前版本可用参数：

```bash
colmap model_aligner --help
```

本次环境示例为：

```text
COLMAP 3.14.0.dev0 (Commit ... with CUDA)
```

### 6.1 关键命令（推荐）

```bash
MODEL_IN=/root/work/aerotri-web/data/outputs/bb38656b-33cc-4c21-9e29-ff94844e9e6d/sparse/0
MODEL_OUT=/root/work/aerotri-web/data/outputs/bb38656b-33cc-4c21-9e29-ff94844e9e6d/sparse_aligned
REF_IMGS=/root/work/aerotri-web/data/geo/city1-CQ02/gps_raw_ref_images.txt

mkdir -p "$MODEL_OUT"

colmap model_aligner \
  --input_path "$MODEL_IN" \
  --output_path "$MODEL_OUT" \
  --ref_images_path "$REF_IMGS" \
  --ref_is_gps 0 \
  --alignment_type custom \
  --min_common_images 3 \
  --alignment_max_error 20
```

### 6.2 关键参数解释

- **`--input_path`**：待对齐的稀疏模型目录（含 `cameras.bin/images.bin/points3D.bin`）
- **`--output_path`**：对齐后输出目录（需要存在；建议 `mkdir -p`）
- **`--ref_images_path`**：参考文件路径（每行 `IMAGE_NAME X Y Z`）
- **`--ref_is_gps`**：
  - `1`：参考坐标是 GPS（经纬高）语义，COLMAP 会按 GPS 方式处理
  - `0`：参考坐标是普通笛卡尔坐标（例如 UTM 米坐标）
  - **本流程用了 `pyproj` 转 UTM，因此必须 `0`**
- **`--alignment_type`**（3.14 版本取值：`{plane, ecef, enu, enu-plane, enu-plane-unscaled, custom}`）：
  - **`custom`**：按你提供的参考坐标直接对齐（适合 UTM、工程坐标等）
  - `ecef/enu/...`：更偏“GPS 语义”流程（当 `ref_is_gps=1` 时常用）
- **`--min_common_images`**：模型中与参考文件可匹配的最少图像数；至少 3
- **`--alignment_max_error`**：
  - 对齐时允许的最大误差阈值（建议设一个 > 0 的米级数值，如 `10~50`）
  - **在本版本中必须 > 0**，否则会报：
    - `You must provide a maximum alignment error > 0`

### 6.3 常见坑

- **参数不兼容**：不同 COLMAP 版本的 `model_aligner` 参数集合不同（例如某些旧教程里的 `--estimate_world_scale`、`--alignment_type similarity` 可能不存在）。务必以 `--help` 为准。
- **输出目录必须存在**：`model_converter` / 某些写文件过程要求输出目录存在，建议统一 `mkdir -p`。
- **图片名必须完全一致**：`ref_images_path` 里的 `IMAGE_NAME` 必须与 COLMAP 模型中的图片名一致（区分大小写）。
- **UTM 带号需正确**：脚本已自动选带号，但若数据跨多个 UTM 带或范围很大，需更谨慎地定义投影/坐标系。

---

## 7. 输出质量评估（建议检查项）

`model_aligner` 会输出对齐统计信息，例如：

```text
=> Using 435 reference images
=> Alignment error: 1.17 (mean), 1.12 (median)
=> Alignment succeeded
```

建议你做两类检查：

### 7.1 坐标数量级检查（是否像 UTM）

对齐后点云坐标应为典型 UTM 数量级：

- Easting (X)：几十万 ~ 百万
- Northing (Y)：几百万
- Height (Z)：与现场海拔同量级（几十~几千米）

### 7.2 抽查相机位置误差（是否与参考接近）

将输出模型转为 TXT 并抽查若干张图像：

```bash
MODEL_OUT=/root/work/aerotri-web/data/outputs/bb38656b-33cc-4c21-9e29-ff94844e9e6d/sparse_aligned
MODEL_OUT_TXT=/root/work/aerotri-web/data/outputs/bb38656b-33cc-4c21-9e29-ff94844e9e6d/sparse_aligned_txt

mkdir -p "$MODEL_OUT_TXT"
colmap model_converter \
  --input_path "$MODEL_OUT" \
  --output_path "$MODEL_OUT_TXT" \
  --output_type TXT
```

对比 `MODEL_OUT_TXT/images.txt` 中对应图像的相机中心（或从位姿换算得到的中心）与 `ref_images` 中的 UTM 坐标，验证误差是否在预期范围（普通 GPS 常见为米级）。

---

## 8. 进一步提升精度（可选）

- 若有 **RTK**、**GCP**（地面控制点）或更精确的相机位置/姿态先验，可以进一步将误差从米级压到分米甚至厘米级。
- 思路依然是：构建可靠的 2D/3D 对应或位置先验，再进行更强约束的对齐/优化（视你的管线而定）。






