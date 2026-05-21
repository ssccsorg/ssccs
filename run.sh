#!/bin/bash
#
# SSCCS Repository Root Runner
#
# Lightweight router that delegates to module-level run.sh scripts.
# Currently routes to poc/run.sh for all PoC validation tasks.
#
# Usage:
#   ./run.sh [--validation|--run]     # delegate to poc/run.sh
#   ./run.sh --docker                  # build and run poc Docker image
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$1" = "--docker" ]; then
    shift
    echo "Building poc Docker image..."
    docker build -t ssccs-poc -f "$SCRIPT_DIR/poc/Dockerfile" "$SCRIPT_DIR"
    echo ""
    echo "Running Spike validation in container..."
    docker run --rm -v "$SCRIPT_DIR:/workspace" ssccs-poc \
        bash -c "cd /workspace/poc/baremetal_riscv/simulation && bash run.sh --check"
    exit $?
fi

# Default: delegate to poc/run.sh
if [ -f "$SCRIPT_DIR/poc/run.sh" ]; then
    exec "$SCRIPT_DIR/poc/run.sh" "$@"
else
    echo "Error: poc/run.sh not found."
    exit 1
fi
