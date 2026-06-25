#!/bin/bash
#
# SSCCS Spike Runtime Validation -- Local Runner
#
# Builds and runs the RISC-V assembly constraint primitives under
# Spike + pk simulation on your local machine.
#
# Prerequisites:
#   - riscv64-unknown-elf-gcc or riscv64-linux-gnu-gcc  (cross-compiler)
#   - spike                    (RISC-V ISA simulator)
#   - riscv-pk                  (proxy kernel "pk" passed as file to spike)
#
# Usage:
#   ./run.sh                    # build and run
#   ./run.sh --check            # build, run, check exit code
#   ./run.sh --verbose          # build and run with verbose output
#

MODE="run"
if [ "$1" = "--check" ]; then
    MODE="check"
elif [ "$1" = "--verbose" ]; then
    MODE="verbose"
elif [ -n "$1" ]; then
    echo "Usage: $0 [--check|--verbose]"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ASMDIR="$SCRIPT_DIR/../asm"
TEST_C="$SCRIPT_DIR/spike_test.c"
STUBS_C="$SCRIPT_DIR/stubs.c"
ASM_S="$ASMDIR/observe_full.S"
TARGET="$SCRIPT_DIR/spike_test"
OS="$(uname -s)"

# ── Find cross-compiler ──────────────────────────────────────────
CC=""
for candidate in riscv64-unknown-elf-gcc riscv64-linux-gnu-gcc; do
    if command -v "$candidate" &>/dev/null; then
        CC="$candidate"
        break
    fi
done

if [ -z "$CC" ]; then
    echo "============================================"
    echo "  Missing: RISC-V cross-compiler"
    if [ "$OS" = "Darwin" ]; then
        echo "    brew tap riscv-software-src/riscv"
        echo "    brew install riscv-tools"
    else
        echo "    sudo apt-get install gcc-riscv64-linux-gnu binutils-riscv64-linux-gnu"
    fi
    echo "============================================"
    exit 1
fi

if ! command -v spike &>/dev/null; then
    echo "============================================"
    echo "  Missing: spike (RISC-V ISA simulator)"
    echo "  macOS: brew install riscv-tools"
    echo "  Linux: build from https://github.com/riscv-software-src/riscv-isa-sim"
    echo "============================================"
    exit 1
fi

# pk is a file that spike loads (not a command). Search known locations.
PK=""
for candidate in \
    "/opt/homebrew/bin/pk" \
    "/opt/homebrew/Cellar/riscv-pk/main/riscv64-unknown-elf/bin/pk" \
    "/usr/local/bin/pk" \
    "/usr/local/riscv64-unknown-elf/bin/pk" \
    "/opt/riscv/bin/pk" \
    "/opt/riscv64-unknown-elf/bin/pk"; do
    if [ -f "$candidate" ]; then
        PK="$candidate"
        break
    fi
done
[ -z "$PK" ] && PK="pk"

if [ ! -f "$PK" ] && [ "$PK" = "pk" ]; then
    echo "============================================"
    echo "  Note: riscv-pk not found. Trying: spike pk $TARGET"
    echo "  macOS: brew install riscv-tools"
    echo "  Linux: build from https://github.com/riscv-software-src/riscv-pk"
    echo "============================================"
fi

echo "============================================"
echo "  SSCCS Spike Runtime Validation"
echo "============================================"
echo "  Compiler: $(basename $CC)"
echo "  Simulator: $(spike 2>&1 | head -1)"
echo "  PK: $PK"
echo "============================================"
echo ""

# ── SSCCS experiment C harnesses ─────────────────────────────
EXP_DIR="$SCRIPT_DIR"
EXP_TARGETS=""
for exp_c in "$EXP_DIR"/exp*.c; do
    [ -f "$exp_c" ] || continue
    exp_name=$(basename "$exp_c" .c)
    exp_bin="$EXP_DIR/$exp_name"
    echo "Building experiment: $exp_name"
    $CC -static -Wall -Wextra -O0 -g -o "$exp_bin" "$exp_c"
    EXP_TARGETS="$EXP_TARGETS $exp_bin"
done

# ── Build legacy spike_test (static link for pk compatibility) ──
echo "Building legacy test..."
$CC -static -Wall -Wextra -O0 -g -o "$TARGET" "$TEST_C" "$STUBS_C" "$ASM_S"
echo "  -> $TARGET"
echo ""

# ── Run all binaries under Spike ─────────────────────────────
run_all() {
    local mode_label="$1"
    shift
    local all_status=0
    for bin in "$@"; do
        [ ! -f "$bin" ] && continue
        local bin_name=$(basename "$bin")
        echo "[$mode_label] Running: $bin_name"
        set +e
        spike "$PK" "$bin"
        local ec=$?
        set -e
        echo "[$mode_label] $bin_name exit code: $ec"
        echo ""
        [ $ec -ne 0 ] && all_status=$ec
    done
    return $all_status
}

TARGETS="$EXP_TARGETS $TARGET"
case "$MODE" in
    run)
        echo "Running under Spike..."
        run_all "run" $TARGETS
        STATUS=$?
        [ $STATUS -eq 0 ] && echo "All done." || echo "Done (exit code: $STATUS)."
        ;;
    check)
        echo "Running under Spike (check mode)..."
        run_all "check" $TARGETS
        STATUS=$?
        [ $STATUS -eq 0 ] && echo "All tests passed." || echo "Some tests failed (exit code: $STATUS)."
        exit $STATUS
        ;;
    verbose)
        echo "Running under Spike (verbose)..."
        spike -l "$PK" "$TARGET"
        ;;
esac
