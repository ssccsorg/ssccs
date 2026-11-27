#!/usr/bin/env bash
#
# SPDX-License-Identifier: LicenseRef-SSCCS-Research-Preview-1.0
# Copyright (c) 2026 Taeho Lee, SSCCS Initiative.
#
# Owned by the SSCCS Initiative. See LICENSE at the root of this proof of
# concept: a copy carries this notice and the revision it was taken from.
#
# Render the visual assets from the hardware units and the hand-authored
# timing and FSM sources. Writes SVG and PNG into visuals/out/.
#
# Requires: yosys, graphviz (dot), node with npx. One of rsvg-convert,
# ImageMagick (magick or convert), or Inkscape for SVG to PNG.

set -euo pipefail

VIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
POC_DIR="$(cd "$VIS_DIR/.." && pwd)"
SV_DIR="$POC_DIR/baremetal_riscv/sv"
OUT="$VIS_DIR/out"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

need() {
  command -v "$1" >/dev/null 2>&1 || { echo "missing required tool: $1" >&2; exit 1; }
}

need yosys
need dot
need node

if command -v rsvg-convert >/dev/null 2>&1; then
  RASTER=rsvg
elif command -v magick >/dev/null 2>&1; then
  RASTER=magick
elif command -v convert >/dev/null 2>&1; then
  RASTER=convert
elif command -v inkscape >/dev/null 2>&1; then
  RASTER=inkscape
else
  echo "missing an SVG rasterizer: install rsvg-convert, ImageMagick, or Inkscape" >&2
  exit 1
fi

rasterize() { # svg png
  case "$RASTER" in
    rsvg)     rsvg-convert -o "$2" "$1" ;;
    magick)   magick "$1" "$2" ;;
    convert)  convert "$1" "$2" ;;
    inkscape) inkscape "$1" --export-type=png --export-filename="$2" >/dev/null 2>&1 ;;
  esac
  # Flatten any transparency to white and keep a small margin around the drawing.
  im=""
  if command -v magick >/dev/null 2>&1; then im=magick
  elif command -v convert >/dev/null 2>&1; then im=convert
  fi
  if [ -n "$im" ]; then
    "$im" "$2" -background white -alpha remove -alpha off -bordercolor white -border 16 "$2.tmp.png" && mv "$2.tmp.png" "$2"
  fi
}

run_netlistsvg() {
  if command -v netlistsvg >/dev/null 2>&1; then command netlistsvg "$@"; else npx --yes netlistsvg@1.0.2 "$@"; fi
}

run_wavedrom() {
  if command -v wavedrom-cli >/dev/null 2>&1; then command wavedrom-cli "$@"; else npx --yes wavedrom-cli@3.2.0 "$@"; fi
}

rm -rf "$OUT"
mkdir -p "$OUT/graphviz" "$OUT/wavedrom" "$OUT/netlist"

echo "Graphviz"
for dotf in "$VIS_DIR"/graphviz/*.dot; do
  name="$(basename "$dotf" .dot)"
  dot -Tsvg "$dotf" -o "$OUT/graphviz/$name.svg"
  dot -Tpng -Gdpi=160 "$dotf" -o "$OUT/graphviz/$name.png"
  echo "  out/graphviz/$name.svg, out/graphviz/$name.png"
done

echo "WaveDrom"
for wdf in "$VIS_DIR"/wavedrom/*.json5; do
  name="$(basename "$wdf" .json5)"
  run_wavedrom -i "$wdf" -s "$OUT/wavedrom/$name.svg" -p "$OUT/wavedrom/$name.png"
  echo "  out/wavedrom/$name.svg, out/wavedrom/$name.png"
done

echo "NetlistSVG (Yosys JSON)"
while IFS='|' read -r module src; do
  [ -z "${module:-}" ] && continue
  case "$module" in \#*) continue ;; esac
  json="$WORK/$module.json"
  yosys -q -p "read_verilog -sv -I$SV_DIR $SV_DIR/$src; hierarchy -top $module; proc; write_json $json"
  run_netlistsvg "$json" -o "$OUT/netlist/$module.svg"
  rasterize "$OUT/netlist/$module.svg" "$OUT/netlist/$module.png"
  echo "  out/netlist/$module.svg, out/netlist/$module.png"
done < "$VIS_DIR/netlistsvg/units.txt"

echo "done: $OUT"
