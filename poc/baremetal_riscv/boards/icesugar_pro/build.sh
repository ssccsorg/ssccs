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
# Build the POC's anchor images for the iCESugar-Pro, check them in simulation, and read them off the board.
#
#   ./build.sh rom                        generate the anchor tables and their negative control
#   ./build.sh sim [data|generated]       build the testbench and check the tables
#   ./build.sh build [pass|swap] [data|generated]
#                                         synthesise, place and route, pack a bitstream
#   ./build.sh flash [pass|swap] [data|generated]
#                                         write that bitstream to the board
#   ./build.sh read                       read the verdict pin
#   ./build.sh all                        rom, both simulations, and both bitstreams of each image
#
# `data` is ssccs_anchor_board: the constraint comes from the inquiry table, so one image answers an inquiry its
# fabric never saw. `generated` is ssccs_generated_board: the constraint is a module the host emitter wrote. Both
# drive the same seven nets and read the same three tables, so the anchors grade them the same way.
#
# nextpnr-ecp5 is not packaged by Homebrew. Put OSS CAD Suite on PATH before `build`, or set OSS_CAD_SUITE.
# icesprog is not packaged either. Pass it as ICESPROG or have it on PATH for `flash` and `read`.

set -euo pipefail
cd "$(dirname "$0")"

TOP=ssccs_anchor_board
GEN_TOP=ssccs_generated_board
DEC_TOP=ssccs_decoded_board
TB=ssccs_anchor_board_tb
GEN_TB=ssccs_generated_board_tb
DEC_TB=ssccs_decoded_board_tb
SV=../../sv
GEN="$SV/../generated"
# The units are the POC's list, asked for rather than repeated. Nothing here names a module.
UNITS=$(make -s -C "$SV" units)
# The low-level constraints are the same pins on the same carrier for all three images.
LPF=$TOP.lpf
REJTAG=1,3

if [ -n "${OSS_CAD_SUITE:-}" ]; then
    PATH="$OSS_CAD_SUITE/bin:$PATH"
fi
ICESPROG=${ICESPROG:-icesprog}

fail() { echo "$1" >&2; exit 1; }

# The image is a word rather than a second script: both tops drive the same nets and read the same tables, so the
# flow differs only in which files it reads and which top it builds.
choose() {
    local kind=${1:-data}
    case $kind in
        data)
            TOP_OF=$TOP
            TB_OF=$TB
            SOURCES="$TOP.sv $UNITS"
            ;;
        generated)
            TOP_OF=$GEN_TOP
            TB_OF=$GEN_TB
            SOURCES="$GEN_TOP.sv $UNITS $(generated_modules)"
            ;;
        decoded)
            TOP_OF=$DEC_TOP
            TB_OF=$DEC_TB
            SOURCES="$DEC_TOP.sv $UNITS $(generated_modules)"
            ;;
        *) fail "unknown image: $kind (data, generated or decoded)" ;;
    esac
}

# The emitter's own list of what it writes, so this file does not carry the module names.
generated_modules() {
    make -s -C "$SV" generated-modules
}

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
    local kind=${1:-data} n
    choose "$kind"
    n=$(image_count "$kind")
    echo "--- verilator: $TB_OF over $n addresses ---"
    verilator --binary --timing -DSIM -I"$SV" -GCOUNT="$n" --top-module "$TB_OF" \
        -Wno-fatal -Wno-WIDTH -Wno-UNUSED \
        "$TB_OF.sv" $SOURCES \
        -o "tb_$kind" --Mdir "obj_dir_$kind" > "out/build_tb_$kind.log" 2>&1 \
        || { cat "out/build_tb_$kind.log"; fail "verilator build failed"; }

    if [ "$kind" = decoded ]; then
        # The image has no table of points: the sweep is the address space itself, and the two files are the host's
        # count and one off it.
        decoded_table "$kind" 1 "$GEN/decode_count.hex"
        decoded_table "$kind" 0 "$GEN/decode_count_off.hex"
        return 0
    fi

    table "$kind" pass 1
    table "$kind" swap 0
    # A program fixed at generation time cannot answer an inquiry it was not generated for, so the generative
    # channel belongs to the image that carries kinds as data.
    if [ "$kind" = data ]; then
        table "$kind" generative 1
    fi
}

decoded_table() {
    local kind=$1 expect=$2 file=$3
    ./"obj_dir_$kind"/"tb_$kind" +count="$file" +expect="$expect"
}

# How many addresses the image sweeps. The anchor images take it from their table; the decoded one takes it from the
# space the host emitted.
image_count() {
    if [ "$1" = decoded ]; then
        printf '%d\n' "$((16#$(cat "$GEN/decode_space.hex")))"
    else
        count
    fi
}

# One table, one expected verdict. The generated image has no inquiry to pass, and says nothing about it.
table() {
    local kind=$1 dir=$2 expect=$3 inquiry=""
    if [ "$kind" = data ]; then
        inquiry="+inquiry=out/$dir/anchor_inquiry.hex"
    fi
    ./"obj_dir_$kind"/"tb_$kind" \
        +coord="out/$dir/anchor_coord.hex" \
        +narrow="out/$dir/anchor_narrow.hex" \
        +broad="out/$dir/anchor_broad.hex" \
        $inquiry +expect="$expect"
}

build() {
    local tag=${1:-pass} kind=${2:-data} n
    command -v yosys >/dev/null 2>&1 || fail "yosys is not on PATH"
    command -v nextpnr-ecp5 >/dev/null 2>&1 || fail "nextpnr-ecp5 is not on PATH; put OSS CAD Suite on PATH"
    command -v ecppack >/dev/null 2>&1 || fail "ecppack is not on PATH; put OSS CAD Suite on PATH"
    choose "$kind"
    n=$(image_count "$kind")
    if [ "$kind" = decoded ]; then
        # The decoded image reads one file: the host's count. There is no table of points to copy.
        mkdir -p out
        cp "$GEN/decode_count.hex" out/decode_count.hex
    else
        [ -d "out/$tag" ] || fail "no table at out/$tag; run ./build.sh rom first"
        # The top reads a fixed path, because readmemh resolves against the directory the flow runs in. Copying is
        # what lets one design build from more than one table.
        cp out/"$tag"/anchor_coord.hex out/"$tag"/anchor_narrow.hex out/"$tag"/anchor_broad.hex \
            out/"$tag"/anchor_inquiry.hex out/
    fi

    echo "--- yosys: $TOP_OF over $n anchors ---"
    yosys -q -p "read_verilog -sv -I$SV $SOURCES; chparam -set COUNT $n $TOP_OF; synth_ecp5 -top $TOP_OF -json out/$TOP_OF.json" \
        2>&1 | tee "out/synth_$kind.log" || fail "synthesis failed"
    [ -s "out/$TOP_OF.json" ] || fail "synthesis wrote no netlist"

    echo "--- nextpnr-ecp5: place and route ---"
    nextpnr-ecp5 --25k --package CABGA256 --speed 6 \
        --json "out/$TOP_OF.json" --lpf "$LPF" --textcfg "out/$TOP_OF.config" 2>&1 | tee "out/pnr_$kind.log" \
        || fail "place and route failed"

    echo "--- ecppack: bitstream ---"
    ecppack "out/$TOP_OF.config" "out/${TOP_OF}_$tag.bit"
    ls -l "out/${TOP_OF}_$tag.bit" | awk '{print "  " $9 " " $5 " bytes"}'
    grep -E "Max frequency|Device utilisation|TRELLIS_COMB|DP16KD" "out/pnr_$kind.log" | sed 's/^/  /' || true
}

flash() {
    local tag=${1:-pass} kind=${2:-data}
    choose "$kind"
    [ -f "out/${TOP_OF}_$tag.bit" ] || fail "no bitstream at out/${TOP_OF}_$tag.bit; run ./build.sh build $tag $kind"
    command -v "$ICESPROG" >/dev/null 2>&1 || fail "$ICESPROG is not on PATH; set ICESPROG"
    # PB7 drives the reset the image comes out of, and icesprog treats -m and -w as exclusive in one call.
    "$ICESPROG" -w "out/${TOP_OF}_$tag.bit"
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
    sim)   sim "${2:-data}" ;;
    build) build "${2:-pass}" "${3:-data}" ;;
    flash) flash "${2:-pass}" "${3:-data}" ;;
    read)  read ;;
    all)   rom; sim data; sim generated; sim decoded; \
           build pass data; build swap data; build pass generated; build swap generated; build pass decoded ;;
    *)     echo "usage: $0 [rom|sim [data|generated|decoded]|build [pass|swap] [data|generated|decoded]|flash [pass|swap] [data|generated|decoded]|read|all]" >&2; exit 2 ;;
esac
