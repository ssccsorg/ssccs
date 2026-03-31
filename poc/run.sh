#!/bin/bash
#
# SSCCS POC Full Validation Script
#

set -e 

MODE="run"

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --validation) MODE="validation" ;;
        --run) MODE="run" ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

echo "─────────────────────────────────────────────────────────────"
echo "SSCCS POC - Mode: $(echo $MODE | tr '[:lower:]' '[:upper:]')"
echo "─────────────────────────────────────────────────────────────"
# ===========================================================================
# Step 1: Code Formatting (Mode-dependent)
# ===========================================================================

if [ "$MODE" = "run" ]; then
    echo "Applying formatting (cargo fmt --all)..."
    cargo fmt --all
    echo " Code formatted"
fi

echo "Step 1: Checking formatting (cargo fmt --check)..."
cargo fmt --check
echo " Formatting check passed"

# ===========================================================================
# Step 2: Linting (Clippy)
# ===========================================================================
echo "─────────────────────────────────────────────────────────────"
echo "Step 2: Running clippy (cargo clippy --workspace)..."
cargo clippy --workspace -- -D warnings
echo " Clippy passed (no warnings)"

# ===========================================================================
# Step 3: Build workspace
# ===========================================================================
echo "─────────────────────────────────────────────────────────────"
echo "Step 3: Building workspace (release mode)..."
cargo build --workspace --release
echo " Build successful"

# ===========================================================================
# Step 4: Run all tests
# ===========================================================================
echo "─────────────────────────────────────────────────────────────"
echo "Step 4: Running all tests (cargo test --workspace)..."
cargo test --workspace --all-targets --release
echo " All tests passed"

# ===========================================================================
# Step 5: Discover and run all binary crates
# ===========================================================================
echo "─────────────────────────────────────────────────────────────"
echo "Step 5: Discovering and running all binary crates..."

# Install jq if not available (for GitHub Actions environment)
if ! command -v jq &> /dev/null; then
    echo "jq not found, attempting to install..."
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo apt-get update && sudo apt-get install -y jq
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        brew install jq
    else
        echo "ERROR: jq is required but cannot be automatically installed on this OS."
        exit 1
    fi
fi

# Extract all binary crate names using cargo metadata
BIN_CRATES=$(cargo metadata --format-version=1 --no-deps | \
    jq -r '.packages[] | select(.targets[] | .kind[] | contains("bin")) | .name' | \
    sort)

if [ -z "$BIN_CRATES" ]; then
    echo "ERROR: No binary crates found in workspace!"
    exit 1
fi

echo "Discovered binary crates:"
echo "$BIN_CRATES" | while read crate; do
    echo "  - $crate"
done
echo ""

FAILED=()
TOTAL=0
PASSED=0

for crate in $BIN_CRATES; do
    TOTAL=$((TOTAL + 1))
    # --quiet: Reduce cargo's own logs and focus on binary output
    if cargo run --release --bin "$crate" --quiet; then
        echo " $crate: SUCCESS"
        PASSED=$((PASSED + 1))
    else
        echo " $crate: FAILED"
        FAILED+=("$crate")
    fi
    echo ""
done

# ===========================================================================
# Final Summary
# ===========================================================================
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  Validation Summary                                        ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "  Formatting:    PASSED"
echo "  Clippy:        PASSED"
echo "  Build:         PASSED"
echo "  Tests:         PASSED"
echo "  Binary crates: $PASSED/$TOTAL passed"
echo ""

if [ ${#FAILED[@]} -eq 0 ]; then
    echo "  ALL VALIDATIONS PASSED!"
    echo ""
    exit 0
else
    echo "  SOME VALIDATIONS FAILED!"
    echo ""
    echo "  Failed crates:"
    for failed in "${FAILED[@]}"; do
        echo "    - $failed"
    done
    echo ""
    exit 1
fi