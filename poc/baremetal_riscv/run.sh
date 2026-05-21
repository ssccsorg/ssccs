#!/bin/bash
#
# SSCCS Bare-Metal RISC-V Validation Runner
#
# Convenience wrapper that delegates to the Spike simulation runner.
# All arguments are forwarded to simulation/run.sh.
#
# Usage:
#   ./run.sh                    # build and run spike tests
#   ./run.sh --check            # build, run, check exit code
#   ./run.sh --verbose          # verbose spike output
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SIM_RUN="$SCRIPT_DIR/simulation/run.sh"

if [ ! -f "$SIM_RUN" ]; then
    echo "Error: $SIM_RUN not found."
    echo "Are you in the poc/baremetal_riscv directory?"
    exit 1
fi

exec "$SIM_RUN" "$@"
