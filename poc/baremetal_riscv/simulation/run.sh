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

set -e

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

# Detect OS
OS="$(uname -s)"

# ── Find cross-compiler  ──────────────────────────────────────────────

CC=""
for candidate in riscv64-unknown-elf-gcc riscv64-linux-gnu-gcc; do
    if command -v "$candidate" &>/dev/null; then
        CC="$candidate"
        break
    fi
done

# ── Check prerequisites ──────────────────────────────────────────────

HAVE_SPIKE=true
PK=""

if [ -z "$CC" ]; then
    echo "============================================"
    echo "  Missing: RISC-V cross-compiler"
    echo ""
    echo "  Install on macOS (Homebrew):"
    echo "    brew tap riscv-software-src/riscv"
    echo "    brew install riscv-tools"
    echo ""
    echo "  Install on Ubuntu/Debian:"
    echo "    sudo apt-get install gcc-riscv64-linux-gnu binutils-riscv64-linux-gnu"
    echo "============================================"
    exit 1
fi

if ! command -v spike &>/dev/null; then
    echo "============================================"
    echo "  Missing: spike (RISC-V ISA simulator)"
    echo ""
    echo "  Install on macOS (Homebrew):"
    echo "    brew tap riscv-software-src/riscv"
    echo "    brew install riscv-tools"
    echo ""
    echo "  Build from source:"
    echo "    git clone https://github.com/riscv-software-src/riscv-isa-sim.git"
    echo "    cd riscv-isa-sim && mkdir build && cd build"
    echo "    ../configure --prefix=/usr/local && make -j\$(nproc) && sudo make install"
    echo "============================================"
    exit 1
fi

# pk is a file that spike loads (not a command). Search known locations.
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

# Fallback: try bare "pk" if not found at known paths
if [ -z "$PK" ]; then
    PK="pk"
fi

if [ ! -f "$PK" ] && [ "$PK" = "pk" ]; then
    echo "============================================"
    echo "  Note: riscv-pk (proxy kernel) not found at any known path."
    echo "  Will try: spike pk $TARGET"
    echo "  If this fails:"
    echo "    macOS: brew install riscv-tools (includes pk)"
    echo "    Linux: build from https://github.com/riscv-software-src/riscv-pk"
    echo "============================================"
fi

SPIKE_VER="$(spike 2>&1 | head -1)"
echo "============================================"
echo "  SSCCS Spike Runtime Validation"
echo "============================================"
echo "  Compiler: $CC ($($CC --version | head -1))"
echo "  Simulator: $SPIKE_VER"
echo "  PK: $PK"
echo "============================================"
echo ""

# ── Build (statically linked for pk compatibility) ────────────────────

echo "Building..."
$CC -static -Wall -Wextra -O0 -g -o "$TARGET" "$TEST_C" "$STUBS_C" "$ASM_S"
echo "  -> $TARGET"
echo ""

# ── Run ──────────────────────────────────────────────────────────────

case "$MODE" in
    run)
        echo "Running under Spike..."
        echo ""
        spike "$PK" "$TARGET"
        STATUS=$?
        echo ""
        if [ $STATUS -eq 0 ]; then
            echo "Done."
        else
            echo "Done (exit code: $STATUS)."
        fi
        ;;
    check)
        echo "Running under Spike (check mode)..."
        echo ""
        spike "$PK" "$TARGET"
        STATUS=$?
        echo ""
        if [ $STATUS -eq 0 ]; then
            echo "All tests passed."
        else
            echo "Some tests failed (exit code: $STATUS)."
        fi
        exit $STATUS
        ;;
    verbose)
        echo "Running under Spike (verbose)..."
        echo ""
        spike -l "$PK" "$TARGET"
        echo ""
        echo "Done (exit code: $?)."
        ;;
esac
