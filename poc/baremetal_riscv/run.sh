#!/bin/bash
#
# SSCCS Bare-Metal RISC-V + SystemVerilog Validation Runner
#
# Two-layer verification pipeline:
#   1. RISC-V asm + Spike  (ISA-level)
#   2. SystemVerilog + Verilator (hardware-level)
#
# Usage:
#   ./run.sh                    # build and run all layers
#   ./run.sh --check            # build, run, check exit code
#   ./run.sh --verbose          # verbose output
#   ./run.sh --spike-only       # skip SystemVerilog
#   ./run.sh --sv-only          # skip Spike

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SIM_DIR="$SCRIPT_DIR/simulation"
SV_DIR="$SCRIPT_DIR/sv"

MODE="run"
SKIP_SPIKE=""
SKIP_SV=""

for arg in "$@"; do
    case "$arg" in
        --check)      MODE="check" ;;
        --verbose)    MODE="verbose" ;;
        --spike-only) SKIP_SV="1" ;;
        --sv-only)    SKIP_SPIKE="1" ;;
        *)            echo "Usage: $0 [--check|--verbose|--spike-only|--sv-only]"; exit 1 ;;
    esac
done

echo "============================================"
echo "  SSCCS Verification Pipeline"
echo "============================================"
echo ""

PASSED=0
FAILED=0
STATUS_SPIKE=0
STATUS_SV=0

# ═══════════════════════════════════════════════════════════════════════
# Layer 1: RISC-V asm + Spike
# ═══════════════════════════════════════════════════════════════════════
if [ -z "$SKIP_SPIKE" ] && [ -f "$SIM_DIR/run.sh" ]; then
    echo "── Layer 1: RISC-V asm + Spike ──"
    set +e
    "$SIM_DIR/run.sh" "$1"
    STATUS_SPIKE=$?
    set -e
    if [ $STATUS_SPIKE -eq 0 ]; then
        echo "  Spike: PASSED"
        PASSED=$((PASSED + 1))
    else
        echo "  Spike: FAILED (exit $STATUS_SPIKE)"
        FAILED=$((FAILED + 1))
    fi
    echo ""
else
    echo "── Layer 1: RISC-V asm + Spike — SKIPPED ──"
    echo ""
fi

# ═══════════════════════════════════════════════════════════════════════
# Layer 2: SystemVerilog + Verilator
# ═══════════════════════════════════════════════════════════════════════
if [ -z "$SKIP_SV" ] && [ -f "$SV_DIR/Makefile" ]; then
    echo "── Layer 2: SystemVerilog + Verilator ──"

    if command -v verilator &>/dev/null; then
        set +e
        make -C "$SV_DIR" check 2>&1 | tail -5
        STATUS_SV=$?
        set -e
        if [ $STATUS_SV -eq 0 ]; then
            echo "  SystemVerilog: PASSED"
            PASSED=$((PASSED + 1))
        else
            echo "  SystemVerilog: FAILED (exit $STATUS_SV)"
            FAILED=$((FAILED + 1))
        fi
    else
        echo "  Verilator not found — install with: brew install verilator"
        echo "  SystemVerilog: SKIPPED"
    fi
    echo ""
else
    echo "── Layer 2: SystemVerilog + Verilator — SKIPPED ──"
    echo ""
fi

# ═══════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════
echo "============================================"
echo "  Results: $PASSED passed, $FAILED failed"
echo "============================================"

if [ "$MODE" = "check" ]; then
    if [ $FAILED -gt 0 ]; then
        exit 1
    fi
fi
