# cuDSS（CUDA_SPARSE）测试报告（COLMAP + GLOMAP）

## 测试目的

验证在安装 cuDSS 后，通过 **Ceres 2.3 + CUDA + cuDSS** 让 GLOMAP 的：
- `GlobalPositioning` 使用 `ceres::CUDA_SPARSE`
- `BundleAdjustment` 使用 `ceres::CUDA_SPARSE`

从而避免常见回退告警：
- `... compiled without cuDSS support. Falling back to CPU-based sparse solvers.`

## 环境信息（本次实测）

- **CUDA**：12.8
- **GPU**：RTX 5090（`sm_120`）
- **cuDSS**：系统安装（库在 `/usr/lib/x86_64-linux-gnu/libcudss/12/`，头文件 `/usr/include/cudss.h`）
- **Ceres（新）**：`/opt/ceres-2.3.0-cuda-cudss`（由仓库脚本编译）
- **COLMAP/GLOMAP（新）**：`/root/work/colmap/build_cuda_ceres23_cudss/`

## 数据集

- **图片目录**：`/root/data/test`
- **图片数量**：76

## 关键命令（可复现）

### 1) 编译安装 Ceres 2.3 + cuDSS

```bash
cd /root/work/colmap
bash scripts/build_ceres_cuda_2.3.0.sh 2>&1 | tee /tmp/ceres23_build.log
ldd /opt/ceres-2.3.0-cuda-cudss/lib/libceres.so | grep -i cudss
```

### 2) 编译 COLMAP/GLOMAP（使用新 Ceres 前缀）

```bash
cd /root/work/colmap
rm -rf build_cuda_ceres23_cudss && mkdir -p build_cuda_ceres23_cudss
cd build_cuda_ceres23_cudss
cmake .. \
  -DCMAKE_BUILD_TYPE=Release \
  -DCUDA_ENABLED=ON \
  -DCMAKE_CUDA_COMPILER=/usr/local/cuda-12.8/bin/nvcc \
  -DCMAKE_CUDA_ARCHITECTURES=120 \
  -DCMAKE_PREFIX_PATH=/opt/ceres-2.3.0-cuda-cudss
make -j"$(nproc)" 2>&1 | tee /tmp/colmap_build_ceres23.log
```

### 3) COLMAP：特征提取与匹配（生成 database.db）

```bash
COLMAP=/root/work/colmap/build_cuda_ceres23_cudss/src/colmap/exe/colmap
IMG_DIR=/root/data/test
OUT=/root/data/test_output
DB=$OUT/database.db
mkdir -p $OUT

$COLMAP feature_extractor \
  --database_path $DB \
  --image_path $IMG_DIR \
  --ImageReader.single_camera 1 \
  --ImageReader.camera_model SIMPLE_RADIAL \
  --FeatureExtraction.use_gpu 1 \
  --FeatureExtraction.gpu_index 0 \
  2>&1 | tee $OUT/feature_extractor.log

$COLMAP sequential_matcher \
  --database_path $DB \
  --SequentialMatching.overlap 20 \
  --FeatureMatching.use_gpu 1 \
  --FeatureMatching.gpu_index 0 \
  2>&1 | tee $OUT/sequential_matcher.log
```

### 4) GLOMAP：mapper（GPU sparse / cuDSS）

```bash
GLOMAP=/root/work/colmap/build_cuda_ceres23_cudss/src/glomap/glomap
OUT_MODEL=$OUT/glomap_gpu_sparse
mkdir -p $OUT_MODEL

$GLOMAP mapper \
  --database_path $DB \
  --image_path $IMG_DIR \
  --output_path $OUT_MODEL \
  --output_format bin \
  --GlobalPositioning.use_gpu 1 \
  --GlobalPositioning.gpu_index 0 \
  --GlobalPositioning.min_num_images_gpu_solver 1 \
  --BundleAdjustment.use_gpu 1 \
  --BundleAdjustment.gpu_index 0 \
  --BundleAdjustment.min_num_images_gpu_solver 1 \
  2>&1 | tee $OUT/glomap_gpu_sparse.log
```

## 关键验证点（本次实测结果）

### A) cuDSS 版（Ceres 2.3 + cuDSS）

日志文件：`/root/data/test_output/glomap_gpu_sparse.log`

- **GlobalPositioning**：
  - `GLOMAP: GlobalPositioning using Ceres CUDA sparse solver (num_images=76, ...)`
- **BundleAdjustment**：
  - 多次出现 `GLOMAP: BundleAdjustment using Ceres CUDA sparse solver ...`
- **无回退**：
  - 不出现 `without cuDSS support ... Falling back ...`

### B) 对比：旧版（Ceres 2.2 dense-only）

日志文件：`/root/data/test_output/glomap_gpu_dense_only.log`

明确出现回退：
- `Requested to use GPU for global positioning, but Ceres was compiled without cuDSS support. Falling back to CPU-based sparse solvers.`
- `Requested to use GPU for bundle adjustment, but Ceres was compiled without cuDSS support. Falling back to CPU-based sparse solvers.`

## 性能对比（本次小数据集）

> 该数据集较小（76 张），主要用于功能验证；性能差异不一定显著。

- **cuDSS 版**：wall time 约 33.13s（从日志时间戳估算）
- **dense-only 版**：wall time 约 34.36s（从日志时间戳估算）

## 输出产物

### cuDSS 版输出

目录：`/root/data/test_output/glomap_gpu_sparse/0/`
- `cameras.bin`
- `images.bin`
- `points3D.bin`
- `frames.bin`
- `rigs.bin`

### dense-only 版输出

目录：`/root/data/test_output/glomap_gpu_dense_only/0/`
- 同上


