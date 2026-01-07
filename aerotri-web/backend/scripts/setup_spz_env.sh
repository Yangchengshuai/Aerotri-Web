#!/bin/bash
# Setup script for SPZ Python bindings conda environment
# This script creates a conda environment with Python 3.10 and installs SPZ Python bindings

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SPZ_DIR="${SCRIPT_DIR}/../third_party/spz"
ENV_NAME="spz-env"
PYTHON_VERSION="3.10"

echo "=========================================="
echo "Setting up SPZ Python bindings environment"
echo "=========================================="

# Check if conda is available
if ! command -v conda &> /dev/null; then
    echo "Error: conda is not installed or not in PATH"
    echo "Please install conda (Miniconda or Anaconda) first"
    exit 1
fi

echo "Conda found: $(conda --version)"

# Check if environment already exists
if conda env list | grep -q "^${ENV_NAME} "; then
    echo ""
    echo "Environment '${ENV_NAME}' already exists."
    read -p "Do you want to remove and recreate it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Removing existing environment..."
        conda env remove -n "${ENV_NAME}" -y
    else
        echo "Using existing environment. Activate it with:"
        echo "  conda activate ${ENV_NAME}"
        exit 0
    fi
fi

# Create conda environment
echo ""
echo "Step 1: Creating conda environment '${ENV_NAME}' with Python ${PYTHON_VERSION}..."
conda create -n "${ENV_NAME}" python="${PYTHON_VERSION}" -y

# Activate environment and install dependencies
echo ""
echo "Step 2: Installing dependencies..."
eval "$(conda shell.bash hook)"
conda activate "${ENV_NAME}"

# Upgrade pip
python -m pip install --upgrade pip

# Install build dependencies
echo "Installing build dependencies (scikit-build-core, nanobind, numpy)..."
pip install scikit-build-core nanobind numpy

# Install SPZ Python bindings
echo ""
echo "Step 3: Installing SPZ Python bindings..."
cd "${SPZ_DIR}"

# Install in editable mode
pip install -e . --no-build-isolation

# Verify installation
echo ""
echo "Step 4: Verifying installation..."
python -c "import spz; print(f'✓ SPZ module imported successfully')" || {
    echo "✗ Failed to import SPZ module"
    exit 1
}

# Try to get version if available
python -c "import spz; print(f'SPZ version: {spz.__version__ if hasattr(spz, \"__version__\") else \"unknown\"}')" 2>/dev/null || echo "Version information not available"

echo ""
echo "=========================================="
echo "Setup completed successfully!"
echo "=========================================="
echo ""
echo "To activate the environment:"
echo "  conda activate ${ENV_NAME}"
echo ""
echo "To use SPZ in Python:"
echo "  import spz"
echo "  cloud = spz.load_spz('path/to/file.spz')"
echo ""
