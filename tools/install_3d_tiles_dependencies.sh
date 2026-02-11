#!/bin/bash
# Install dependencies for 3D Tiles conversion

set -e

echo "=========================================="
echo "Installing 3D Tiles Dependencies"
echo "=========================================="
echo ""

# Install system dependencies
echo "1. Installing system packages..."
sudo apt-get update -qq
sudo apt-get install -y -qq \
    libcairo2-dev \
    libpango1.0-dev \
    libglib2.0-dev \
    libimage-exiftool-perl \
    nodejs \
    npm

echo ""
echo "2. Installing obj2gltf globally..."
sudo npm install -g --silent obj2gltf

echo ""
echo "3. Installing 3d-tiles-tools (gltf-to-3dtiles)..."
sudo npm install -g --silent 3d-tiles-tools

echo ""
echo "4. Installing Python packages..."
pip install -q gltf-to-3d-tiles tensorboard

echo ""
echo "=========================================="
echo "Verifying installations..."
echo "=========================================="
echo ""

# Verify obj2gltf
echo -n "obj2gltf: "
if which obj2gltf >/dev/null 2>&1; then
    VERSION=$(obj2gltf --version 2>/dev/null | head -1 || echo "unknown")
    echo "✓ INSTALLED ($VERSION)"
else
    echo "✗ FAILED"
    exit 1
fi

# Verify gltf-to-3dtiles
echo -n "gltf-to-3dtiles: "
if which gltf-to-3dtiles >/dev/null 2>&1; then
    echo "✓ INSTALLED"
else
    echo "✗ FAILED"
    exit 1
fi

# Verify exiftool
echo -n "exiftool: "
if which exiftool >/dev/null 2>&1; then
    VERSION=$(exiftool -ver 2>/dev/null || echo "unknown")
    echo "✓ INSTALLED ($VERSION)"
else
    echo "✗ FAILED"
    exit 1
fi

# Verify Python packages
echo ""
echo "Python packages:"
python3 -c "
import importlib
packages = {
    'gltf_to_3d_tiles': 'gltf-to-3d-tiles',
    'tensorboard': 'tensorboard',
}
for name, pkg in packages.items():
    try:
        mod = importlib.import_module(name)
        version = getattr(mod, '__version__', 'installed')
        print(f'  ✓ {pkg} ({version})')
    except ImportError as e:
        print(f'  ✗ {pkg} - {e}')
        exit(1)
"

echo ""
echo "=========================================="
echo "✓ All dependencies installed successfully!"
echo "=========================================="
echo ""
echo "Environment variables (optional):"
echo "  export OBJ2GLTF_PATH=$(which obj2gltf)"
echo "  export GLTF_TO_3DTILES_PATH=$(which gltf-to-3dtiles)"
echo "  export EXIFTOOL_PATH=$(which exiftool)"
echo ""
