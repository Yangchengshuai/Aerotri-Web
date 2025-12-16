# COLMAP / GLOMAP 各阶段命令、参数解释与 GPU 加速（CUDA 12.8 + RTX 5090 / sm_120）

> 目标：给“可直接复制执行”的命令与参数解释，明确 **每个阶段是否真的能用 GPU**、如何选择 GPU、如何从日志验证是否在跑 GPU，以及常见踩坑（尤其是 Ceres / cuDSS）。

---

## 0. 术语速查：哪些算“GPU 加速”

- **COLMAP SIFT 提取/匹配 GPU**：由 SiftGPU / CUDA 路径加速，参数是 `FeatureExtraction.use_gpu` / `FeatureMatching.use_gpu`
- **COLMAP Mapper / BA GPU**：由 Ceres 的 CUDA 路径加速，参数是 `Mapper.ba_use_gpu`
- **GLOMAP GlobalPositioning / BA GPU**：由 Ceres 的 CUDA 路径加速，参数是 `GlobalPositioning.use_gpu` / `BundleAdjustment.use_gpu`
- **重要限制（非常常见）**：
  - Ceres **CUDA dense** 与 **CUDA sparse（cuDSS）** 是两条不同能力线
  - 你可能看到 “CUDA dense 启用” 但 “cuDSS 不支持 → sparse 回退 CPU/CHOLMOD”，这不表示 GPU 完全没用，而是 **只启用了 dense 路径**

---

## 1. 环境要求（本文假设）

- **CUDA**：12.8（`nvcc 12.8.93`）
- **GPU**：RTX 5090 → **sm_120** → `-DCMAKE_CUDA_ARCHITECTURES=120`
- **Ceres（GLOMAP GPU 必需）**：**≥ 2.2 且用 CUDA 编译**
  - 推荐本文前缀：`/opt/ceres-2.2.0-cuda`

---

## 2. 如何验证 “Ceres 真的是 CUDA 版”

### 2.1 直接看动态库依赖（最直观）

```bash
ldd /opt/ceres-2.2.0-cuda/lib/libceres.so | egrep -i 'cudart|cublas|cusolver|cusparse'
```

预期至少能看到：
- `libcudart.so.12`
- `libcublas.so.12`
- `libcusolver.so.11`
- `libcusparse.so.12`

### 2.2 用仓库脚本自检（推荐）

```bash
CERES_PREFIX=/opt/ceres-2.2.0-cuda /root/work/colmap/scripts/check_ceres_cuda.sh
```

---

## 3. COLMAP：特征提取 → 匹配 →（可选）增量建图

> 你只想“测试 GLOMAP GPU”时，可以只做 **特征提取/匹配** 生成 `database.db`，然后直接跳到第 4 节运行 `glomap mapper`。

### 3.1 特征提取：`feature_extractor`

```bash
COLMAP=/root/work/colmap/build_cuda_ceres2/src/colmap/exe/colmap
IMG_DIR="/root/data/city1-CQ02-441-bagcp-riggcp-adj - export"
DB="/root/data/recon_colmap_stage/database.db"

$COLMAP feature_extractor \
  --database_path "$DB" \
  --image_path "$IMG_DIR" \
  --ImageReader.single_camera 1 \
  --ImageReader.camera_model SIMPLE_RADIAL \
  --FeatureExtraction.use_gpu 1 \
  --FeatureExtraction.gpu_index 0 \
  --FeatureExtraction.num_threads 8 \
  --SiftExtraction.max_image_size 2000 \
  --SiftExtraction.max_num_features 4096
```

- **`FeatureExtraction.use_gpu`**：是否用 GPU 做 SIFT（1/0）
- **`FeatureExtraction.gpu_index`**：选择 GPU（0/1/...；-1 表示自动）
- **`SiftExtraction.max_image_size`**：缩放上限（降低可显著提速）
- **`SiftExtraction.max_num_features`**：每张图最多特征数

### 3.2 匹配（序列）：`sequential_matcher`

```bash
$COLMAP sequential_matcher \
  --database_path "$DB" \
  --SequentialMatching.overlap 20 \
  --FeatureMatching.use_gpu 1 \
  --FeatureMatching.gpu_index 0
```

- **`SequentialMatching.overlap`**：序列窗口大小（越大越慢但更稳）
- **`FeatureMatching.use_gpu`**：是否用 GPU 加速匹配

### 3.3（可选）COLMAP 增量建图：`mapper`

```bash
OUT_SPARSE="/root/data/recon_colmap_stage/colmap_sparse"

$COLMAP mapper \
  --database_path "$DB" \
  --image_path "$IMG_DIR" \
  --output_path "$OUT_SPARSE" \
  --Mapper.ba_use_gpu 1 \
  --Mapper.ba_gpu_index 0
```

> 注意：COLMAP 的 BA GPU 是否真正启用，取决于你的 Ceres 是否 CUDA 版、以及数据规模/阈值等。

---

## 4. GLOMAP：直接复用 COLMAP database.db 测 GPU 加速（推荐测试方式）

### 4.1 最短命令（只依赖 DB + 图像目录）

```bash
GLOMAP=/root/work/colmap/build_cuda_ceres2/src/glomap/glomap
IMG_DIR="/root/data/city1-CQ02-441-bagcp-riggcp-adj - export"
DB="/root/data/recon_colmap_glomap_city1_ceres22_cuda_fullgpu/database.db"
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

### 4.2 参数解释（GPU 相关）

- **`GlobalPositioning.use_gpu`**：全局定位阶段启用 GPU（基于 Ceres CUDA）
- **`BundleAdjustment.use_gpu`**：BA 阶段启用 GPU（基于 Ceres CUDA）
- **`*.gpu_index`**：选择 GPU（字符串形式，支持 CSV，例如 `"0,1"`；一般用 `0`）
- **`*.min_num_images_gpu_solver`**：启用 GPU solver 的图片数阈值
  - 如果你想“强制验证 GPU 分支是否生效”，建议临时设置为 `1`
  - 正式跑可恢复默认（当前默认是 50）

### 4.3 如何确认真的在跑 GPU（看日志）

在 `glomap_mapper.log` 中搜索：

```bash
grep -nE "GLOMAP: (GlobalPositioning|BundleAdjustment) using Ceres CUDA" glomap_mapper.log
```

预期能看到类似：
- `GLOMAP: GlobalPositioning using Ceres CUDA dense solver ...`
- `GLOMAP: BundleAdjustment using Ceres CUDA dense solver ...`

### 4.4 cuDSS（CUDA sparse）相关说明

如果日志出现：
- `... without cuDSS support. Falling back to CPU-based sparse solvers.`

含义是：
- **CUDA dense 已启用**（仍能加速部分线性代数）
- **CUDA sparse（cuDSS）未启用** → 稀疏求解仍走 CPU（SuiteSparse/CHOLMOD）

想要 “CUDA sparse”：
- 需要 **Ceres 版本支持 `ceres::CUDA_SPARSE`** 并且能找到 **cuDSS**

### 4.5 小结：当前 Ceres **无 cuDSS** 时的真实运行模式

- **前提（本项目当前配置）**  
  - 使用的 Ceres：**2.2.0 + CUDA**，只支持 **CUDA dense**，**不包含 CUDA sparse / cuDSS**。  
- **当你设置 `GlobalPositioning.use_gpu = 1` / `BundleAdjustment.use_gpu = 1` 时：**
  - GLOMAP 会启用 **Ceres CUDA dense solver（跑在 GPU 上）**：  
    - 日志里能看到：`GLOMAP: GlobalPositioning/BundleAdjustment using Ceres CUDA dense solver ...`  
  - 但由于 **缺少 cuDSS**，**稀疏求解部分会回退到 CPU（CHOLMOD 等）**：  
    - 日志里会看到：`without cuDSS support. Falling back to CPU-based sparse solvers.`  
- **这意味着：**
  - GlobalPositioning 和 BundleAdjustment 两个阶段，实际是 **“GPU dense + CPU sparse 的混合模式”**；  
  - 不是“完全 GPU”，也不是“完全 CPU”，而是 **部分算子在 GPU、稀疏线性求解仍在 CPU**；  
  - 在中大型问题上仍然可以获得一定加速效果，但**想要“更彻底的 GPU sparse 加速”需要升级到支持 `ceres::CUDA_SPARSE` + cuDSS 的 Ceres 版本**（见第 7 节）。

---

## 7. 升级到支持 cuDSS 的 Ceres（启用更完整的 sparse GPU / `ceres::CUDA_SPARSE`）

> 适用场景：你希望 GLOMAP 的 sparse 求解也尽量走 GPU，而不是只启用 CUDA dense。
>
> 现实情况：Ceres 2.2.0 可以启用 CUDA dense，但**不包含 `ceres::CUDA_SPARSE`**；要用 cuDSS，通常需要更新到更新版本的 Ceres（例如后续版本/主干）。

### 7.1 第一步：确认系统是否安装了 cuDSS

> 在很多环境里，cuDSS **不是 CUDA Toolkit 默认就有的**（可能需要单独安装/预览版包）。

```bash
ls -la /usr/local/cuda-12.8/lib64/libcudss.so* 2>/dev/null || true
ls -la /usr/local/cuda-12.8/include/cudss*.h 2>/dev/null || true
ldconfig -p | grep -i cudss || true
```

如果没有任何输出：说明当前机器还没装 cuDSS（先安装 cuDSS 再继续）。

### 7.2 第二步：用“支持 cuDSS 的 Ceres 版本”源码编译安装

由于 Ceres 2.2.0 的 release tag 不含 cuDSS，建议采用：
- **Ceres 官方后续版本**（如果已发布并明确包含 cuDSS 支持）
- 或 **Ceres 主干（master）** 的某个 commit（可复现性稍弱，但能拿到最新特性）

编译关键点：
- 仍然需要启用 CUDA：`-DUSE_CUDA=ON`
- 让 CMake 能找到 cuDSS 的 **include** 与 **library**
  - 如果自动探测失败，常见做法是显式指定路径（示例变量名以你下载包为准）：

```bash
cmake -S <ceres-src> -B <ceres-build> \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX=/opt/ceres-<new>-cuda-cudss \
  -DUSE_CUDA=ON \
  -DCMAKE_CUDA_ARCHITECTURES=120 \
  -DCMAKE_CUDA_STANDARD=17 \
  -DCMAKE_CXX_STANDARD=17 \
  -DCUDSS_INCLUDE_DIR=/path/to/cudss/include \
  -DCUDSS_LIBRARY=/path/to/cudss/lib/libcudss.so
cmake --build <ceres-build> -j"$(nproc)"
cmake --install <ceres-build>
```

> 注意：不同 cuDSS 安装包/版本的路径可能不同，你可以用 `find / -name 'libcudss.so*'` 定位真实路径，再填进 CMake。

### 7.3 第三步：验证 Ceres 是否真的启用了 cuDSS / CUDA_SPARSE

**(A) 动态库依赖验证**

```bash
ldd /opt/ceres-<new>-cuda-cudss/lib/libceres.so | egrep -i 'cudss|cudart|cublas|cusolver|cusparse' || true
```

预期至少能看到 `libcudss.so`（以及 `libcudart.so / libcublas.so / libcusolver.so / libcusparse.so`）。

**(B) API 能力验证（能否编译使用 `ceres::CUDA_SPARSE`）**

最可靠的方式是写一个最小程序，在你的新 Ceres 头文件里设置：
- `options.sparse_linear_algebra_library_type = ceres::CUDA_SPARSE;`

如果能编译通过，基本可确认此版本包含 CUDA_SPARSE 能力。

### 7.4 第四步：让 COLMAP/GLOMAP 使用新 Ceres

重新配置并编译 COLMAP 时把前缀加进去：

```bash
cmake .. -DCMAKE_PREFIX_PATH=/opt/ceres-<new>-cuda-cudss ...
```

之后再跑 GLOMAP：
- 你应该不再看到 `without cuDSS support ...` 的回退 warning
- 且日志中仍会保留 `GLOMAP: ... using Ceres CUDA ...` 的启用标记

### 7.5 实测：用 `/root/data/test` 小数据集验证 CUDA_SPARSE（含对比）

> 本节是“可直接复制执行”的最短验证路径：先用 COLMAP 生成 `database.db`，再用 GLOMAP mapper 验证 **CUDA dense + CUDA sparse（cuDSS）** 是否启用，并与旧版 Ceres 2.2（dense-only）对比。

#### 7.5.1 编译 Ceres 2.3 + cuDSS（推荐固定 commit，可复现）

```bash
cd /root/work/colmap
bash scripts/build_ceres_cuda_2.3.0.sh 2>&1 | tee /tmp/ceres23_build.log
```

完成后重点确认：

```bash
ldd /opt/ceres-2.3.0-cuda-cudss/lib/libceres.so | grep -i cudss
```

#### 7.5.2 用新 Ceres 重新编译 COLMAP/GLOMAP

```bash
cd /root/work/colmap
rm -rf build_cuda_ceres23_cudss && mkdir -p build_cuda_ceres23_cudss
cd build_cuda_ceres23_cudss
cmake .. \
  -DCMAKE_BUILD_TYPE=Release \
  -DCUDA_ENABLED=ON \
  -DCMAKE_CUDA_COMPILER=/usr/local/cuda-12.8/bin/nvcc \
  -DCMAKE_CUDA_ARCHITECTURES=120 \
  -DCMAKE_CUDA_STANDARD=17 \
  -DCMAKE_CXX_STANDARD=17 \
  -DCMAKE_PREFIX_PATH=/opt/ceres-2.3.0-cuda-cudss \
  -DGUI_ENABLED=ON \
  -DOPENGL_ENABLED=ON \
  -DSIMD_ENABLED=ON \
  -DOPENMP_ENABLED=ON \
  -DCGAL_ENABLED=ON \
  -DLSD_ENABLED=ON \
  -DDOWNLOAD_ENABLED=ON \
  -DTESTS_ENABLED=OFF \
  -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
  -DCMAKE_CUDA_FLAGS="-Wno-deprecated-gpu-targets --expt-relaxed-constexpr"
make -j"$(nproc)" 2>&1 | tee /tmp/colmap_build_ceres23.log
```

产物路径（本文实测）：
- `COLMAP=/root/work/colmap/build_cuda_ceres23_cudss/src/colmap/exe/colmap`
- `GLOMAP=/root/work/colmap/build_cuda_ceres23_cudss/src/glomap/glomap`

#### 7.5.3 COLMAP 特征提取 + 匹配（生成 `database.db`）

```bash
IMG_DIR="/root/data/test"
OUT="/root/data/test_output"
DB="${OUT}/database.db"
mkdir -p "${OUT}"

$COLMAP feature_extractor \
  --database_path "$DB" \
  --image_path "$IMG_DIR" \
  --ImageReader.single_camera 1 \
  --ImageReader.camera_model SIMPLE_RADIAL \
  --FeatureExtraction.use_gpu 1 \
  --FeatureExtraction.gpu_index 0 \
  --SiftExtraction.max_image_size 2000 \
  --SiftExtraction.max_num_features 4096 \
  2>&1 | tee "${OUT}/feature_extractor.log"

$COLMAP sequential_matcher \
  --database_path "$DB" \
  --SequentialMatching.overlap 20 \
  --FeatureMatching.use_gpu 1 \
  --FeatureMatching.gpu_index 0 \
  2>&1 | tee "${OUT}/sequential_matcher.log"
```

#### 7.5.4 GLOMAP mapper（cuDSS / CUDA_SPARSE 版）

```bash
OUT_MODEL="${OUT}/glomap_gpu_sparse"
mkdir -p "${OUT_MODEL}"

$GLOMAP mapper \
  --database_path "$DB" \
  --image_path "$IMG_DIR" \
  --output_path "$OUT_MODEL" \
  --output_format bin \
  --GlobalPositioning.use_gpu 1 \
  --GlobalPositioning.gpu_index 0 \
  --GlobalPositioning.min_num_images_gpu_solver 1 \
  --BundleAdjustment.use_gpu 1 \
  --BundleAdjustment.gpu_index 0 \
  --BundleAdjustment.min_num_images_gpu_solver 1 \
  2>&1 | tee "${OUT}/glomap_gpu_sparse.log"
```

验证关键日志（应看到 CUDA sparse solver）：

```bash
grep -nE "GLOMAP: (GlobalPositioning|BundleAdjustment) using Ceres CUDA (dense|sparse) solver" \
  "${OUT}/glomap_gpu_sparse.log"
```

预期至少包含：
- `GLOMAP: GlobalPositioning using Ceres CUDA sparse solver ...`
- `GLOMAP: BundleAdjustment using Ceres CUDA sparse solver ...`

#### 7.5.5 对比：旧版 Ceres 2.2（dense-only，sparse 回退 CPU）

```bash
GLOMAP_OLD=/root/work/colmap/build_cuda_ceres2/src/glomap/glomap
OUT_MODEL_OLD="${OUT}/glomap_gpu_dense_only"
mkdir -p "${OUT_MODEL_OLD}"

$GLOMAP_OLD mapper \
  --database_path "$DB" \
  --image_path "$IMG_DIR" \
  --output_path "$OUT_MODEL_OLD" \
  --output_format bin \
  --GlobalPositioning.use_gpu 1 \
  --GlobalPositioning.min_num_images_gpu_solver 1 \
  --BundleAdjustment.use_gpu 1 \
  --BundleAdjustment.min_num_images_gpu_solver 1 \
  2>&1 | tee "${OUT}/glomap_gpu_dense_only.log"

grep -nE "without cuDSS support|Falling back to CPU-based sparse solvers" \
  "${OUT}/glomap_gpu_dense_only.log"
```

---

## 5. 输出产物（GLOMAP）

默认 `--output_format bin`：
- `$OUT/0/cameras.bin`
- `$OUT/0/images.bin`
- `$OUT/0/points3D.bin`
- `$OUT/0/frames.bin`
- `$OUT/0/rigs.bin`

---

## 6. 常见问题（GPU 相关）

### 6.1 “glomap --help 显示 compiled with CUDA，但运行时说 GLOMAP_CUDA_ENABLED not set”

原因：`GLOMAP_CUDA_ENABLED` 只加到了 `glomap` 可执行文件目标，但真正做优化的库目标没带这个宏。

修复：确保 `GLOMAP_CUDA_ENABLED` 在编译 glomap 的 **estimators/processors/controllers** 等库时同样生效。

### 6.2 “启用 GPU 后仍然看到 CHOLMOD / sparse solver 的 warning”

这通常说明你当前只启用了 **CUDA dense**，而 **CUDA sparse（cuDSS）** 未启用，属于预期。


