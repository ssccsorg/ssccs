#!/bin/bash
#
# SSCCS POC Full Validation Script (Standard Cargo Only)
# Automatically discovers and runs all binary crates in the workspace
#

set -e  # Stop immediately when an error occurs

echo "SSCCS POC - Full Validation"

# Go to script location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 1. Build (entire workspace)
echo "--- Step 1: Building workspace ---"
cargo build --workspace --release

# 2. Run standard tests (use default cargo test instead of nexttest)
echo "--- Step 2: Running all tests (Standard Cargo Test) ---"
# --workspace: Test entire crate
# --all-targets: Includes unit, integration, and doc tests
cargo test --workspace --all-targets --release

# 3. Automatic discovery and sequential execution of binaries
echo "--- Step 3: Discovering and running all binary crates ---"

# Extract all binary crate names using cargo metadata
BIN_CRATES=$(cargo metadata --format-version=1 --no-deps | \
    jq -r '.packages[] | select(.targets[] | .kind[] | contains("bin")) | .name' | \
    sort)

if [ -z "$BIN_CRATES" ]; then
    echo "No binary crates found in workspace!"
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
    echo "─────────────────────────────────────────────────────────────"
    echo " Running: $crate"
    echo "─────────────────────────────────────────────────────────────"
    
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

# Summary of results
echo ""
echo "  Build: SUCCESS"
echo "  Tests: SUCCESS"
echo "  Binary crates: $PASSED/$TOTAL passed"
echo ""

if [ ${#FAILED[@]} -eq 0 ]; then
    echo "  ALL VALIDATIONS PASSED"
    echo ""
    exit 0
else
    echo "  SOME VALIDATIONS FAILED"
    echo ""
    echo "  Failed crates:"
    for failed in "${FAILED[@]}"; do
        echo "    - $failed"
    done
    echo ""
    exit 1
fi