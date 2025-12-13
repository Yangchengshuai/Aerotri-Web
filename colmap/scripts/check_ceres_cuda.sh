#!/usr/bin/env bash
#
# Quick sanity check: whether the Ceres found by CMake / compiler has CUDA enabled.
#
set -euo pipefail

CERES_PREFIX="${CERES_PREFIX:-}"
CXX="${CXX:-c++}"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

cat >"${TMP_DIR}/check.cpp" <<'CPP'
#include <ceres/version.h>
#include <ceres/internal/config.h>
#include <iostream>

int main() {
#if defined(CERES_VERSION_MAJOR) && defined(CERES_VERSION_MINOR) && defined(CERES_VERSION_PATCH)
  std::cout << "CERES_VERSION="
            << CERES_VERSION_MAJOR << "."
            << CERES_VERSION_MINOR << "."
            << CERES_VERSION_PATCH << "\n";
#endif
#if defined(CERES_VERSION_STRING)
  std::cout << "CERES_VERSION_STRING=" << CERES_VERSION_STRING << "\n";
#endif
#ifdef CERES_NO_CUDA
  std::cout << "CERES_NO_CUDA=1\n";
#else
  std::cout << "CERES_NO_CUDA=0\n";
#endif
#ifdef CERES_NO_CUDSS
  std::cout << "CERES_NO_CUDSS=1\n";
#else
  std::cout << "CERES_NO_CUDSS=0\n";
#endif
  return 0;
}
CPP

EXTRA_CMAKE_PREFIX=""
if [[ -n "${CERES_PREFIX}" ]]; then
  EXTRA_CMAKE_PREFIX="-DCMAKE_PREFIX_PATH=${CERES_PREFIX}"
fi

# Use CMake to locate Ceres and emit include/link flags.
cat >"${TMP_DIR}/CMakeLists.txt" <<'CMAKE'
cmake_minimum_required(VERSION 3.17)
project(check_ceres_cuda CXX)
find_package(Ceres REQUIRED)
add_executable(check check.cpp)
if(TARGET Ceres::ceres)
  target_link_libraries(check PRIVATE Ceres::ceres)
else()
  # Older Ceres versions (e.g. 1.x) do not export an imported target.
  target_include_directories(check PRIVATE ${CERES_INCLUDE_DIRS})
  target_link_libraries(check PRIVATE ${CERES_LIBRARIES})
endif()
CMAKE

cmake -S "${TMP_DIR}" -B "${TMP_DIR}/build" ${EXTRA_CMAKE_PREFIX} >/dev/null
cmake --build "${TMP_DIR}/build" -j 1 >/dev/null

echo "== Running check =="
"${TMP_DIR}/build/check"

echo "== ldd (looking for libcudart / cuda libs) =="
ldd "${TMP_DIR}/build/check" | egrep -i 'cudart|cuda|cudss|cublas|cusolver|curand' || true


