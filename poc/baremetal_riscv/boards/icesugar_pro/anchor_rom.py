#!/usr/bin/env python3
# SPDX-License-Identifier: CERN-OHL-P-2.0
# Copyright (C) 2026 Taeho Lee
#
# This source describes Open Hardware and is licensed under the CERN-OHL-P v2.
# You may redistribute and modify this documentation and make products using
# it under the terms of the CERN-OHL-P v2 (https://cern.ch/cern-ohl). This
# documentation is distributed WITHOUT ANY EXPRESS OR IMPLIED WARRANTY,
# INCLUDING OF MERCHANTABILITY, SATISFACTORY QUALITY AND FITNESS FOR A
# PARTICULAR PURPOSE. Please see the CERN-OHL-P v2 for applicable conditions.
"""Write the tables a board image reads, from the anchors the POC already pins.

The scenario's three tables are in ``sv/_golden_anchors.svh``: the coordinates it asks about, the result the
narrow observation expects for each, and the result the broad one expects. The ROM is generated from that file
rather than transcribed, so the die cannot be handed a table the anchors do not hold.

A fourth file is the inquiry: two selectors and a composition bit per observation. The selectors are the core's
unit table in ``sv/_units.svh``, read here rather than repeated, so the emitter and the substrate cannot disagree
about which unit a number means.

``--swap`` exchanges two entries of the broad table, which is the negative control: the same coordinates, the same
multiset of expectations, and a table the die must refuse.

``--generative`` writes a table for a different inquiry and computes its expectations here instead of reading
them. That is the check that the image carries the units rather than the scenario: the same design, a different
inquiry, and the emitter's own model as the grader.

Usage:
    anchor_rom.py [--swap I,J | --generative] [--anchors PATH] [--units PATH] OUT_DIR
"""

import argparse
import pathlib
import re
import sys

REJECT = 0x8000000000000000

ANCHOR = re.compile(r"^`define\s+GOLDEN_(SEG|NARROW|BROAD)_(\d+)\s+64'([dh])([0-9A-Fa-f]+)\s*$")
UNIT = re.compile(r"^`define\s+((?:UNIT|COMPOSE)_\w+)\s+(?:3'd|1'b)(\d+)\s*$")

NAMES = {
    "SEG": "anchor_coord.hex",
    "NARROW": "anchor_narrow.hex",
    "BROAD": "anchor_broad.hex",
    "PROGRAM": "anchor_inquiry.hex",
}
WIDTH = {"SEG": 4, "NARROW": 16, "BROAD": 16, "PROGRAM": 4}

# The host's model of the units an inquiry may name. The die's model is the SystemVerilog under sv/, written
# separately, so a table computed here is a second opinion rather than the same code twice.
UNITS = {
    "UNIT_EVEN": lambda coord: (coord & 1) == 0,
    "UNIT_RANGE_010": lambda coord: coord <= 10,
}


def read_units(path: pathlib.Path) -> dict[str, int]:
    units: dict[str, int] = {}
    for line in path.read_text().splitlines():
        found = UNIT.match(line)
        if found:
            units[found.group(1)] = int(found.group(2))
    for name in ("UNIT_EVEN", "UNIT_RANGE_010", "COMPOSE_AND", "COMPOSE_OR"):
        if name not in units:
            raise SystemExit(f"{path}: no {name}")
    return units


def read_anchors(path: pathlib.Path) -> tuple[dict[str, dict[int, int]], int]:
    tables: dict[str, dict[int, int]] = {"SEG": {}, "NARROW": {}, "BROAD": {}}
    sentinel = None
    for line in path.read_text().splitlines():
        if line.startswith("`define REJECT_SENTINEL"):
            sentinel = int(line.split("64'h")[1].strip(), 16)
            continue
        found = ANCHOR.match(line)
        if not found:
            continue
        table, index, base, value = found.groups()
        tables[table][int(index)] = int(value, 16 if base == "h" else 10)
    if sentinel is None:
        raise SystemExit(f"{path}: no REJECT_SENTINEL, so the rejections cannot be recognised")
    if sentinel != REJECT:
        raise SystemExit(f"{path}: REJECT_SENTINEL is {sentinel:016X}, and observe() emits {REJECT:016X}")
    for table in ("SEG", "NARROW", "BROAD"):
        if not tables[table]:
            raise SystemExit(f"{path}: no GOLDEN_{table} anchors")
    return tables, sentinel


def ordered(table: dict[int, int], name: str, path: pathlib.Path) -> list[int]:
    indices = sorted(table)
    if indices != list(range(len(indices))):
        raise SystemExit(f"{path}: GOLDEN_{name} is not numbered from zero without a gap: {indices}")
    return [table[index] for index in indices]


def inquiry_word(narrow: tuple[int, int, int], broad: tuple[int, int, int]) -> int:
    # Layout the substrate decodes: narrow a[13:11] b[10:8] op[7], broad a[6:4] b[3:1] op[0].
    return (
        (narrow[0] << 11)
        | (narrow[1] << 8)
        | (narrow[2] << 7)
        | (broad[0] << 4)
        | (broad[1] << 1)
        | broad[2]
    )


def observe(coord: int, valid: bool, sentinel: int) -> int:
    return coord if valid else sentinel


def names_of(units: dict[str, int], value: int) -> str:
    return next((name for name, number in units.items() if number == value), str(value))


def compose(pick: tuple[int, int, int], coord: int, units: dict[str, int]) -> bool:
    a = UNITS[names_of(units, pick[0])](coord)
    b = UNITS[names_of(units, pick[1])](coord)
    return (a or b) if pick[2] == units["COMPOSE_OR"] else (a and b)


def main() -> None:
    here = pathlib.Path(__file__).resolve()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--anchors", default=str(here.parents[2] / "sv" / "_golden_anchors.svh"))
    parser.add_argument("--units", default=str(here.parents[2] / "sv" / "_units.svh"))
    parser.add_argument("--swap", default="", help="two entries of the broad table to exchange, for the negative control")
    parser.add_argument(
        "--generative",
        action="store_true",
        help="write a table for a different inquiry and compute its expectations here",
    )
    parser.add_argument("out_dir", help="where to write the four tables")
    args = parser.parse_args()

    units = read_units(pathlib.Path(args.units))
    anchors = pathlib.Path(args.anchors)
    tables, sentinel = read_anchors(anchors)
    coord = ordered(tables["SEG"], "SEG", anchors)
    narrow = ordered(tables["NARROW"], "NARROW", anchors)
    broad = ordered(tables["BROAD"], "BROAD", anchors)
    if not len(coord) == len(narrow) == len(broad):
        raise SystemExit(
            f"{anchors}: the tables disagree in length: {len(coord)} coordinates, {len(narrow)} narrow, "
            f"{len(broad)} broad"
        )

    note = ""
    if args.generative and args.swap:
        raise SystemExit("--swap and --generative write different tables; ask for one")

    if args.generative:
        # The same two units, composed the other way round. Every coordinate that the anchored tables call a
        # rejection of one observation is a value of the other, so a design that had the scenario in it would fail.
        inquiry_narrow = (units["UNIT_EVEN"], units["UNIT_RANGE_010"], units["COMPOSE_OR"])
        inquiry_broad = (units["UNIT_EVEN"], units["UNIT_RANGE_010"], units["COMPOSE_AND"])
        narrow = [observe(value, compose(inquiry_narrow, value, units), sentinel) for value in coord]
        broad = [observe(value, compose(inquiry_broad, value, units), sentinel) for value in coord]
        note = " for a different inquiry, with the expectations computed here"
    else:
        inquiry_narrow = (units["UNIT_EVEN"], units["UNIT_RANGE_010"], units["COMPOSE_AND"])
        inquiry_broad = (units["UNIT_EVEN"], units["UNIT_RANGE_010"], units["COMPOSE_OR"])

    if args.swap:
        first, second = (int(part) for part in args.swap.split(","))
        for index in (first, second):
            if not 0 <= index < len(broad):
                raise SystemExit(f"--swap {args.swap} is outside the {len(broad)} anchors")
        if broad[first] == broad[second] or REJECT in (broad[first], broad[second]):
            raise SystemExit(
                f"anchors {first} and {second} cannot be exchanged: {broad[first]:016X} and {broad[second]:016X}"
            )
        broad[first], broad[second] = broad[second], broad[first]
        note = f", broad {broad[second]:X} and {broad[first]:X} exchanged"

    out = pathlib.Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for name, values in (("SEG", coord), ("NARROW", narrow), ("BROAD", broad)):
        (out / NAMES[name]).write_text("".join(f"{value:0{WIDTH[name]}X}\n" for value in values))
    word = inquiry_word(inquiry_narrow, inquiry_broad)
    (out / NAMES["PROGRAM"]).write_text(f"{word:04X}\n")

    rejected = sum(1 for value in narrow if value == REJECT)
    print(f"{len(coord)} anchors, {rejected} of them rejections{note}")
    print(f"  inquiry {word:04X}: narrow {inquiry_narrow}, broad {inquiry_broad}")
    print("  coord  " + " ".join(f"{value:4d}" for value in coord))
    print("  narrow " + " ".join(f"{'REJECT' if value == REJECT else value}" for value in narrow))
    print("  broad  " + " ".join(f"{'REJECT' if value == REJECT else value}" for value in broad))


if __name__ == "__main__":
    sys.exit(main())
