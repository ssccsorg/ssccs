#!/usr/bin/env bash
#
# Build SSCCS documentation using SDBS.
#
# Usage:
#   ./build.sh               # build all docs with website profile
#
# SDBS is installed automatically via one of:
#   uv tool install git+https://github.com/ssccsorg/sdbs.git
#   pip install git+https://github.com/ssccsorg/sdbs.git
#
# Falls back to Docker if neither uv, pip, nor sdb are available.
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
IMAGE="ghcr.io/ssccsorg/sdbs:latest"
SDBS_REPO="git+https://github.com/ssccsorg/sdbs.git"

# ---- 1. Install SDBS if not already available ----
if ! command -v sdb &>/dev/null; then
  if command -v uv &>/dev/null; then
    echo "Installing SDBS via uv..."
    uv tool install "$SDBS_REPO"
  elif command -v pip &>/dev/null; then
    echo "Installing SDBS via pip..."
    pip install "$SDBS_REPO"
  else
    echo "Neither uv nor pip found. Falling back to Docker."
    echo "Pulling SDBS Docker image..."
    docker pull "$IMAGE"
    exec docker run --rm \
      -v "$SCRIPT_DIR/..":/work \
      -w /work \
      -e QUARTO_PYTHON=python3 \
      "$IMAGE" \
      sdb build docs --website
  fi
fi

# ---- 2. Check Quarto ----
if ! command -v quarto &>/dev/null; then
  echo "Quarto not found on PATH. Falling back to Docker."
  echo "Pulling SDBS Docker image..."
  docker pull "$IMAGE"
  exec docker run --rm \
    -v "$SCRIPT_DIR/..":/work \
    -w /work \
    -e QUARTO_PYTHON=python3 \
    "$IMAGE" \
    sdb build docs --website
fi

# ---- 3. Run directly ----
echo "Running: sdb build docs --website"
exec sdb build docs --website
