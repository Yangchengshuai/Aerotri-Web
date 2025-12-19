#!/usr/bin/env bash
#
# Build & install OpenImageIO from source.
#
# This script is intended for Ubuntu 20.04+, but should work on other Linux
# systems if dependencies are satisfied.
#
# Output:
#   Installs into: /opt/openimageio-<version>
#
set -euo pipefail

# Default to stable 2.3.x version (v2.3.10.1)
# Note: 2.4.x+ requires fmt 9.x, 2.5.x+ and 3.x have stricter requirements
OIIO_VERSION="${OIIO_VERSION:-2.3.10.1}"
OIIO_TAG="${OIIO_TAG:-v${OIIO_VERSION}}"
PREFIX="${PREFIX:-/opt/openimageio-${OIIO_VERSION}}"
JOBS="${JOBS:-$(nproc)}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${ROOT_DIR}/build_openimageio_${OIIO_VERSION}"
SRC_DIR="${ROOT_DIR}/_deps/openimageio-${OIIO_VERSION}"

echo "=== Build OpenImageIO ${OIIO_VERSION} ==="
echo "VERSION  : ${OIIO_VERSION}"
echo "TAG      : ${OIIO_TAG}"
echo "PREFIX   : ${PREFIX}"
echo "JOBS     : ${JOBS}"
echo ""

# Check for required build tools
echo "Checking for required build tools..."
MISSING_DEPS=()
for cmd in cmake git pkg-config; do
  if ! command -v "${cmd}" &> /dev/null; then
    MISSING_DEPS+=("${cmd}")
  fi
done

if [[ ${#MISSING_DEPS[@]} -gt 0 ]]; then
  echo "ERROR: Missing required tools: ${MISSING_DEPS[*]}"
  echo "Please install them with: sudo apt-get install -y cmake git pkg-config build-essential"
  exit 1
fi

# Check for required libraries
echo "Checking for required libraries..."
LIB_DEPS=(
  "libjpeg-dev"
  "libtiff-dev"
  "libpng-dev"
  "libopenexr-dev"
  "libboost-all-dev"
  "libraw-dev"
  "libwebp-dev"
)

MISSING_LIBS=()
for lib in "${LIB_DEPS[@]}"; do
  if ! dpkg -l | grep -q "^ii.*${lib}"; then
    MISSING_LIBS+=("${lib}")
  fi
done

if [[ ${#MISSING_LIBS[@]} -gt 0 ]]; then
  echo "WARNING: Missing library dependencies: ${MISSING_LIBS[*]}"
  echo "Attempting to install them..."
  sudo apt-get update
  sudo apt-get install -y "${MISSING_LIBS[@]}" || {
    echo "ERROR: Failed to install dependencies. Please install manually:"
    echo "  sudo apt-get install -y ${MISSING_LIBS[*]}"
    exit 1
  }
fi

# Clone or update source
mkdir -p "${ROOT_DIR}/_deps"

# Clone fmt library if needed (OpenImageIO 2.3.x may use older fmt or system fmt)
# For 2.3.x, we'll let OpenImageIO handle fmt dependency
FMT_DIR="${ROOT_DIR}/_deps/fmt"

# Clone or update OpenImageIO
if [[ ! -d "${SRC_DIR}/.git" ]]; then
  rm -rf "${SRC_DIR}"
  echo "Cloning OpenImageIO and checking out tag ${OIIO_TAG}..."
  git clone https://ghfast.top/https://github.com/AcademySoftwareFoundation/OpenImageIO.git "${SRC_DIR}"
  cd "${SRC_DIR}"
  git checkout "${OIIO_TAG}"
  cd -
else
  echo "Source directory exists, updating..."
  cd "${SRC_DIR}"
  git fetch origin
  git checkout "${OIIO_TAG}"
  cd -
fi

# OpenImageIO 2.3.x should handle dependencies automatically
# No need to manually link fmt or robin-map

# Clean and create build directory
rm -rf "${BUILD_DIR}"
mkdir -p "${BUILD_DIR}"

echo ""
echo "Configuring CMake..."
echo ""

# Configure CMake
# Note: OpenImageIO 2.5.x uses OpenEXR (Imath 2.x), not Imath 3.x
CMAKE_ARGS=(
  -S "${SRC_DIR}"
  -B "${BUILD_DIR}"
  -DCMAKE_BUILD_TYPE=Release
  -DCMAKE_INSTALL_PREFIX="${PREFIX}"
  -DBUILD_SHARED_LIBS=ON
  -DBUILD_TESTING=OFF
  -DOIIO_BUILD_TESTS=OFF
  -DOIIO_BUILD_TOOLS=ON
  -DOIIO_BUILD_DOCS=OFF
  -DUSE_PYTHON=OFF
  -DUSE_OPENGL=OFF
  -DUSE_QT=OFF
  -DUSE_FIELD3D=OFF
  -DUSE_FFMPEG=OFF
  -DUSE_OPENCV=OFF
  -DUSE_FREETYPE=OFF
  -DUSE_GIF=OFF
  -DUSE_LIBRAW=ON
  -DUSE_WEBP=ON
  -DUSE_OPENJPEG=OFF
  -DUSE_DICOM=OFF
  -DUSE_NUKE=OFF
  -DUSE_OPENVDB=OFF
  -DUSE_PTEX=OFF
  -DUSE_R3DSDK=OFF
  -DUSE_TBB=OFF
  -DUSE_PUGIXML=OFF
  -DUSE_OPENSSL=OFF
  -DSTOP_ON_WARNING=OFF
)

# Try to find OpenEXR and set its root if found
# Ubuntu 20.04's OpenEXR may not have CMake config files, try to find it manually
OPENEXR_CMAKE_DIR=$(find /usr -name "OpenEXRConfig.cmake" -o -name "openexr-config.cmake" 2>/dev/null | head -1 | xargs dirname 2>/dev/null || echo "")
if [[ -n "${OPENEXR_CMAKE_DIR}" ]]; then
  CMAKE_ARGS+=(-DOpenEXR_DIR="${OPENEXR_CMAKE_DIR}")
  echo "Found OpenEXR CMake config at: ${OPENEXR_CMAKE_DIR}"
elif pkg-config --exists OpenEXR 2>/dev/null; then
  # Ubuntu 20.04's OpenEXR is installed in /usr, set root to /usr
  # OpenEXR_ROOT should point to the prefix, not include directory
  CMAKE_ARGS+=(-DOpenEXR_ROOT="/usr")
  echo "Using system OpenEXR at: /usr"
fi

cmake "${CMAKE_ARGS[@]}"

echo ""
echo "Building OpenImageIO..."
echo "This may take a while..."
echo ""

cmake --build "${BUILD_DIR}" -j "${JOBS}"

echo ""
echo "Installing OpenImageIO to ${PREFIX}..."
echo ""

cmake --install "${BUILD_DIR}"

echo ""
echo "=========================================="
echo "=== OpenImageIO Installation Complete ==="
echo "=========================================="
echo "Installed to: ${PREFIX}"
echo ""
echo "Verifying installation..."
if [[ -f "${PREFIX}/lib/libOpenImageIO.so" ]] || [[ -f "${PREFIX}/lib64/libOpenImageIO.so" ]]; then
  echo "✓ SUCCESS: OpenImageIO library found!"
  if [[ -f "${PREFIX}/lib/libOpenImageIO.so" ]]; then
    echo "  Library: ${PREFIX}/lib/libOpenImageIO.so"
  else
    echo "  Library: ${PREFIX}/lib64/libOpenImageIO.so"
  fi
else
  echo "⚠ WARNING: OpenImageIO library not found in expected location"
fi

if [[ -f "${PREFIX}/lib/cmake/OpenImageIO/OpenImageIOConfig.cmake" ]] || [[ -f "${PREFIX}/lib64/cmake/OpenImageIO/OpenImageIOConfig.cmake" ]]; then
  echo "✓ SUCCESS: CMake config file found!"
else
  echo "⚠ WARNING: CMake config file not found"
fi

echo ""
echo "Version information:"
if [[ -f "${PREFIX}/bin/oiiotool" ]]; then
  "${PREFIX}/bin/oiiotool" --version || true
fi

echo ""
echo "Next steps:"
echo "1. Build COLMAP with: -DCMAKE_PREFIX_PATH=${PREFIX}"
echo "2. Or set environment variable: export CMAKE_PREFIX_PATH=${PREFIX}:\$CMAKE_PREFIX_PATH"
echo "=========================================="

