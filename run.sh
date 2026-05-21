#!/bin/bash
#
# SSCCS Repository Root Runner
#
# Lightweight router that delegates to module-level run.sh scripts.
# Currently routes to poc/run.sh for all PoC validation tasks.
#
# Usage:
#   ./run.sh [--validation|--run]     # delegate to poc/run.sh
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "$SCRIPT_DIR/poc/run.sh" ]; then
    exec "$SCRIPT_DIR/poc/run.sh" "$@"
else
    echo "Error: poc/run.sh not found."
    exit 1
fi
