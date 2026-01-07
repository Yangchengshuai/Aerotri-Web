#!/bin/bash
# Build PyTorch from source for RTX 5090 (Blackwell sm_120)
# Based on: https://discuss.vllm.ai/t/vllm-on-rtx5090-working-gpu-setup-with-torch-2-9-0-cu128/1492
#
# WARNING: This takes 2-4 hours and requires significant disk space (~20GB)

set -e

GS_ENV="/root/work/gs_workspace/gs_env"
PYTORCH_SRC="/tmp/pytorch"
CUDA_VERSION="12.8"

echo "=========================================="
echo "Building PyTorch from Source for RTX 5090"
echo "=========================================="
echo "This will take 2-4 hours and require ~20GB disk space"
echo "Press Ctrl+C to cancel, or wait 5 seconds to continue..."
sleep 5

# Activate environment
source "${GS_ENV}/bin/activate"

# Check prerequisites
echo "[1/7] Checking prerequisites..."
command -v git >/dev/null 2>&1 || { echo "✗ git not found"; exit 1; }
command -v cmake >/dev/null 2>&1 || { echo "✗ cmake not found"; exit 1; }
command -v nvcc >/dev/null 2>&1 || { echo "✗ nvcc not found"; exit 1; }
nvcc --version | grep -q "release ${CUDA_VERSION}" || { echo "⚠ CUDA version mismatch (expected ${CUDA_VERSION})"; }
echo "✓ Prerequisites OK"

# Clone/update PyTorch
echo "[2/7] Cloning/updating PyTorch repository..."
if [ ! -d "${PYTORCH_SRC}" ]; then
    echo "  Cloning PyTorch (this may take a while)..."
    git clone --recursive --depth 1 --branch main https://github.com/pytorch/pytorch.git "${PYTORCH_SRC}"
else
    echo "  Updating existing PyTorch repository..."
    cd "${PYTORCH_SRC}"
    git fetch origin
    git checkout main
    git submodule update --init --recursive
    cd -
fi

# Install build dependencies
echo "[3/7] Installing build dependencies..."
pip install -q ninja pyyaml setuptools wheel

# Set build environment for Blackwell (sm_120)
echo "[4/7] Setting build environment for Blackwell (sm_120)..."
export TORCH_CUDA_ARCH_LIST="12.0"
export CMAKE_CUDA_ARCHITECTURES=120
export MAX_JOBS=$(nproc)
export USE_CUDA=1
export USE_CUDNN=1
export USE_NCCL=0  # Disable NCCL if not needed
export BUILD_TEST=0  # Skip tests to speed up build

# Build PyTorch
echo "[5/7] Building PyTorch (this will take 2-4 hours)..."
echo "  Build configuration:"
echo "    - CUDA architectures: ${TORCH_CUDA_ARCH_LIST}"
echo "    - Max jobs: ${MAX_JOBS}"
echo "    - CUDA: ${CUDA_VERSION}"
echo ""
echo "  Starting build at $(date)..."
cd "${PYTORCH_SRC}"

# Use setup.py for installation
python setup.py build develop

cd -

# Verify installation
echo "[6/7] Verifying PyTorch installation..."
python -c "
import torch
print(f'PyTorch version: {torch.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'CUDA version: {torch.version.cuda}')
    print(f'Device: {torch.cuda.get_device_name(0)}')
    capability = torch.cuda.get_device_capability(0)
    print(f'Compute capability: {capability[0]}.{capability[1]}')
    
    # Test CUDA operations
    x = torch.randn(10, 10).cuda()
    y = torch.randn(10, 10).cuda()
    z = torch.matmul(x, y)
    print('✓ CUDA operations working')
"

echo "[7/7] Build complete!"
echo ""
echo "Next steps:"
echo "1. Run: /root/work/gs_workspace/fix_rtx5090_pytorch.sh"
echo "2. This will recompile 3DGS CUDA extensions with sm_120 support"

