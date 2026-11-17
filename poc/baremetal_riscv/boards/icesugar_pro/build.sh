#!/usr/bin/env bash
# SPDX-License-Identifier: CERN-OHL-P-2.0
# Copyright (C) 2026 Taeho Lee
#
# This source describes Open Hardware and is licensed under the CERN-OHL-P v2.
# You may redistribute and modify this documentation and make products using
# it under the terms of the CERN-OHL-P v2 (https://cern.ch/cern-ohl). This
# documentation is distributed WITHOUT ANY EXPRESS OR IMPLIED WARRANTY,
# INCLUDING OF MERCHANTABILITY, SATISFACTORY QUALITY AND FITNESS FOR A
# PARTICULAR PURPOSE. Please see the CERN-OHL-P v2 for applicable conditions.
#
# Build the POC's anchor image for the iCESugar-Pro, check it in simulation, and read it off the board.
#
#   ./build.sh rom              generate the anchor tables and their negative control
#   ./build.sh sim              build the testbench and check both tables
#   ./build.sh build [pass|swap]  synthesise, place and route, pack a bitstream
#   ./build.sh flash [pass|swap]  write that bitstream to the board
#   ./build.sh read             read the verdict pin
#   ./build.sh all              rom, sim, and both bitstreams
#
# nextpnr-ecp5 is not packaged by Homebrew. Put OSS CAD Suite on PATH before `build`, or set OSS_CAD_SUITE.
# icesprog is not packaged either. Pass it as ICESPROG or have it on PATH for `flash` and `read`.

set -euo pipefail
cd "$(dirname "$0")"

TOP=ssccs_anchor_board
TB=ssccs_anchor_board_tb
SV=../../sv
# The units are the POC's list, asked for rather than repeated. Nothing here names a module.
UNITS=$(make -s -C "$SV" units)
SOURCES="$TOP.sv $UNITS"
LPF=$TOP.lpf
REJTAG=1,3

if [ -n "${OSS_CAD_SUITE:-}" ]; then
    PATH="$OSS_CAD_SUITE/bin:$PATH"
fi
ICESPROG=${ICESPROG:-icesprog}

fail() { echo "$1" >&2; exit 1; }

lines_of() {
    # Lines of data, not newlines: a file whose last line has no newline would otherwise be one short of what
    # readmemh loads, and the sweep would skip that line without saying so.
    grep -cE '^[0-9A-Fa-f]+$' "$1" || true
}

rom() {
    command -v python3 >/dev/null 2>&1 || fail "python3 is not on PATH"
    mkdir -p out
    echo "--- anchors: the scenario's table, and the same table with two expectations exchanged ---"
    python3 anchor_rom.py out/pass
    python3 anchor_rom.py --swap "$REJTAG" out/swap
    echo "--- the same units, composed the other way round ---"
    python3 anchor_rom.py --generative out/generative
}

count() {
    [ -f out/pass/anchor_coord.hex ] || fail "no anchor table; run ./build.sh rom first"
    local n
    n=$(lines_of out/pass/anchor_coord.hex)
    [ "$n" -gt 0 ] || fail "the anchor table holds no line, so there is nothing to compare"
    if [ "$(lines_of out/pass/anchor_narrow.hex)" != "$n" ] || [ "$(lines_of out/pass/anchor_broad.hex)" != "$n" ]; then
        fail "the three tables disagree in length"
    fi
    echo "$n"
}

sim() {
    command -v verilator >/dev/null 2>&1 || fail "verilator is not on PATH"
    local n
    n=$(count)
    echo "--- verilator: $TB over $n anchors, both controls ---"
    verilator --binary --timing -DSIM -I"$SV" -GCOUNT="$n" --top-module "$TB" \
        -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-PROCASSINIT \
        "$TB.sv" "$TOP.sv" $UNITS \
        -o tb_anchor > out/build_tb.log 2>&1 || { cat out/build_tb.log; fail "verilator build failed"; }
    ./obj_dir/tb_anchor \
        +coord=out/pass/anchor_coord.hex +narrow=out/pass/anchor_narrow.hex +broad=out/pass/anchor_broad.hex \
        +inquiry=out/pass/anchor_inquiry.hex +expect=1
    ./obj_dir/tb_anchor \
        +coord=out/swap/anchor_coord.hex +narrow=out/swap/anchor_narrow.hex +broad=out/swap/anchor_broad.hex \
        +inquiry=out/swap/anchor_inquiry.hex +expect=0
    # The image carries the units rather than the scenario: a different inquiry, and the emitter's own model as
    # the grader, on the same build.
    ./obj_dir/tb_anchor \
        +coord=out/generative/anchor_coord.hex +narrow=out/generative/anchor_narrow.hex \
        +broad=out/generative/anchor_broad.hex +inquiry=out/generative/anchor_inquiry.hex +expect=1
}

build() {
    local tag=${1:-pass} n
    command -v yosys >/dev/null 2>&1 || fail "yosys is not on PATH"
    command -v nextpnr-ecp5 >/dev/null 2>&1 || fail "nextpnr-ecp5 is not on PATH; put OSS CAD Suite on PATH"
    command -v ecppack >/dev/null 2>&1 || fail "ecppack is not on PATH; put OSS CAD Suite on PATH"
    n=$(count)
    [ -d "out/$tag" ] || fail "no table at out/$tag; run ./build.sh rom first"
    # The top reads a fixed path, because readmemh resolves against the directory the flow runs in. Copying is what
    # lets one design build from more than one table.
    cp out/"$tag"/anchor_coord.hex out/"$tag"/anchor_narrow.hex out/"$tag"/anchor_broad.hex \
        out/"$tag"/anchor_inquiry.hex out/

    echo "--- yosys: $TOP over $n anchors ---"
    yosys -q -p "read_verilog -sv -I$SV $SOURCES; chparam -set COUNT $n $TOP; synth_ecp5 -top $TOP -json out/$TOP.json" \
        2>&1 | tee out/synth.log || fail "synthesis failed"
    [ -s "out/$TOP.json" ] || fail "synthesis wrote no netlist"

    echo "--- nextpnr-ecp5: place and route ---"
    nextpnr-ecp5 --25k --package CABGA256 --speed 6 \
        --json "out/$TOP.json" --lpf "$LPF" --textcfg "out/$TOP.config" 2>&1 | tee out/pnr.log \
        || fail "place and route failed"

    echo "--- ecppack: bitstream ---"
    ecppack "out/$TOP.config" "out/${TOP}_$tag.bit"
    ls -l "out/${TOP}_$tag.bit" | awk '{print "  " $9 " " $5 " bytes"}'
    grep -E "Max frequency|Device utilisation|TRELLIS_COMB|DP16KD" out/pnr.log | sed 's/^/  /' || true
}

flash() {
    local tag=${1:-pass}
    [ -f "out/${TOP}_$tag.bit" ] || fail "no bitstream at out/${TOP}_$tag.bit; run ./build.sh build $tag"
    command -v "$ICESPROG" >/dev/null 2>&1 || fail "$ICESPROG is not on PATH; set ICESPROG"
    # PB7 drives the reset the image comes out of, and icesprog treats -m and -w as exclusive in one call.
    "$ICESPROG" -w "out/${TOP}_$tag.bit"
    "$ICESPROG" -g PB7 -m out
    "$ICESPROG" -g PB7 -w 0
    sleep 1
    "$ICESPROG" -g PB7 -w 1
}

read() {
    command -v "$ICESPROG" >/dev/null 2>&1 || fail "$ICESPROG is not on PATH; set ICESPROG"
    "$ICESPROG" -g PA13 -m in
    # The part answers about two seconds after it is released, so a read before that is the image being replaced.
    sleep 3
    "$ICESPROG" -g PA13 -r
}

case ${1:-all} in
    rom)   rom ;;
    sim)   sim ;;
    build) build "${2:-pass}" ;;
    flash) flash "${2:-pass}" ;;
    read)  read ;;
    all)   rom; sim; build pass; build swap ;;
    *)     echo "usage: $0 [rom|sim|build [pass|swap]|flash [pass|swap]|read|all]" >&2; exit 2 ;;
esac
