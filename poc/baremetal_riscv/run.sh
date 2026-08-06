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
ASM_ONLY=""

for arg in "$@"; do
    case "$arg" in
        --check)      MODE="check" ;;
        --verbose)    MODE="verbose" ;;
        --spike-only) SKIP_SV="1" ;;
        --sv-only)    SKIP_SPIKE="1" ;;
        --asm-only)   ASM_ONLY="1" ;;
        *)            echo "Usage: $0 [--check|--verbose|--spike-only|--sv-only|--asm-only]"; exit 1 ;;
    esac
done

echo "============================================"
echo "  SSCCS Verification Pipeline"
echo "============================================"
echo ""

PASSED=0
FAILED=0
STATUS_ASM=0
STATUS_SPIKE=0
STATUS_SV=0

# ═══════════════════════════════════════════════════════════════════════
# Layer 0: Assembly syntax gate (all .S files)
# Every assembly module must assemble cleanly; Spike covers observe_full.S
# at runtime, the gate covers the remaining modules at build time.
# ═══════════════════════════════════════════════════════════════════════
echo "── Layer 0: Assembly syntax gate ──"

ASMDIR="$SCRIPT_DIR/asm"
if command -v riscv64-unknown-elf-as &>/dev/null; then
    for asm_file in "$ASMDIR"/*.S; do
        [ -e "$asm_file" ] || continue
        obj=$(mktemp)
        set +e
        riscv64-unknown-elf-as -o "$obj" "$asm_file" >/dev/null 2>&1
        status=$?
        set -e
        rm -f "$obj"
        if [ $status -eq 0 ]; then
            echo "  $(basename "$asm_file"): OK"
        else
            echo "  $(basename "$asm_file"): FAILED"
            STATUS_ASM=1
        fi
    done
    if [ $STATUS_ASM -eq 0 ]; then
        echo "  Assembly syntax: PASSED"
        PASSED=$((PASSED + 1))
    else
        echo "  Assembly syntax: FAILED"
        FAILED=$((FAILED + 1))
    fi
else
    # The gate is skipped, not failed, when the cross-toolchain is absent,
    # consistent with the SystemVerilog layer's Verilator handling. CI
    # environments with the RISC-V toolchain get the full gate.
    echo "  riscv64-unknown-elf-as not found — assembly gate SKIPPED"
fi
echo ""

# ── asm-only mode: exit after the syntax gate ──
if [ "$ASM_ONLY" = "1" ]; then
    if [ "$MODE" = "check" ] && [ $FAILED -gt 0 ]; then
        exit 1
    fi
    exit 0
fi

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
        SV_LOG=$(mktemp)
        make -C "$SV_DIR" check >"$SV_LOG" 2>&1
        STATUS_SV=$?
        if [ $STATUS_SV -eq 0 ]; then
            tail -20 "$SV_LOG"
            echo "  SystemVerilog: PASSED"
            PASSED=$((PASSED + 1))
        else
            cat "$SV_LOG"
            echo "  SystemVerilog: FAILED (exit $STATUS_SV)"
            FAILED=$((FAILED + 1))
        fi
        rm -f "$SV_LOG"
        set -e
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
