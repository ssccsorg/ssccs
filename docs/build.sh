#!/usr/bin/env bash
#
# Build SSCCS documentation using the SDBS Docker image.
#
# Usage:
#   ./build.sh               # build all docs with website profile
#
# Prerequisites: Docker
#
# The SDBS image is published at ghcr.io/ssccsorg/sdbs:latest
# from the https://github.com/ssccsorg/sdbs repository.
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
IMAGE="ghcr.io/ssccsorg/sdbs:latest"

echo "Pulling SDBS Docker image..."
docker pull "$IMAGE"

# Run the build (mirrors .github/workflows/deploy-docs-ghpage.yml)
exec docker run --rm \
  -v "$SCRIPT_DIR/..":/work \
  -w /work \
  -e QUARTO_PYTHON=python3 \
  "$IMAGE" \
  sdb build docs --website
