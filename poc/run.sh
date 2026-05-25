#!/bin/bash
#
# SSCCS POC Full Validation Script
# Automatically discovers all Rust workspaces (Cargo.toml with [workspace])
# and standalone crates (Cargo.toml with [package] but not part of a workspace),
# then runs all local module-level run.sh scripts (Spike tests, etc.).
#
# Usage:
#   ./run.sh [--validation|--run] [--workspace <path>]...
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

if [ ${#WORKSPACES[@]} -eq 0 ]; then
    echo "Auto-discovering Rust workspaces and crates..."
    
    WORKSPACE_ROOTS=""
    WORKSPACE_MEMBERS=""
    
    while IFS= read -r -d '' cargo_toml; do
        if grep -q '^\[workspace\]' "$cargo_toml" 2>/dev/null; then
            ws_dir=$(dirname "$cargo_toml")
            WORKSPACE_ROOTS="$WORKSPACE_ROOTS|$ws_dir|"
            
            in_workspace=false
            while IFS= read -r line; do
                if [[ "$line" == "[workspace]" ]]; then
                    in_workspace=true
                    continue
                fi
                if [[ "$line" == "["* ]] && [ "$in_workspace" = true ]; then
                    break
                fi
                if [ "$in_workspace" = true ]; then
                    member=$(echo "$line" | sed 's/.*"\([^"]*\)".*/\1/' | tr -d ' ,')
                    if [[ "$member" =~ ^(crates/|[a-zA-Z]) ]]; then
                        full_path="$ws_dir/$member"
                        full_path=$(cd "$full_path" 2>/dev/null && pwd || echo "$full_path")
                        WORKSPACE_MEMBERS="$WORKSPACE_MEMBERS|$full_path|"
                    fi
                fi
            done < "$cargo_toml"
        fi
    done < <(find . -name "Cargo.toml" -not -path "*/target/*" -print0 2>/dev/null)
    
    while IFS= read -r -d '' cargo_toml; do
        ws_dir=$(dirname "$cargo_toml")
        abs_ws_dir=$(cd "$ws_dir" 2>/dev/null && pwd || echo "$ws_dir")
        
        if grep -q '^\[workspace\]' "$cargo_toml" 2>/dev/null; then
            WORKSPACES+=("$ws_dir")
            echo "  Found workspace: $ws_dir"
        elif grep -q '^\[package\]' "$cargo_toml" 2>/dev/null; then
            is_member=false
            
            if [[ "$WORKSPACE_MEMBERS" == *"|$abs_ws_dir|"* ]]; then
                is_member=true
            fi
            
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

is_baremetal_workspace() {
    local ws="$1"
    grep -q '^\[package\.metadata\.rust-analyzer\]' "$ws/Cargo.toml" 2>/dev/null || \
    grep -q '^\[workspace\.metadata\.rust-analyzer\]' "$ws/Cargo.toml" 2>/dev/null || \
    grep -q 'target.*=.*"riscv' "$ws/Cargo.toml" 2>/dev/null
}

get_baremetal_target() {
    local ws="$1"
    grep -oP 'target\s*=\s*"\K[^"]+' "$ws/Cargo.toml" 2>/dev/null | head -1
}

# ── Step 0: Auto-fix before validation ──
# Runs compiler fixes, clippy lint fixes, then format — 
# catching unused imports, collapsible ifs, and style issues proactively.

echo "Step 0: Auto-fixing (cargo fix → clippy --fix → fmt)..."
for ws in "${WORKSPACES[@]}"; do
    echo "  Auto-fix: $ws"
    if is_baremetal_workspace "$ws"; then
        echo "    ⊘ Skipped (bare-metal)"
    else
        (cd "$ws" && cargo fix --allow-dirty --workspace 2>&1) || true
        (cd "$ws" && cargo clippy --fix --allow-dirty --workspace 2>&1) || true
        (cd "$ws" && cargo fmt --all 2>&1)
        echo "    ✓ Fixed"
    fi
done
echo "Auto-fix complete"
echo ""

if [ "$MODE" = "run" ]; then
    echo "Step 1: Applying formatting (cargo fmt --all)..."
    for ws in "${WORKSPACES[@]}"; do (cd "$ws" && cargo fmt --all); done
    echo "Code formatted"
    echo ""
fi

echo "Step 1: Checking formatting (cargo fmt --check)..."
FMT_FAILED=0
for ws in "${WORKSPACES[@]}"; do
    echo "  Checking: $ws"
    if (cd "$ws" && cargo fmt --check 2>&1); then echo "    ✓ Passed"; else echo "    ✗ Failed"; FMT_FAILED=1; fi
done
[ $FMT_FAILED -eq 1 ] && exit 1
echo "Formatting check passed"
echo ""

echo "─────────────────────────────────────────────────────────────"
echo "Step 2: Running clippy for each workspace..."
CLIPPY_FAILED=0
for ws in "${WORKSPACES[@]}"; do
    echo "  Clippy: $ws"
    if is_baremetal_workspace "$ws"; then
        echo "    ⊘ Skipped (bare-metal)"
    else
        (cd "$ws" && cargo clippy --workspace -- -D warnings 2>&1) && echo "    ✓ Passed" || { echo "    ✗ Failed"; CLIPPY_FAILED=1; }
    fi
done
[ $CLIPPY_FAILED -eq 1 ] && exit 1
echo "Clippy passed"
echo ""

echo "─────────────────────────────────────────────────────────────"
echo "Step 3: Building all workspaces (release mode)..."
BUILD_FAILED=0
for ws in "${WORKSPACES[@]}"; do
    echo "  Building: $ws"
    if is_baremetal_workspace "$ws"; then
        echo "    ⊘ Skipped (bare-metal)"
    else
        (cd "$ws" && cargo build --workspace --release 2>&1) && echo "    ✓ Built" || { echo "    ✗ Failed"; BUILD_FAILED=1; }
    fi
done
[ $BUILD_FAILED -eq 1 ] && exit 1
echo "Build successful"
echo ""

echo "─────────────────────────────────────────────────────────────"
echo "Step 4: Running all tests (host target)..."
TEST_FAILED=0
for ws in "${WORKSPACES[@]}"; do
    echo "  Testing: $ws"
    (cd "$ws" && cargo test --workspace --all-targets --release 2>&1) && echo "    ✓ Passed" || { echo "    ✗ Failed"; TEST_FAILED=1; }
done
[ $TEST_FAILED -eq 1 ] && exit 1
echo "All tests passed"
echo ""

echo "─────────────────────────────────────────────────────────────"
echo "Step 5: Discovering and running all binary crates..."

if ! command -v jq &> /dev/null; then
    echo "jq not found, installing..."
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then sudo apt-get update && sudo apt-get install -y jq
    elif [[ "$OSTYPE" == "darwin"* ]]; then brew install jq
    else echo "ERROR: jq required."; exit 1; fi
fi

ALL_FAILED=()
ALL_PASSED=0
ALL_TOTAL=0

for ws in "${WORKSPACES[@]}"; do
    echo "  Workspace: $ws"
    BIN_CRATES=$(cd "$ws" && cargo metadata --format-version=1 --no-deps 2>/dev/null | \
        jq -r '.packages[] | select(.targets[] | .kind[] | contains("bin")) | .name' 2>/dev/null | sort)
    [ -z "$BIN_CRATES" ] && echo "    No binary crates" && continue
    
    for crate in $BIN_CRATES; do
        ALL_TOTAL=$((ALL_TOTAL + 1))
        echo -n "    Running $crate... "
        if (cd "$ws" && cargo run --release --bin "$crate" --quiet 2>&1); then
            echo "SUCCESS"; ALL_PASSED=$((ALL_PASSED + 1))
        else
            echo "FAILED"; ALL_FAILED+=("$ws/$crate")
        fi
    done
done

echo ""
echo "─────────────────────────────────────────────────────────────"
echo "Step 6: Running local module-level run.sh scripts..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_FAILED=0

while IFS= read -r -d '' local_run; do
    [ "$local_run" = "$SCRIPT_DIR/run.sh" ] && continue
    [[ "$local_run" == */target/* || "$local_run" == */.git/* ]] && continue

    local_dir="$(dirname "$local_run")"
    rel="${local_dir#$SCRIPT_DIR/}"
    [ "$rel" = "$local_dir" ] && rel="$local_dir"

    echo ""
    echo "~~~~~~~~~~~~ $rel/run.sh ~~~~~~~~~~~~"

    if [ ! -x "$local_run" ] && ! head -1 "$local_run" 2>/dev/null | grep -q '^#!/'; then
        echo "  ⊘ Skipped (not executable, no shebang)"
        continue
    fi

    set +e
    (cd "$local_dir" && bash "$local_run" --check 2>&1)
    STATUS=$?
    set -e

    if [ $STATUS -eq 0 ]; then
        echo "~~~~~~~~~~~~ $rel/run.sh PASSED ~~~~~~~~~~~~"
    else
        echo "~~~~~~~~~~~~ $rel/run.sh FAILED (exit code $STATUS) ~~~~~~~~~~~~"
        LOCAL_FAILED=1
    fi
    echo ""
done < <(find "$SCRIPT_DIR" -name "run.sh" -not -path "*/baremetal_riscv/run.sh" -type f -print0 2>/dev/null)

[ $LOCAL_FAILED -eq 1 ] && ALL_FAILED+=("local run.sh scripts")

echo "═════════════════════════════════════════════════════════════"
echo "  Validation Summary"
echo "═════════════════════════════════════════════════════════════"
echo ""
echo "Formatting:    PASSED"
echo "Clippy:        PASSED (bare-metal skipped)"
echo "Build:         PASSED (bare-metal skipped)"
echo "Tests:         PASSED"
echo "Binary crates: $ALL_PASSED/$ALL_TOTAL passed"
echo "Local scripts: $([ $LOCAL_FAILED -eq 0 ] && echo 'PASSED' || echo 'FAILED')"
echo ""

if [ ${#ALL_FAILED[@]} -eq 0 ] && [ $LOCAL_FAILED -eq 0 ]; then
    echo "═════════════════════════════════════════════════════════════"
    echo "  ALL VALIDATIONS PASSED!"
    echo "═════════════════════════════════════════════════════════════"
    exit 0
else
    echo "═════════════════════════════════════════════════════════════"
    echo "  SOME VALIDATIONS FAILED!"
    echo "═════════════════════════════════════════════════════════════"
    for f in "${ALL_FAILED[@]}"; do echo "  - $f"; done
    exit 1
fi
