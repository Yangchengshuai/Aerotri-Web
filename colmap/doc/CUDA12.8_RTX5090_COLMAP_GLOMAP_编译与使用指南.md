# CUDA 12.8 + RTX 5090 编译 COLMAP / GLOMAP & 使用指南（Ubuntu 20.04）

> 目标：在 **CUDA 12.8**、**RTX 5090（Compute Capability 12.0 / sm_120）** 环境下，完成 COLMAP 的 CUDA 编译，并给出可复用的 **COLMAP 特征提取/匹配** 与 **GLOMAP mapper 全局建图**命令示例；同时记录本次实际遇到的依赖/运行时问题与修复方法，方便在其它服务器复现部署。

---

## 环境与依赖版本（本次实测）

- **OS**：Ubuntu 20.04.6 LTS
- **Driver**：NVIDIA 570.124.06
- **CUDA Toolkit**：12.8（`nvcc 12.8.93`）
- **GPU**：NVIDIA GeForce RTX 5090（`compute_cap = 12.0`）
- **编译器/构建工具**：
  - GCC/G++：11.4.0
  - CMake：4.2.1

### 关键三方库（系统侧）

> 说明：不同服务器“系统库版本”会导致行为差异，尤其是 OpenImageIO / GDAL / PROJ 一类库。建议部署时做一次 `apt-cache policy`、`ldd` 自检。

- **Ceres**：
  - **系统默认**：1.14.0（Ubuntu 20.04 默认版本）
  - **本文启用 GLOMAP GPU 实测版本**：**2.2.0（源码编译 + CUDA 12.8，安装到 `/opt/ceres-2.2.0-cuda`）**
- **Eigen**：3.3.7
- **OpenImageIO**：2.1.12
- **Qt**：5.12.8（GUI 相关）
- **SuiteSparse / CHOLMOD**：5.7.1
- **CGAL**：5.0.2

---

## CMake / CUDA 架构参数：`90` vs `120`

- RTX 5090 的计算能力是 **12.0**，对应 CUDA 架构 **`sm_120`**，因此：
  - **正确**：`-DCMAKE_CUDA_ARCHITECTURES=120`
  - **不适用**：`90`（`sm_90` 通常对应 Hopper/H100 代）

实践建议：
- 固定写死：`-DCMAKE_CUDA_ARCHITECTURES=120`
- 或者不传，让 CMake 使用 `native`（依赖驱动/编译器环境，跨机复制时不如写死稳定）

---

## 编译：COLMAP CUDA（建议路径）

仓库内有脚本：
- `build_cuda.sh`
- `编译说明.md`

手动配置时关键 CMake 参数示例（核心是 CUDA 12.8 + sm_120）：

```bash
cmake .. \
  -DCMAKE_BUILD_TYPE=Release \
  -DCUDA_ENABLED=ON \
  -DCMAKE_CUDA_COMPILER=/usr/local/cuda-12.8/bin/nvcc \
  -DCMAKE_CUDA_ARCHITECTURES=120 \
  -DCMAKE_CUDA_STANDARD=17 \
  -DCMAKE_CXX_STANDARD=17 \
  -DGUI_ENABLED=ON \
  -DOPENGL_ENABLED=ON
```

---

## 本次编译/运行遇到的问题与解决方法（强烈建议阅读）

### 问题 1：Ubuntu 20.04 的 OpenImageIO 不提供 `OpenImageIOConfig.cmake`

**现象**
- CMake 报错找不到：
  - `OpenImageIOConfig.cmake` 或 `openimageio-config.cmake`

**原因**
- Ubuntu 20.04 的 `libopenimageio-dev` 通常只提供 `pkg-config`（`OpenImageIO.pc`），不提供 CMake package config。

**解决**
- 在仓库中新增 CMake module：`cmake/FindOpenImageIO.cmake`（基于 pkg-config 回退查找）
- 使 `find_package(OpenImageIO)` 能成功，并提供 `OpenImageIO::OpenImageIO` 目标。

---

### 问题 2：OpenImageIO 2.1.x 缺少 `OIIO_MAKE_VERSION` 宏导致编译失败

**现象**
- 编译报错（预处理阶段）类似：
  - `missing binary operator before token "("` 指向 `OIIO_MAKE_VERSION(...)`

**原因**
- Ubuntu 20.04 的 OpenImageIO 2.1.x 头文件未定义 `OIIO_MAKE_VERSION`（但有 `OIIO_VERSION`）。

**解决**
- 在以下文件增加兼容宏定义（若未定义则补齐）：
  - `src/colmap/util/oiio_utils.cc`
  - `src/colmap/sensor/bitmap.cc`

---

### 问题 3：Ceres 1.14 API 与新代码 const-correctness 不一致

**现象**
- `bundle_adjustment.cc` 报错：
  - `invalid conversion from 'const double*' to 'double*'`

**原因**
- Ceres 1.x 的 `Problem::IsParameterBlockConstant(double*)` 接口参数是 `double*`，而新代码传了 `const double*`。

**解决**
- 在 `src/colmap/estimators/bundle_adjustment.cc` 做版本兼容：
  - Ceres < 2 时对指针做 `const_cast`（仅用于查询，不修改参数块）

---

### 问题 4：Eigen 3.3.x 不支持 `Eigen::Vector<T, N>`（GLOMAP 编译失败）

**现象**
- `cost_function.h` 报错：
  - `Eigen::Vector<T, 4> ... does not name a template type`

**原因**
- `Eigen::Vector<T, N>` 是较新版本 Eigen 的别名，Eigen 3.3.x 没有。

**解决**
- `src/glomap/estimators/cost_function.h` 中把：
  - `Eigen::Vector<T, 4>` 替换为 `Eigen::Matrix<T, 4, 1>`

---

### 问题 5（运行期致命）：`colmap/glomap --help` 退出时 `free(): invalid pointer`

**现象**
- 执行 `colmap -h` / `glomap --help` 在退出阶段崩溃，堆栈显示 `osgeo::proj::common::UnitOfMeasure::~UnitOfMeasure()`。

**根因（本次实测）**
- 系统中同时存在多套地理栈依赖链：
  - `libgdal.so.26` 依赖 `libproj.so.15`
  - 但某些库（例如 `libgeotiff5` / `libspatialite7` 的非官方版本）依赖 `libproj.so.22`
  - 最终导致同进程加载多版本 PROJ，触发析构/释放阶段崩溃。

**排查方法（建议复制到新服务器自检）**
```bash
ldd /path/to/colmap | egrep -i 'gdal|proj|geos|geotiff|spatialite'
readelf -d /lib/libgdal.so.26.* | grep NEEDED | egrep -i 'proj|geos'
```

**解决方法（本次采用）**
- 将 `libgeotiff5` 与 `libspatialite7` 降级回 Ubuntu 20.04 官方版本，使其回到 `proj15` 体系，避免 `proj22` 混入：

```bash
sudo apt-get update -y
sudo apt-get install -y --allow-downgrades \
  libgeotiff5=1.5.1-2 \
  libspatialite7=4.3.0a-6build1
```

> 注意：该操作会触发移除一些与新地理栈版本绑定的包（例如 `gdal-bin/libgdal-dev/libgdal30/...`）。如你需要 GDAL 3.4 系列，请确保整套依赖在同一前缀/同一版本族，不要混装。

---

## COLMAP：典型流水线命令（特征提取→匹配→建图）

### 1) 特征提取（`feature_extractor`）

**示例（CPU，稳定复现；建议先跑通再考虑 GPU）**

```bash
COLMAP=/root/work/colmap/build_cuda/src/colmap/exe/colmap
IMG_DIR="/root/data/city1-CQ02-441-bagcp-riggcp-adj - export"
DB="/root/data/recon_colmap_glomap_city1/database.db"

$COLMAP feature_extractor \
  --database_path "$DB" \
  --image_path "$IMG_DIR" \
  --ImageReader.single_camera 1 \
  --ImageReader.camera_model SIMPLE_RADIAL \
  --FeatureExtraction.use_gpu 0 \
  --FeatureExtraction.num_threads 8 \
  --SiftExtraction.max_image_size 2000 \
  --SiftExtraction.max_num_features 4096
```

**关键参数说明**
- `ImageReader.single_camera=1`：假设所有图像共享同一相机内参（手机/无人机单机位常用）
- `ImageReader.camera_model`：相机模型；不确定时先用 `SIMPLE_RADIAL`，后续可改 `OPENCV` 等
- `FeatureExtraction.use_gpu`：SIFT 提取是否用 GPU（1/0）
- `SiftExtraction.max_image_size`：提取时最大边缩放；降到 2000 可显著提速并更省资源
- `SiftExtraction.max_num_features`：每张图最多特征点

### 2) 图像匹配（推荐：序列数据用 `sequential_matcher`）

```bash
$COLMAP sequential_matcher \
  --database_path "$DB" \
  --SequentialMatching.overlap 20 \
  --FeatureMatching.use_gpu 0
```

**关键参数说明**
- `SequentialMatching.overlap`：序列匹配的邻接窗口大小；越大越慢但更稳（典型 10~30）
- `FeatureMatching.use_gpu`：SIFT 匹配是否用 GPU（1/0）

> 若是无序照片集，改用 `exhaustive_matcher` 或 `vocab_tree_matcher`。

### 3) COLMAP 建图（可选，对比用）

```bash
$COLMAP mapper \
  --database_path "$DB" \
  --image_path "$IMG_DIR" \
  --output_path "/root/data/recon_colmap_glomap_city1/colmap_sparse"
```

---

## GLOMAP：mapper 全局建图（基于 COLMAP 数据库）

### 运行示例（本次实测跑通）

```bash
GLOMAP=/root/work/colmap/build_cuda/src/glomap/glomap
IMG_DIR="/root/data/city1-CQ02-441-bagcp-riggcp-adj - export"
DB="/root/data/recon_colmap_glomap_city1/database.db"
OUT="/root/data/recon_colmap_glomap_city1/glomap_model"

$GLOMAP mapper \
  --database_path "$DB" \
  --image_path "$IMG_DIR" \
  --output_path "$OUT" \
  --output_format bin \
  --GlobalPositioning.use_gpu 0 \
  --BundleAdjustment.use_gpu 0
```

输出目录（bin 格式）示例：
- `.../glomap_model/0/cameras.bin`
- `.../glomap_model/0/images.bin`
- `.../glomap_model/0/points3D.bin`
- `.../glomap_model/0/frames.bin`
- `.../glomap_model/0/rigs.bin`

### 关键参数说明（摘自 `glomap mapper -h`）

- **输入/输出**
  - `--database_path`：COLMAP database.db
  - `--image_path`：图像目录（GLOMAP 会读图像列表/名称）
  - `--output_path`：输出模型目录
  - `--output_format`：`bin` / `txt`
- **阶段开关（调试/加速用）**
  - `--skip_preprocessing`
  - `--skip_view_graph_calibration`
  - `--skip_relative_pose_estimation`
  - `--skip_rotation_averaging`
  - `--skip_global_positioning`
  - `--skip_bundle_adjustment`
  - `--skip_retriangulation`
  - `--skip_pruning`
- **GPU（如果启用 CUDA 构建才可能生效；否则会回退 CPU）**
  - `--GlobalPositioning.use_gpu`
  - `--GlobalPositioning.gpu_index`
  - `--BundleAdjustment.use_gpu`
  - `--BundleAdjustment.gpu_index`

---

## GLOMAP mapper 是否支持 `prior_position`（先验位置）加速？

结论：**当前版本不支持**。

依据（源码中明确写了 TODO）：
- `src/glomap/io/colmap_converter.cc` 里对 “从 database 读取 prior pose/position” 的逻辑是注释 + TODO：
  - `// TODO: Implement the logic of reading prior pose from the database`
  - 包括 `database.ReadPosePrior(image_id)` 与 `prior.position` 的示例代码均被注释掉。

补充说明：
- GLOMAP **确实会读取**数据库中的 `PosePrior`（例如用于 gravity/rotation 相关流程），但“位置先验（position prior）用于加速/约束 global positioning”目前未在 converter 中落地。

如果你需要“基于 prior_position 的加速/约束”，需要改源码实现并暴露参数（建议从 `ConvertDatabaseToGlomap()` 处接入 `ReadPosePrior` 并把位置约束纳入 `GlobalPositioning` 的优化问题）。

---

## GLOMAP 是否可以 CUDA 编译加速？

结论：**可以**（已实测启用）。前提是同时满足：
- **Ceres ≥ 2.2 且用 CUDA 编译**（否则会回退 CPU）
- 构建时让 **`GLOMAP_CUDA_ENABLED` 对 GLOMAP 的所有库目标生效**（不能只加到 `glomap` 可执行文件，否则会出现“help 显示 compiled with CUDA，但运行时仍回退 CPU”的矛盾现象）
- （可选）若要 **CUDA Sparse（cuDSS）**，需要 Ceres 支持 `CUDA_SPARSE` + cuDSS（否则只会启用 CUDA dense，sparse 仍走 CPU/CHOLMOD）

### 1) 代码层面已经写了 GPU 路径

在以下文件中可以看到：
- `src/glomap/estimators/global_positioning.cc`
- `src/glomap/estimators/bundle_adjustment.cc`

逻辑是：
- 若定义了 `GLOMAP_CUDA_ENABLED`，且 **Ceres 版本足够新**，并且 Ceres 编译时开启 CUDA，则会设置：
  - `options_.solver_options.dense_linear_algebra_library_type = ceres::CUDA`
  - 或 `ceres::CUDA_SPARSE`（需要 cuDSS）
- 否则即使 `*.use_gpu=1` 也会打印 warning 并回退 CPU。

### 2) 典型现象：为什么会出现 “help 显示 CUDA，但运行时提示 compiled without CUDA support”

根因通常是：`GLOMAP_CUDA_ENABLED` **只定义在 `glomap` 可执行文件目标**，但 `bundle_adjustment.cc / global_positioning.cc` 位于 `colmap_glomap_estimators` 静态库里，库编译单元没有宏，运行时就会打印：
- `... GLOMAP_CUDA_ENABLED not set ... Falling back to CPU ...`

修复要点：让 `GLOMAP_CUDA_ENABLED` 在 `add_subdirectory(estimators/...)` 之前就进入全局编译定义（或对 glomap 的库目标逐个 `target_compile_definitions`）。

### 3) 真正想让 GLOMAP GPU 生效，你需要什么？

- **Ceres ≥ 2.2**（源码检查了版本门槛），并且 **Ceres 需要启用 CUDA**
  - Ubuntu 20.04 默认 `libceres-dev=1.14.0` 太老，不满足门槛
  - 需要你用 **源码编译 Ceres** 或使用 vcpkg/conan 等拉新版本
- （可选）若希望用 `CUDA_SPARSE`，还需要 cuDSS（对应 `CERES_NO_CUDSS` 相关宏门槛）
- 在 COLMAP/GLOMAP 的构建中定义 `GLOMAP_CUDA_ENABLED`（并确保能找到 CUDA toolkit）

> 建议：如果你的目标是“GLOMAP GPU 加速”，优先把依赖链切到 vcpkg（Ceres/Eigen 等统一版本），或像本文一样把 Ceres 安装到独立前缀（例如 `/opt/ceres-2.2.0-cuda`），再确保 `GLOMAP_CUDA_ENABLED` 对所有 glomap 库目标生效，这样最可控。

### 4) 实测：只用 COLMAP 的 database.db 测 GLOMAP GPU（不重新跑特征/匹配）

前提：你已经用 COLMAP 生成了 `database.db`（包含 features + matches）。

```bash
GLOMAP=/root/work/colmap/build_cuda_ceres2/src/glomap/glomap
IMG_DIR="/root/data/city1-CQ02-441-bagcp-riggcp-adj - export"
DB="/root/data/recon_colmap_glomap_city1_ceres22_cuda_fullgpu/database.db"   # 直接复用现成 DB
OUT="/root/data/recon_glomap_only_from_colmapdb_gpu"

$GLOMAP mapper \
  --database_path "$DB" \
  --image_path "$IMG_DIR" \
  --output_path "$OUT" \
  --output_format bin \
  --GlobalPositioning.use_gpu 1 \
  --GlobalPositioning.gpu_index 0 \
  --GlobalPositioning.min_num_images_gpu_solver 50 \
  --BundleAdjustment.use_gpu 1 \
  --BundleAdjustment.gpu_index 0 \
  --BundleAdjustment.min_num_images_gpu_solver 1
```

如何确认 GPU 路径真的启用：
- 在 `glomap_mapper.log` 里能看到（本文已加入显式日志）：
  - `GLOMAP: GlobalPositioning using Ceres CUDA dense solver ...`
  - `GLOMAP: BundleAdjustment using Ceres CUDA dense solver ...`
- 若你看到 `... without cuDSS support ...`：表示 **CUDA dense 已启用**，但 **CUDA sparse（cuDSS）未启用**，属于预期行为（Ceres 2.2 无 `CUDA_SPARSE`）。

> 如果你希望 sparse 求解也尽量走 GPU（`ceres::CUDA_SPARSE` / cuDSS），请看：
> - `doc/COLMAP_GLOMAP_各阶段命令参数_GPU加速详解.md` 的“升级到支持 cuDSS 的 Ceres”章节。

---

## 参考：本次数据集跑通记录

- 数据集：`/root/data/city1-CQ02-441-bagcp-riggcp-adj - export/`（约 280 张 JPG）
- 输出工作目录：`/root/data/recon_colmap_glomap_city1/`
  - `database.db`
  - `feature_extractor.log`
  - `sequential_matcher.log`
  - `glomap_mapper.log`
  - `glomap_model/0/*.bin`

---

## 附录：cuDSS（CUDA_SPARSE）完整 GPU 加速实测（Ceres 2.3 + cuDSS）

> 本附录用于解决并验证以下典型告警（dense 启用但 sparse 回退 CPU）：
>
> - `Requested to use GPU for bundle adjustment, but Ceres was compiled without cuDSS support. Falling back to CPU-based sparse solvers.`
>
> 参考思路与背景可见：[greenbrettmichael 的记录](https://gist.github.com/greenbrettmichael/942fab33e5056c4cf4e0cc3e0fef8e60)。

### A.1 编译并安装 Ceres 2.3 + cuDSS

本仓库脚本（已适配 CUDA 12.8 + sm_120 + cuDSS）：

```bash
cd /root/work/colmap
bash scripts/build_ceres_cuda_2.3.0.sh 2>&1 | tee /tmp/ceres23_build.log
```

验证（应看到 `libcudss.so`）：

```bash
ldd /opt/ceres-2.3.0-cuda-cudss/lib/libceres.so | grep -i cudss
```

### A.2 重新编译 COLMAP/GLOMAP（使用新 Ceres 前缀）

```bash
cd /root/work/colmap
rm -rf build_cuda_ceres23_cudss && mkdir -p build_cuda_ceres23_cudss
cd build_cuda_ceres23_cudss
cmake .. -DCMAKE_PREFIX_PATH=/opt/ceres-2.3.0-cuda-cudss -DCUDA_ENABLED=ON -DCMAKE_CUDA_ARCHITECTURES=120 ...
make -j"$(nproc)"
```

### A.3 小数据集验证（`/root/data/test`）

```bash
COLMAP=/root/work/colmap/build_cuda_ceres23_cudss/src/colmap/exe/colmap
GLOMAP=/root/work/colmap/build_cuda_ceres23_cudss/src/glomap/glomap
IMG_DIR=/root/data/test
OUT=/root/data/test_output
DB=$OUT/database.db
mkdir -p $OUT

$COLMAP feature_extractor --database_path $DB --image_path $IMG_DIR --FeatureExtraction.use_gpu 1
$COLMAP sequential_matcher --database_path $DB --FeatureMatching.use_gpu 1

mkdir -p $OUT/glomap_gpu_sparse
$GLOMAP mapper --database_path $DB --image_path $IMG_DIR --output_path $OUT/glomap_gpu_sparse \
  --GlobalPositioning.use_gpu 1 --GlobalPositioning.min_num_images_gpu_solver 1 \
  --BundleAdjustment.use_gpu 1 --BundleAdjustment.min_num_images_gpu_solver 1 \
  2>&1 | tee $OUT/glomap_gpu_sparse.log

grep -nE \"GLOMAP: (GlobalPositioning|BundleAdjustment) using Ceres CUDA (dense|sparse) solver\" $OUT/glomap_gpu_sparse.log
```

预期：能看到 `CUDA sparse solver`，且不再出现 `without cuDSS support ... Falling back ...`。


