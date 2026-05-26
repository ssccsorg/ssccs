#!/usr/bin/env bash
# sv2dot.sh — Synthesize SV modules with Yosys and produce gate-level DOT diagrams.
#
# Usage:
#   ./scripts/sv2dot.sh <sv_dir> <out_dir>
#
# Reads all .sv files in <sv_dir> (recursive), synthesizes each module
# with Yosys, and writes a .dot file to <out_dir>.
#
# Requires: yosys
#
# Output: <out_dir>/<module_name>.dot for each synthesizable module.

set -euo pipefail

if [ $# -lt 2 ]; then
    echo "Usage: $0 <sv_dir> <out_dir>" >&2
    exit 1
fi

SV_DIR="$1"
OUT_DIR="$2"

if ! command -v yosys &>/dev/null; then
    mkdir -p "$OUT_DIR"
    exit 0
fi

mkdir -p "$OUT_DIR"
WORK_DIR="$(mktemp -d 2>/dev/null || mktemp -d -t 'sv2dot')"
trap 'rm -rf "$WORK_DIR"' EXIT

count=0
skip=0

while IFS= read -r -d '' sv_file; do
    # Extract module name from file (first module declaration)
    mod=$(grep -m1 -oP '^\s*module\s+\K\w+' "$sv_file" || true)
    if [ -z "$mod" ]; then
        echo "  SKIP $(basename "$sv_file"): no module declaration found"
        skip=$((skip + 1))
        continue
    fi

    dot_out="$OUT_DIR/${mod}.dot"
    echo "  $mod ← $(basename "$sv_file")"

    # Run Yosys: read SV file, synthesize, export DOT
    # Suppress stderr noise, capture only errors
    if yosys -q -p "
        read_verilog -sv \"$sv_file\";
        synth -top $mod;
        show -format dot -prefix \"$OUT_DIR/${mod}\" $mod;
    " 2>/dev/null; then
        count=$((count + 1))
    else
        echo "  FAIL $mod: Yosys synthesis error"
        skip=$((skip + 1))
    fi
done < <(find "$SV_DIR" -name '*.sv' -print0)

echo "Done: $count modules synthesized, $skip skipped"
