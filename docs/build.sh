#!/usr/bin/env bash
#
# Build SSCCS documentation using the SDBS Docker image.
#
# Usage:
#   ./build.sh               # build all docs with website profile
#   ./build.sh --no-cache    # force rebuild (ignore Docker cache)
#
# Prerequisites: Docker
#

set -euo pipefail

cd "$(dirname "$0")"

IMAGE="ghcr.io/ssccsorg/sdbs:latest"
DOCKER_FLAGS=

# Parse flags
for arg in "$@"; do
  case "$arg" in
    --no-cache)
      DOCKER_FLAGS="--no-cache"
      ;;
    *)
      echo "Unknown option: $arg"
      echo "Usage: $0 [--no-cache]"
      exit 1
      ;;
  esac
done

# Pull or build the image
if docker pull "$IMAGE" 2>/dev/null; then
  echo "Image pulled successfully."
else
  echo "Image not found locally or in registry. Building from ../tools/docs-orchestrator/Dockerfile..."
  # shellcheck disable=SC2086
  docker build $DOCKER_FLAGS \
    -t "$IMAGE" \
    -f ../tools/docs-orchestrator/Dockerfile \
    ..
fi

# Run the build (mirrors .github/workflows/deploy-docs-ghpage.yml)
exec docker run --rm \
  -v "$(pwd)/..":/work \
  -w /work \
  -e QUARTO_PYTHON=python3 \
  "$IMAGE" \
  sdb build docs --website
