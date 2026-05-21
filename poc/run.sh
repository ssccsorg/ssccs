#!/bin/bash
#
# SSCCS POC Full Validation Script
# Automatically discovers all Rust workspaces (Cargo.toml with [workspace])
# and standalone crates (Cargo.toml with [package] but not part of a workspace),
# then runs all local module-level run.sh scripts (Spike tests, etc.).
#
# For bare-metal workspaces/crates (those with [package.metadata.rust-analyzer.rustc.target]),
# this script skips clippy and build steps (as they require cross-compilation),
# but still runs tests on the host target.
#
# Usage:
#   ./run.sh [--validation|--run] [--workspace <path>]...
#
# Options:
#   --validation  Run in validation mode (skip auto-formatting)
#   --run         Run in development mode (apply formatting first)
#   --workspace   Specify a workspace path (can be used multiple times)
#                 If not specified, all workspaces/crates are auto-discovered
#

set -e 

MODE="run"
WORKSPACES=()

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --validation) MODE="validation" ;;
        --run) MODE="run" ;;
        --workspace) 
            shift
            WORKSPACES+=("$1")
            ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

# Auto-discover workspaces and standalone crates if not specified
if [ ${#WORKSPACES[@]} -eq 0 ]; then
    echo "Auto-discovering Rust workspaces and crates..."
    
    # First pass: find all workspace roots and collect their members
    WORKSPACE_ROOTS=""
    WORKSPACE_MEMBERS=""
    
    while IFS= read -r -d '' cargo_toml; do
        if grep -q '^\[workspace\]' "$cargo_toml" 2>/dev/null; then
            ws_dir=$(dirname "$cargo_toml")
            WORKSPACE_ROOTS="$WORKSPACE_ROOTS|$ws_dir|"
            
            # Collect members from this workspace
            # Read lines between [workspace] and next section
            in_workspace=false
            while IFS= read -r line; do
                if [[ "$line" =~ ^\[workspace\] ]]; then
                    in_workspace=true
                    continue
                fi
                if [[ "$line" =~ ^\[ ]] && [ "$in_workspace" = true ]; then
                    break
                fi
                if [ "$in_workspace" = true ]; then
                    # Extract member path (remove quotes and whitespace)
                    member=$(echo "$line" | sed 's/.*"\([^"]*\)".*/\1/' | tr -d ' ,')
                    if [[ "$member" =~ ^crates/ ]] || [[ "$member" =~ ^[a-zA-Z] ]]; then
                        # Resolve relative path
                        full_path="$ws_dir/$member"
                        # Normalize path (remove ./ and resolve ..)
                        full_path=$(cd "$full_path" 2>/dev/null && pwd || echo "$full_path")
                        WORKSPACE_MEMBERS="$WORKSPACE_MEMBERS|$full_path|"
                    fi
                fi
            done < "$cargo_toml"
        fi
    done < <(find . -name "Cargo.toml" -not -path "*/target/*" -print0 2>/dev/null)
    
    # Second pass: find all packages and workspaces
    while IFS= read -r -d '' cargo_toml; do
        ws_dir=$(dirname "$cargo_toml")
        # Get absolute path
        abs_ws_dir=$(cd "$ws_dir" 2>/dev/null && pwd || echo "$ws_dir")
        
        # Check if this Cargo.toml defines a workspace
        if grep -q '^\[workspace\]' "$cargo_toml" 2>/dev/null; then
            WORKSPACES+=("$ws_dir")
            echo "  Found workspace: $ws_dir"
        # Check if it's a standalone package (has [package] but no [workspace])
        elif grep -q '^\[package\]' "$cargo_toml" 2>/dev/null; then
            # Skip if this is a member of any workspace
            is_member=false
            
            # Check if path is in WORKSPACE_MEMBERS
            if [[ "$WORKSPACE_MEMBERS" == *"|$abs_ws_dir|"* ]]; then
                is_member=true
            fi
            
            # Also check if path is under any workspace root
            if [[ "$WORKSPACE_ROOTS" == *"|"* ]]; then
                for ws_root in $(echo "$WORKSPACE_ROOTS" | tr '|' '\n' | grep -v '^$'); do
                    if [[ "$abs_ws_dir" == "$ws_root"/* ]]; then
                        is_member=true
                        break
                    fi
                done
            fi
            
            if [ "$is_member" = false ]; then
                WORKSPACES+=("$ws_dir")
                echo "  Found standalone crate: $ws_dir"
            fi
        fi
    done < <(find . -name "Cargo.toml" -not -path "*/target/*" -print0 2>/dev/null)
    
    # If still nothing found, exit with error
    if [ ${#WORKSPACES[@]} -eq 0 ]; then
        echo "ERROR: No Rust workspaces or crates found!"
        exit 1
    fi
fi

echo ""
echo "─────────────────────────────────────────────────────────────"
echo "SSCCS POC - Mode: $(echo $MODE | tr '[:lower:]' '[:upper:]')"
echo "─────────────────────────────────────────────────────────────"
echo "Workspaces to validate: ${WORKSPACES[@]}"
echo "Total workspaces: ${#WORKSPACES[@]}"
echo "─────────────────────────────────────────────────────────────"
echo ""

# Function to check if a workspace/crate is a bare-metal target
is_baremetal_workspace() {
    local ws="$1"
    grep -q '^\[package\.metadata\.rust-analyzer\]' "$ws/Cargo.toml" 2>/dev/null || \
    grep -q '^\[workspace\.metadata\.rust-analyzer\]' "$ws/Cargo.toml" 2>/dev/null || \
    grep -q '^\[package\.metadata\.rustc\]' "$ws/Cargo.toml" 2>/dev/null || \
    grep -q '^\[workspace\.metadata\.rustc\]' "$ws/Cargo.toml" 2>/dev/null || \
    grep -q 'target.*=.*"riscv' "$ws/Cargo.toml" 2>/dev/null
}

# Function to get the target from a bare-metal workspace
get_baremetal_target() {
    local ws="$1"
    grep -oP 'target\s*=\s*"\K[^"]+' "$ws/Cargo.toml" 2>/dev/null | head -1
}

# ===========================================================================
# Step 1: Code Formatting (Mode-dependent) - per workspace
# ===========================================================================

if [ "$MODE" = "run" ]; then
    echo "Step 1: Applying formatting (cargo fmt --all)..."
    for ws in "${WORKSPACES[@]}"; do
        echo "  Formatting: $ws"
        (cd "$ws" && cargo fmt --all)
    done
    echo "Code formatted"
    echo ""
fi

echo "Step 1: Checking formatting (cargo fmt --check)..."
FMT_FAILED=0
for ws in "${WORKSPACES[@]}"; do
    echo "  Checking: $ws"
    if (cd "$ws" && cargo fmt --check 2>&1); then
        echo "    ✓ Passed"
    else
        echo "    ✗ Failed"
        FMT_FAILED=1
    fi
done

if [ $FMT_FAILED -eq 1 ]; then
    echo "Formatting check failed in one or more workspaces"
    exit 1
fi
echo "Formatting check passed"
echo ""

# ===========================================================================
# Step 2: Linting (Clippy) - per workspace (skip bare-metal)
# ===========================================================================
echo "─────────────────────────────────────────────────────────────"
echo "Step 2: Running clippy for each workspace..."
echo ""

CLIPPY_FAILED=0
for ws in "${WORKSPACES[@]}"; do
    echo "  Clippy: $ws"
    if is_baremetal_workspace "$ws"; then
        echo "    ⊘ Skipped (bare-metal workspace - requires cross-compilation)"
    else
        if (cd "$ws" && cargo clippy --workspace -- -D warnings 2>&1); then
            echo "    ✓ Passed"
        else
            echo "    ✗ Failed"
            CLIPPY_FAILED=1
        fi
    fi
    echo ""
done

if [ $CLIPPY_FAILED -eq 1 ]; then
    echo "Clippy failed in one or more workspaces"
    exit 1
fi
echo "Clippy passed (no warnings)"
echo ""

# ===========================================================================
# Step 3: Build all workspaces (skip bare-metal)
# ===========================================================================
echo "─────────────────────────────────────────────────────────────"
echo "Step 3: Building all workspaces (release mode)..."
echo ""

BUILD_FAILED=0
for ws in "${WORKSPACES[@]}"; do
    echo "  Building: $ws"
    if is_baremetal_workspace "$ws"; then
        TARGET=$(get_baremetal_target "$ws")
        if [ -n "$TARGET" ]; then
            echo "    ⊘ Skipped (bare-metal workspace - requires target: $TARGET)"
        else
            echo "    ⊘ Skipped (bare-metal workspace)"
        fi
    else
        if (cd "$ws" && cargo build --workspace --release 2>&1); then
            echo "    ✓ Built successfully"
        else
            echo "    ✗ Build failed"
            BUILD_FAILED=1
        fi
    fi
    echo ""
done

if [ $BUILD_FAILED -eq 1 ]; then
    echo "Build failed in one or more workspaces"
    exit 1
fi
echo "Build successful"
echo ""

# ===========================================================================
# Step 4: Run all tests (host target only)
# ===========================================================================
echo "─────────────────────────────────────────────────────────────"
echo "Step 4: Running all tests (host target)..."
echo ""

TEST_FAILED=0
for ws in "${WORKSPACES[@]}"; do
    echo "  Testing: $ws"
    if (cd "$ws" && cargo test --workspace --all-targets --release 2>&1); then
        echo "    ✓ Tests passed"
    else
        echo "    ✗ Tests failed"
        TEST_FAILED=1
    fi
    echo ""
done

if [ $TEST_FAILED -eq 1 ]; then
    echo "Tests failed in one or more workspaces"
    exit 1
fi
echo "All tests passed"
echo ""

# ===========================================================================
# Step 5: Discover and run all binary crates (per workspace)
# ===========================================================================
echo "─────────────────────────────────────────────────────────────"
echo "Step 5: Discovering and running all binary crates..."
echo ""

# Install jq if not available
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

OVERALL_FAILED=()
OVERALL_PASSED=0
OVERALL_TOTAL=0

for ws in "${WORKSPACES[@]}"; do
    echo "  Workspace: $ws"
    
    # Extract all binary crate names using cargo metadata
    BIN_CRATES=$(cd "$ws" && cargo metadata --format-version=1 --no-deps 2>/dev/null | \
        jq -r '.packages[] | select(.targets[] | .kind[] | contains("bin")) | .name' 2>/dev/null | \
        sort)
    
    if [ -z "$BIN_CRATES" ]; then
        echo "    No binary crates found"
        echo ""
        continue
    fi
    
    echo "    Binary crates:"
    echo "$BIN_CRATES" | while read crate; do
        echo "      - $crate"
    done
    echo ""
    
    WS_FAILED=()
    WS_PASSED=0
    WS_TOTAL=0
    
    for crate in $BIN_CRATES; do
        WS_TOTAL=$((WS_TOTAL + 1))
        OVERALL_TOTAL=$((OVERALL_TOTAL + 1))
        
        echo -n "    Running $crate... "
        if (cd "$ws" && cargo run --release --bin "$crate" --quiet 2>&1); then
            echo "SUCCESS"
            WS_PASSED=$((WS_PASSED + 1))
            OVERALL_PASSED=$((OVERALL_PASSED + 1))
        else
            echo "FAILED"
            WS_FAILED+=("$ws/$crate")
            OVERALL_FAILED+=("$ws/$crate")
        fi
    done
    
    echo "    Workspace result: $WS_PASSED/$WS_TOTAL passed"
    echo ""
done

# ===========================================================================
# Step 6: Run all local module-level run.sh scripts
# ===========================================================================
echo "─────────────────────────────────────────────────────────────"
echo "Step 6: Running local module-level run.sh scripts..."
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_RUN_FAILED=0

while IFS= read -r -d '' local_run; do
    # Skip this script itself
    [ "$local_run" = "$SCRIPT_DIR/run.sh" ] && continue
    # Skip anything inside target/ or .git/
    [[ "$local_run" == */target/* || "$local_run" == */.git/* ]] && continue

    local_dir="$(dirname "$local_run")"

    # Compute relative path from SCRIPT_DIR
    rel="${local_dir#$SCRIPT_DIR/}"
    # If prefix did not start with SCRIPT_DIR, show absolute path
    if [ "$rel" = "$local_dir" ]; then
        rel="$local_dir"
    fi
    echo "  Found: $rel/run.sh"

    if [ ! -x "$local_run" ] && ! head -1 "$local_run" 2>/dev/null | grep -q '^#!/'; then
        echo "    ⊘ Skipped (not executable, no shebang)"
        continue
    fi

    echo ""
    if (cd "$local_dir" && bash "$local_run" --check 2>&1); then
        echo "    ✓ $rel/run.sh passed"
    else
        echo "    ✗ $rel/run.sh failed"
        LOCAL_RUN_FAILED=1
    fi
    echo ""
done < <(find "$SCRIPT_DIR" -name "run.sh" -type f -print0 2>/dev/null)

if [ $LOCAL_RUN_FAILED -eq 1 ]; then
    OVERALL_FAILED+=("local run.sh scripts")
fi

# ===========================================================================
# Final Summary
# ===========================================================================
echo "═════════════════════════════════════════════════════════════"
echo "  Validation Summary"
echo "═════════════════════════════════════════════════════════════"
echo ""
echo "Formatting:    PASSED"
echo "Clippy:        PASSED (bare-metal skipped)"
echo "Build:         PASSED (bare-metal skipped)"
echo "Tests:         PASSED"
echo "Binary crates: $OVERALL_PASSED/$OVERALL_TOTAL passed"
echo "Local scripts: $([ $LOCAL_RUN_FAILED -eq 0 ] && echo 'PASSED' || echo 'FAILED')"
echo ""

if [ ${#OVERALL_FAILED[@]} -eq 0 ] && [ $LOCAL_RUN_FAILED -eq 0 ]; then
    echo "═════════════════════════════════════════════════════════════"
    echo "  ALL VALIDATIONS PASSED!"
    echo "═════════════════════════════════════════════════════════════"
    echo ""
    exit 0
else
    echo "═════════════════════════════════════════════════════════════"
    echo "  SOME VALIDATIONS FAILED!"
    echo "═════════════════════════════════════════════════════════════"
    echo ""
    echo "Failed items:"
    for failed in "${OVERALL_FAILED[@]}"; do
        echo "  - $failed"
    done
    echo ""
    exit 1
fi
