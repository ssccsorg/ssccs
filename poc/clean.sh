#!/bin/bash
#
# SSCCS POC Clean Script
# Automatically discovers all Rust workspaces (Cargo.toml with [workspace])
# and standalone crates (Cargo.toml with [package] but not part of a workspace).
#
# Runs `cargo clean` on each discovered workspace/crate to remove build artifacts.
#
# Usage:
#   ./clean.sh [--workspace <path>]...
#
# Options:
#   --workspace   Specify a workspace path (can be used multiple times)
#                 If not specified, all workspaces/crates are auto-discovered
#

set -e

WORKSPACES=()

while [[ "$#" -gt 0 ]]; do
    case $1 in
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
echo "SSCCS POC - Clean Build Artifacts"
echo "─────────────────────────────────────────────────────────────"
echo "Workspaces to clean: ${WORKSPACES[@]}"
echo "Total workspaces: ${#WORKSPACES[@]}"
echo "─────────────────────────────────────────────────────────────"
echo ""

# ===========================================================================
# Run cargo clean on each workspace
# ===========================================================================
echo "Running cargo clean on each workspace..."
echo ""

CLEAN_FAILED=0
for ws in "${WORKSPACES[@]}"; do
    echo "  Cleaning: $ws"
    if (cd "$ws" && cargo clean 2>&1); then
        echo "    ✓ Cleaned"
    else
        echo "    ✗ Failed"
        CLEAN_FAILED=1
    fi
    echo ""
done

if [ $CLEAN_FAILED -eq 1 ]; then
    echo "Clean failed in one or more workspaces"
    exit 1
fi

echo "═════════════════════════════════════════════════════════════"
echo "  CLEAN COMPLETE!"
echo "═════════════════════════════════════════════════════════════"
echo ""
