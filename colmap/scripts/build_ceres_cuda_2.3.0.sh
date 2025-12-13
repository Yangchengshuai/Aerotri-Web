#!/usr/bin/env bash
#
# Build & install Ceres Solver 2.3.0 with CUDA support.
#
# This script is intended for Ubuntu 20.04 + CUDA 12.8 + RTX 5090 (sm_120),
# but should work on other Linux systems if dependencies are satisfied.
#
# Output:
#   Installs into: /opt/ceres-2.3.0-cuda
#
set -euo pipefail

CERES_VERSION="${CERES_VERSION:-2.2.0}"
PREFIX="${PREFIX:-/opt/ceres-${CERES_VERSION}-cuda}"
CUDA_HOME="${CUDA_HOME:-/usr/local/cuda-12.8}"
CUDA_ARCH="${CUDA_ARCH:-120}"
JOBS="${JOBS:-$(nproc)}"
PATCH_CERES_CUDA_ARCHES="${PATCH_CERES_CUDA_ARCHES:-1}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${ROOT_DIR}/build_ceres_${CERES_VERSION}_cuda"
SRC_DIR="${ROOT_DIR}/_deps/ceres-solver-${CERES_VERSION}"

echo "=== Build Ceres ${CERES_VERSION} with CUDA ==="
echo "PREFIX   : ${PREFIX}"
echo "CUDA_HOME: ${CUDA_HOME}"
echo "CUDA_ARCH: ${CUDA_ARCH}"
echo "JOBS     : ${JOBS}"

if [[ ! -x "${CUDA_HOME}/bin/nvcc" ]]; then
  echo "ERROR: nvcc not found at ${CUDA_HOME}/bin/nvcc"
  exit 1
fi

mkdir -p "${ROOT_DIR}/_deps"
if [[ ! -d "${SRC_DIR}/.git" ]]; then
  rm -rf "${SRC_DIR}"
  git clone --depth 1 --branch "${CERES_VERSION}" \
    https://github.com/ceres-solver/ceres-solver.git \
    "${SRC_DIR}"
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

cmake -S "${SRC_DIR}" -B "${BUILD_DIR}" \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX="${PREFIX}" \
  -DBUILD_SHARED_LIBS=ON \
  -DBUILD_TESTING=OFF \
  -DBUILD_EXAMPLES=OFF \
  -DUSE_CUDA=ON \
  -DCMAKE_CUDA_COMPILER="${CUDA_HOME}/bin/nvcc" \
  -DCMAKE_CUDA_ARCHITECTURES="${CUDA_ARCH}" \
  -DCMAKE_CUDA_STANDARD=17 \
  -DCMAKE_CXX_STANDARD=17

cmake --build "${BUILD_DIR}" -j "${JOBS}"
cmake --install "${BUILD_DIR}"

echo "=== Installed Ceres to ${PREFIX} ==="
echo "Next: configure COLMAP with: -DCMAKE_PREFIX_PATH=${PREFIX}"


