#!/bin/bash
# COLMAP CUDA 编译脚本
# 使用 CUDA 12.8 和 RTX 5090 (Compute Capability 12.0)
# Ceres 版本: 1.14.0
# Eigen 版本: 3.3.7

set -e  # 遇到错误立即退出

echo "=========================================="
echo "COLMAP CUDA 编译配置"
echo "=========================================="
echo "CUDA 版本: 12.8"
echo "GPU: RTX 5090 (Compute Capability 12.0)"
echo "Ceres 版本: 1.14.0"
echo "Eigen 版本: 3.3.7"
echo "=========================================="

# 设置 CUDA 路径
export CUDA_HOME=/usr/local/cuda-12.8
export PATH=${CUDA_HOME}/bin:${PATH}
export LD_LIBRARY_PATH=${CUDA_HOME}/lib64:${LD_LIBRARY_PATH}

# 验证 CUDA
if [ ! -f "${CUDA_HOME}/bin/nvcc" ]; then
    echo "错误: 找不到 CUDA 12.8 编译器"
    echo "请检查 CUDA 12.8 是否已正确安装在 ${CUDA_HOME}"
    exit 1
fi

echo "检查 CUDA 编译器..."
nvcc --version

# 检查 GPU
echo ""
echo "检查 GPU..."
nvidia-smi --query-gpu=name,compute_cap --format=csv,noheader | head -1

# 检查依赖
echo ""
echo "检查依赖库..."
if pkg-config --exists eigen3; then
    EIGEN_VERSION=$(pkg-config --modversion eigen3)
    echo "✓ Eigen3: $EIGEN_VERSION"
else
    echo "⚠ 警告: 无法通过 pkg-config 找到 Eigen3，但 CMake 可能会找到"
fi

# 创建构建目录
BUILD_DIR="build_cuda"
if [ -d "$BUILD_DIR" ]; then
    echo ""
    echo "清理旧的构建目录..."
    rm -rf "$BUILD_DIR"
fi
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

echo ""
echo "=========================================="
echo "配置 CMake..."
echo "=========================================="

# CMake 配置
# 注意: RTX 5090 使用 Blackwell 架构，计算能力 12.0
# CUDA 架构设置为 "120" 对应 sm_120
cmake .. \
    -DCMAKE_BUILD_TYPE=Release \
    -DCUDA_ENABLED=ON \
    -DCMAKE_CUDA_COMPILER=${CUDA_HOME}/bin/nvcc \
    -DCMAKE_CUDA_ARCHITECTURES="120" \
    -DCMAKE_CUDA_STANDARD=17 \
    -DCMAKE_CXX_STANDARD=17 \
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

if [ $? -ne 0 ]; then
    echo ""
    echo "错误: CMake 配置失败"
    echo "请检查依赖库是否已正确安装"
    exit 1
fi

echo ""
echo "=========================================="
echo "开始编译..."
echo "=========================================="
echo "这可能需要较长时间，请耐心等待..."

# 编译（使用所有可用 CPU 核心）
NPROC=$(nproc)
echo "使用 $NPROC 个并行任务进行编译..."
make -j${NPROC}

if [ $? -ne 0 ]; then
    echo ""
    echo "错误: 编译失败"
    exit 1
fi

echo ""
echo "=========================================="
echo "编译完成！"
echo "=========================================="
if [ -f "src/colmap/colmap" ]; then
    echo "✓ 可执行文件位置: $(pwd)/src/colmap/colmap"
    echo "✓ 安装命令: cd $(pwd) && sudo make install"
else
    echo "⚠ 警告: 未找到可执行文件，请检查编译日志"
fi
echo "=========================================="

