#!/usr/bin/env bash
#
# Build SSCCS documentation using the SDBS Docker image.
#
# Usage:
#   ./build.sh               # build all docs with website profile
#
# Prerequisites: Docker
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
IMAGE="ghcr.io/ssccsorg/sdbs:latest"

echo "Pulling SDBS Docker image..."
docker pull "$IMAGE"

exec docker run --rm \
  -v "$SCRIPT_DIR/..":/work \
  -w /work \
  -e QUARTO_PYTHON=python3 \
  "$IMAGE" \
  sdb build docs --website
