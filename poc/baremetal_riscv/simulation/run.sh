#!/bin/bash
#
# SSCCS Spike Runtime Validation — Local Runner
#
# Builds and runs the RISC-V assembly constraint primitives under
# Spike + pk simulation on your local machine.
#
# Prerequisites:
#   - riscv64-unknown-elf-gcc  (cross-compiler)
#   - spike                    (RISC-V ISA simulator)
#   - riscv-pk                  (proxy kernel)
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
ASMDIR="$SCRIPT_DIR/../../asm"
TEST_C="$SCRIPT_DIR/spike_test.c"
ASM_S="$ASMDIR/observe_full.S"
TARGET="$SCRIPT_DIR/spike_test"

# ── Check prerequisites ──────────────────────────────────────────────

MISSING=""

if ! command -v riscv64-unknown-elf-gcc &>/dev/null; then
    MISSING="$MISSING  - riscv64-unknown-elf-gcc (cross-compiler)\n"
fi

if ! command -v spike &>/dev/null; then
    MISSING="$MISSING  - spike (RISC-V ISA simulator)\n"
fi

# pk might not be in PATH (spike takes it as a file argument)
PK=""
if command -v pk &>/dev/null; then
    PK="pk"
elif [ -f /usr/local/riscv64-unknown-elf/bin/pk ]; then
    PK="/usr/local/riscv64-unknown-elf/bin/pk"
elif [ -f /usr/riscv64-unknown-elf/bin/pk ]; then
    PK="/usr/riscv64-unknown-elf/bin/pk"
elif [ -f /opt/riscv/bin/pk ]; then
    PK="/opt/riscv/bin/pk"
elif [ -f ./pk ]; then
    PK="./pk"
else
    MISSING="$MISSING  - riscv-pk (proxy kernel)\n"
fi

if [ -n "$MISSING" ]; then
    echo "============================================"
    echo "  Missing prerequisites:"
    echo -e "$MISSING"
    echo ""
    echo "  Install on Ubuntu/Debian:"
    echo "    sudo apt-get install gcc-riscv64-unknown-elf binutils-riscv64-unknown-elf"
    echo ""
    echo "  Build spike from source:"
    echo "    git clone https://github.com/riscv-software-src/riscv-isa-sim.git"
    echo "    cd riscv-isa-sim && mkdir build && cd build"
    echo "    ../configure --prefix=/usr/local && make -j\$(nproc) && sudo make install"
    echo ""
    echo "  Build riscv-pk from source:"
    echo "    git clone https://github.com/riscv-software-src/riscv-pk.git"
    echo "    cd riscv-pk && mkdir build && cd build"
    echo "    ../configure --prefix=/usr/local --host=riscv64-unknown-elf"
    echo "    make -j\$(nproc) && sudo make install"
    echo "============================================"
    exit 1
fi

echo "============================================"
echo "  SSCCS Spike Runtime Validation"
echo "============================================"
echo "  Compiler: $(riscv64-unknown-elf-gcc --version | head -1)"
echo "  Simulator: $(spike --version 2>&1 | head -1)"
echo "  PK: $PK"
echo "============================================"
echo ""

# ── Build ────────────────────────────────────────────────────────────

echo "Building..."
riscv64-unknown-elf-gcc -Wall -Wextra -O0 -g -o "$TARGET" "$TEST_C" "$ASM_S"
echo "  -> $TARGET"
echo ""

# ── Run ──────────────────────────────────────────────────────────────

case "$MODE" in
    run)
        echo "Running under Spike..."
        echo ""
        spike "$PK" "$TARGET"
        echo ""
        echo "Done (exit code: $?)."
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
