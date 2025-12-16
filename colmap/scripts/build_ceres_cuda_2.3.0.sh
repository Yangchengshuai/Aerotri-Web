#!/usr/bin/env bash
#
# Build & install Ceres Solver 2.3.0 with CUDA + cuDSS support.
#
# This script is intended for Ubuntu 20.04 + CUDA 12.8 + RTX 5090 (sm_120),
# but should work on other Linux systems if dependencies are satisfied.
#
# Output:
#   Installs into: /opt/ceres-2.3.0-cuda-cudss
#
set -euo pipefail

CERES_VERSION="${CERES_VERSION:-2.3.0-dev}"
CERES_COMMIT="${CERES_COMMIT:-46b4b3b002994ddb9d6fc72268c3e271243cd1df}"
PREFIX="${PREFIX:-/opt/ceres-2.3.0-cuda-cudss}"
CUDA_HOME="${CUDA_HOME:-/usr/local/cuda-12.8}"
CUDA_ARCH="${CUDA_ARCH:-120}"
JOBS="${JOBS:-$(nproc)}"
PATCH_CERES_CUDA_ARCHES="${PATCH_CERES_CUDA_ARCHES:-1}"
CUDSS_ROOT="${CUDSS_ROOT:-/usr/lib/x86_64-linux-gnu/libcudss/12}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${ROOT_DIR}/build_ceres_${CERES_VERSION}_cuda_cudss"
SRC_DIR="${ROOT_DIR}/_deps/ceres-solver-${CERES_VERSION}"

echo "=== Build Ceres ${CERES_VERSION} with CUDA + cuDSS ==="
echo "VERSION  : ${CERES_VERSION}"
echo "COMMIT   : ${CERES_COMMIT}"
echo "PREFIX   : ${PREFIX}"
echo "CUDA_HOME: ${CUDA_HOME}"
echo "CUDA_ARCH: ${CUDA_ARCH}"
echo "CUDSS_ROOT: ${CUDSS_ROOT}"
echo "JOBS     : ${JOBS}"

if [[ ! -x "${CUDA_HOME}/bin/nvcc" ]]; then
  echo "ERROR: nvcc not found at ${CUDA_HOME}/bin/nvcc"
  exit 1
fi

mkdir -p "${ROOT_DIR}/_deps"
if [[ ! -d "${SRC_DIR}/.git" ]]; then
  rm -rf "${SRC_DIR}"
  echo "Cloning Ceres Solver and checking out commit ${CERES_COMMIT}..."
  git clone https://ghfast.top/https://github.com/ceres-solver/ceres-solver.git "${SRC_DIR}"
  cd "${SRC_DIR}"
  git checkout "${CERES_COMMIT}"
  cd -
fi

# Ceres 2.2.0 hardcodes CMAKE_CUDA_ARCHITECTURES to 50;60;70;80 when using
# CUDAToolkit and CMake >= 3.18, which is incompatible with newer GPUs like
# RTX 5090 (sm_120). Patch it to only set a default when the user did not
# specify an architecture.
if [[ "${PATCH_CERES_CUDA_ARCHES}" == "1" ]]; then
  CERES_CMAKE="${SRC_DIR}/CMakeLists.txt"
  if grep -q 'set(CMAKE_CUDA_ARCHITECTURES "50;60;70;80")' "${CERES_CMAKE}"; then
    CERES_CMAKE_PATH="${CERES_CMAKE}" python3 - <<'PY'
import os
import pathlib, re
p = pathlib.Path(os.environ["CERES_CMAKE_PATH"])
s = p.read_text()
pat = r'(?m)^(\s*)set\(CMAKE_CUDA_ARCHITECTURES "50;60;70;80"\)\s*$\n^(\s*)message\("-- Setting CUDA Architecture to \$\{CMAKE_CUDA_ARCHITECTURES\}"\)\s*$\n'
m = re.search(pat, s)
if not m:
    raise SystemExit("Failed to find expected CUDA_ARCHITECTURES set/message lines to patch in Ceres CMakeLists.txt")
indent = m.group(1)
indent_msg = m.group(2)
replacement = (
    f'{indent}if(NOT DEFINED CMAKE_CUDA_ARCHITECTURES OR CMAKE_CUDA_ARCHITECTURES STREQUAL \"\")\\n'
    f'{indent}  set(CMAKE_CUDA_ARCHITECTURES \"50;60;70;80\")\\n'
    f'{indent}endif()\\n'
    f'{indent_msg}message(\"-- Setting CUDA Architecture to ${{CMAKE_CUDA_ARCHITECTURES}}\")\\n'
)
s2 = re.sub(pat, replacement, s, count=1)
p.write_text(s2)
print("Patched Ceres CMakeLists.txt to respect user-provided CMAKE_CUDA_ARCHITECTURES")
PY
  fi
fi

rm -rf "${BUILD_DIR}"
mkdir -p "${BUILD_DIR}"

echo ""
echo "Configuring CMake with cuDSS support..."
echo "CMake will search for cuDSS in: ${CUDSS_ROOT}"
echo ""

cmake -S "${SRC_DIR}" -B "${BUILD_DIR}" \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX="${PREFIX}" \
  -DCMAKE_PREFIX_PATH="${CUDSS_ROOT}" \
  -DBUILD_SHARED_LIBS=ON \
  -DBUILD_TESTING=OFF \
  -DBUILD_EXAMPLES=OFF \
  -DUSE_CUDA=ON \
  -DCMAKE_CUDA_COMPILER="${CUDA_HOME}/bin/nvcc" \
  -DCMAKE_CUDA_ARCHITECTURES="${CUDA_ARCH}" \
  -DCMAKE_CUDA_STANDARD=17 \
  -DCMAKE_CXX_STANDARD=17

echo ""
echo "Checking CMake output for cuDSS detection..."
if grep -q "cudss" "${BUILD_DIR}/CMakeCache.txt" 2>/dev/null; then
  echo "✓ cuDSS references found in CMake cache"
  grep -i cudss "${BUILD_DIR}/CMakeCache.txt" | head -10
else
  echo "⚠ WARNING: No cuDSS references found in CMake cache"
  echo "  This may mean cuDSS was not detected by CMake"
fi
echo ""

cmake --build "${BUILD_DIR}" -j "${JOBS}"
cmake --install "${BUILD_DIR}"

echo ""
echo "=========================================="
echo "=== Ceres Installation Complete ==="
echo "=========================================="
echo "Installed to: ${PREFIX}"
echo ""
echo "Verifying cuDSS linkage..."
if ldd "${PREFIX}/lib/libceres.so" | grep -q cudss; then
  echo "✓ SUCCESS: libceres.so is linked with cuDSS!"
  ldd "${PREFIX}/lib/libceres.so" | grep cudss
else
  echo "⚠ WARNING: libceres.so does NOT appear to be linked with cuDSS"
  echo "  This may be expected if Ceres doesn't dynamically link cuDSS"
fi
echo ""
echo "Next steps:"
echo "1. Verify with: CERES_PREFIX=${PREFIX} /root/work/colmap/scripts/check_ceres_cuda.sh"
echo "2. Build COLMAP with: -DCMAKE_PREFIX_PATH=${PREFIX}"
echo "=========================================="


