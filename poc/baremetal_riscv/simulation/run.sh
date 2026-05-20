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

# ── Check prerequisites ──────────────────────────────────────────────

HAVE_GCC=true
HAVE_SPIKE=true
PK=""

if ! command -v riscv64-unknown-elf-gcc &>/dev/null; then
    HAVE_GCC=false
fi

if ! command -v spike &>/dev/null; then
    HAVE_SPIKE=false
fi

# pk is a file that spike loads (not a command). Search known locations.
for candidate in \
    "/opt/homebrew/bin/pk" \
    "/opt/homebrew/Cellar/riscv-pk/main/riscv64-unknown-elf/bin/pk" \
    "/usr/local/bin/pk" \
    "/opt/riscv/bin/pk" \
    "/usr/local/riscv64-unknown-elf/bin/pk" \
    "/opt/riscv64-unknown-elf/bin/pk"; do
    if [ -f "$candidate" ]; then
        PK="$candidate"
        break
    fi
done

# If pk was not found at any known path, try bare "pk" as a fallback.
if [ -z "$PK" ]; then
    PK="pk"
fi

# ── Report missing tools ─────────────────────────────────────────────

NEED_INSTALL=false

if [ "$HAVE_GCC" = false ] || [ "$HAVE_SPIKE" = false ]; then
    NEED_INSTALL=true
    echo "============================================"
    echo "  Missing prerequisites:"
    echo ""
    [ "$HAVE_GCC" = false ]   && echo "  - riscv64-unknown-elf-gcc (cross-compiler)"
    [ "$HAVE_SPIKE" = false ] && echo "  - spike (RISC-V ISA simulator)"
    echo ""
    if [ "$OS" = "Darwin" ]; then
        echo "  Install on macOS (Homebrew):"
        echo "    brew tap riscv-software-src/riscv"
        echo "    brew install riscv-tools"
        echo ""
        echo "  This installs spike, riscv-pk, and the GNU toolchain together."
    else
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
    fi
    echo "============================================"
fi

# pk not found at any known path — warn but proceed (spike will report
# the error if it cannot open the file).
if [ ! -f "$PK" ] && [ "$PK" = "pk" ]; then
    echo "============================================"
    echo "  Note: riscv-pk (proxy kernel) not found at any known path."
    echo "  Will try: spike pk $TARGET"
    echo "  If this fails, install riscv-pk or set PK=/path/to/pk"
    echo "============================================"
fi

if [ "$NEED_INSTALL" = true ]; then
    exit 1
fi

SPIKE_VER="$(spike 2>&1 | head -1)"
echo "============================================"
echo "  SSCCS Spike Runtime Validation"
echo "============================================"
echo "  Compiler: $(riscv64-unknown-elf-gcc --version | head -1)"
echo "  Simulator: $SPIKE_VER"
echo "  PK: $PK"
echo "============================================"
echo ""

# ── Build ────────────────────────────────────────────────────────────

echo "Building..."
riscv64-unknown-elf-gcc -Wall -Wextra -O0 -g -o "$TARGET" "$TEST_C" "$STUBS_C" "$ASM_S"
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
