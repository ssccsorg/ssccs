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

A fourth file is the inquiry: a descriptor naming the two constraint kinds and the composition for each
observation, then two 64-bit operands per kind. The kind numbers are the core's unit table in ``sv/_units.svh``,
read here rather than repeated, and the bounds are data, so a constraint is a kind and two numbers rather than a
module name.

``--swap`` exchanges two entries of the broad table, which is the negative control: the same coordinates, the same
multiset of expectations, and a table the die must refuse.

``--generative`` writes an inquiry that uses kinds and bounds the anchored scenario never uses, and computes the
expectations here instead of reading them. That is the check that the image carries the units and the table
carries the constraint: the same design, a different inquiry, and the emitter's own model as the grader.

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
WIDTH = {"SEG": 16, "NARROW": 16, "BROAD": 16, "PROGRAM": 16}

# The host's model of each kind. The die's model is the SystemVerilog under sv/, written separately, so a table
# computed here is a second opinion rather than the same code twice.
KINDS = {
    "UNIT_EVEN": lambda coord, low, high: (coord & 1) == 0,
    "UNIT_RANGE": lambda coord, low, high: low <= coord <= high,
    "UNIT_EQ": lambda coord, low, high: coord == low,
    "UNIT_GT": lambda coord, low, high: coord > low,
}


def read_units(path: pathlib.Path) -> dict[str, int]:
    units: dict[str, int] = {}
    for line in path.read_text().splitlines():
        found = UNIT.match(line)
        if found:
            units[found.group(1)] = int(found.group(2))
    for name in ("UNIT_EVEN", "UNIT_RANGE", "UNIT_EQ", "UNIT_GT", "COMPOSE_AND", "COMPOSE_OR"):
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


def slot(kind: int, low: int = 0, high: int = 0) -> tuple[int, int, int]:
    return (kind, low, high)


def descriptor(a: tuple, b: tuple, op: int, c: tuple, d: tuple, other: int) -> int:
    # Layout the substrate decodes: narrow a[13:11] b[10:8] op[7], broad a[6:4] b[3:1] op[0].
    return (a[0] << 11) | (b[0] << 8) | (op << 7) | (c[0] << 4) | (d[0] << 1) | other


def observe(coord: int, valid: bool, sentinel: int) -> int:
    return coord if valid else sentinel


def value_of(units: dict[str, int], number: int) -> str:
    return next((name for name, other in units.items() if other == number), "")


def compose(units: dict[str, int], first: tuple, second: tuple, op: int, coord: int) -> bool:
    a = KINDS[value_of(units, first[0])](coord, first[1], first[2])
    b = KINDS[value_of(units, second[0])](coord, second[1], second[2])
    return (a or b) if op == units["COMPOSE_OR"] else (a and b)


def main() -> None:
    here = pathlib.Path(__file__).resolve()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--anchors", default=str(here.parents[2] / "sv" / "_golden_anchors.svh"))
    parser.add_argument("--units", default=str(here.parents[2] / "sv" / "_units.svh"))
    parser.add_argument("--swap", default="", help="two entries of the broad table to exchange, for the negative control")
    parser.add_argument(
        "--generative",
        action="store_true",
        help="write an inquiry of kinds and bounds the scenario never uses, and compute its expectations here",
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
    if args.generative and args.swap:
        raise SystemExit("--swap and --generative write different tables; ask for one")

    if args.generative:
        # Kinds and bounds the anchored scenario never uses: a threshold on one side, equality on the other.
        coord = [-2, 3, 5, 10, 12]
        narrow_a = slot(units["UNIT_EVEN"])
        narrow_b = slot(units["UNIT_GT"], -1)
        broad_a = slot(units["UNIT_RANGE"], -10, 10)
        broad_b = slot(units["UNIT_EQ"], -2)
        narrow_op = units["COMPOSE_AND"]
        broad_op = units["COMPOSE_OR"]
        narrow = [observe(value, compose(units, narrow_a, narrow_b, narrow_op, value), sentinel) for value in coord]
        broad = [observe(value, compose(units, broad_a, broad_b, broad_op, value), sentinel) for value in coord]
        note = " of an inquiry the scenario never uses, with the expectations computed here"
    else:
        narrow_a = slot(units["UNIT_EVEN"])
        narrow_b = slot(units["UNIT_RANGE"], 0, 10)
        broad_a = slot(units["UNIT_EVEN"])
        broad_b = slot(units["UNIT_RANGE"], 0, 10)
        narrow_op = units["COMPOSE_AND"]
        broad_op = units["COMPOSE_OR"]
        note = ""

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
    exact = (1 << 64) - 1
    for name, values in (("SEG", coord), ("NARROW", narrow), ("BROAD", broad)):
        (out / NAMES[name]).write_text(
            "".join(f"{value & exact:0{WIDTH[name]}X}\n" for value in values)
        )

    # The inquiry: a descriptor, then two operands for each of the four slots the descriptor names.
    words = [
        descriptor(narrow_a, narrow_b, narrow_op, broad_a, broad_b, broad_op),
        narrow_a[1], narrow_a[2],
        narrow_b[1], narrow_b[2],
        broad_a[1], broad_a[2],
        broad_b[1], broad_b[2],
    ]
    (out / NAMES["PROGRAM"]).write_text("".join(f"{word & exact:016X}\n" for word in words))

    rejected = sum(1 for value in narrow if value == REJECT)
    print(f"{len(coord)} anchors, {rejected} of them rejections{note}")
    print(f"  inquiry {words[0]:04X}: narrow {narrow_a}+{narrow_b} op {narrow_op}, "
          f"broad {broad_a}+{broad_b} op {broad_op}")
    print("  coord  " + " ".join(f"{value:4d}" for value in coord))
    print("  narrow " + " ".join(f"{'REJECT' if value == REJECT else value}" for value in narrow))
    print("  broad  " + " ".join(f"{'REJECT' if value == REJECT else value}" for value in broad))


if __name__ == "__main__":
    sys.exit(main())
