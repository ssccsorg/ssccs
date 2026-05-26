#!/usr/bin/env bash
# sv2dot.sh — Synthesize SV modules with Yosys and produce gate-level DOT diagrams.
#
# Usage:   ./sv2dot.sh <sv_dir>
# Output:  _sv_dots/*.dot  (per-module DOT files)
#          arch_sv_diagram.qmd  (regenerated with inline DOT blocks)

set -euo pipefail

[ $# -ge 1 ] || { echo "Usage: $0 <sv_dir>" >&2; exit 1; }

SV_DIR="$1"
POC_DIR="$(cd "$(dirname "$0")" && pwd)"
DOTS_DIR="$POC_DIR/_sv_dots"
QMD_FILE="$POC_DIR/arch_sv_diagram.qmd"

# ── Prerequisite: DOT files must exist (from Yosys or pre-generated) ──
if ! ls "$DOTS_DIR"/*.dot &>/dev/null; then
    if command -v yosys &>/dev/null; then
        mkdir -p "$DOTS_DIR"
    else
        # No Yosys, no DOTs — create placeholder QMD and exit
        mkdir -p "$POC_DIR"
        cat > "$QMD_FILE" << 'EOF'
---
title: "PoC SystemVerilog Diagram"
subtitle: "Synthesized from POC RTL modules"
date: last-modified
metadata-files:
  - ../_include/author.yml
abstract: |
  Circuit diagrams for every SSCCS verification module.
---

{{< include ../_include/_title_meta_items.qmd >}}

*SV diagrams are not available — Yosys synthesis engine is not installed.*
EOF
        exit 0
    fi
fi

# ── Step 1: Synthesize (if yosys present) ─────────────────────────────
if command -v yosys &>/dev/null; then
    mkdir -p "$DOTS_DIR"
    while IFS= read -r -d '' sv_file; do
        mod=$(grep -m1 -oP '^\s*module\s+\K\w+' "$sv_file" || true)
        [ -z "$mod" ] && continue
        dot_file="$DOTS_DIR/${mod}.dot"
        if yosys -q -p "
            read_verilog -sv \"$sv_file\";
            synth -top $mod;
            show -format dot -prefix \"$DOTS_DIR/${mod}\" $mod;
        " 2>/dev/null; then
            echo "  $mod ← $(basename "$sv_file") ($(wc -l < "$dot_file") lines)"
        else
            echo "  FAIL $mod ← $(basename "$sv_file")"
        fi
    done < <(find "$SV_DIR" -name '*.sv' -print0)
fi

# ── Step 2: Generate QMD ──────────────────────────────────────────────

write_dot_cell() {
    local mod="$1" dotf="$2" h="${3:-300px}" cap="${4:-$mod}"
    echo "" >> "$QMD_FILE"
    echo "### $mod" >> "$QMD_FILE"
    echo "" >> "$QMD_FILE"
    echo '```{python}' >> "$QMD_FILE"
    echo "#| label: fig-$mod" >> "$QMD_FILE"
    echo "#| fig-cap: \"$cap\"" >> "$QMD_FILE"
    echo 'dot("""' >> "$QMD_FILE"
    cat "$dotf" >> "$QMD_FILE"
    echo '""", h="'"$h"'")' >> "$QMD_FILE"
    echo '```' >> "$QMD_FILE"
}

write_group() {
    local title="$1"; shift
    echo "" >> "$QMD_FILE"
    echo "## $title" >> "$QMD_FILE"
    while [ $# -ge 2 ]; do
        local mod="$1" h="$2"; shift 2
        local dotf="$DOTS_DIR/$mod.dot"
        [ -f "$dotf" ] && write_dot_cell "$mod" "$dotf" "$h"
    done
}

cat > "$QMD_FILE" << QMDHEAD
---
title: "PoC SystemVerilog Diagram"
subtitle: "Synthesized from POC RTL modules"
date: last-modified
metadata-files:
  - ../_include/author.yml
abstract: |
  Circuit diagrams for every SSCCS verification module.
  Each module is synthesized independently and rendered
  as a directed graph of its logic structure.
---

{{< include ../_include/_title_meta_items.qmd >}}

QMDHEAD

cat >> "$QMD_FILE" << 'QMDIMPORT'
```{python}
#| include: false
#| context: local
%run ../_include/_graphviz.py
```

QMDIMPORT

write_group "Constraints" \
    ck_even      200px \
    ck_range_010 300px \
    ck_range     300px \
    ck_eq        300px \
    ck_gt        300px

write_group "Composition" \
    compose_union         150px \
    compose_intersect     150px \
    compose_product_2d    150px

write_group "Projectors" \
    proj_identity   150px \
    proj_sum2d      400px \
    proj_sum3d      400px \
    proj_parity     150px \
    proj_negate     300px

if [ -f "$DOTS_DIR/observe.dot" ]; then
    write_dot_cell "observe" "$DOTS_DIR/observe.dot" "400px" "observe: gated projection pipeline"
fi

echo "Regenerated: $QMD_FILE"
