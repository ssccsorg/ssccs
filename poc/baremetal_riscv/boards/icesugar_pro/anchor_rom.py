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
"""Write the anchor table the board image reads, from the anchors the POC already pins.

The scenario's three tables are in ``sv/_golden_anchors.svh``: the coordinates it asks about, the result the
narrow observation expects for each, and the result the broad one expects. The ROM is generated from that file
rather than transcribed, so the die cannot be handed a table the anchors do not hold.

The narrow and broad tables carry the reject sentinel (i64::MIN) where the scenario expects a rejection.

Usage:
    anchor_rom.py [--swap I,J] [--anchors PATH] OUT_DIR

``--swap`` exchanges two entries of the broad table, which is the negative control: the same coordinates, the same
multiset of expectations, and a table the die must refuse. It refuses to write a pair whose two entries are equal,
because that control would change nothing.
"""

import argparse
import pathlib
import re
import sys

REJECT = 0x8000000000000000

ANCHOR = re.compile(r"^`define\s+GOLDEN_(SEG|NARROW|BROAD)_(\d+)\s+64'([dh])([0-9A-Fa-f]+)\s*$")

NAMES = {"SEG": "anchor_coord.hex", "NARROW": "anchor_narrow.hex", "BROAD": "anchor_broad.hex"}
WIDTH = {"SEG": 4, "NARROW": 16, "BROAD": 16}


def read_anchors(path: pathlib.Path) -> dict[str, dict[int, int]]:
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
    return tables


def ordered(table: dict[int, int], name: str, path: pathlib.Path) -> list[int]:
    indices = sorted(table)
    if indices != list(range(len(indices))):
        raise SystemExit(f"{path}: GOLDEN_{name} is not numbered from zero without a gap: {indices}")
    return [table[index] for index in indices]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--anchors",
        default=str(pathlib.Path(__file__).resolve().parents[2] / "sv" / "_golden_anchors.svh"),
        help="the anchors file the ROM is generated from",
    )
    parser.add_argument("--swap", default="", help="two entries of the broad table to exchange, for the negative control")
    parser.add_argument("out_dir", help="where to write the three tables")
    args = parser.parse_args()

    anchors = pathlib.Path(args.anchors)
    tables = read_anchors(anchors)
    coord = ordered(tables["SEG"], "SEG", anchors)
    narrow = ordered(tables["NARROW"], "NARROW", anchors)
    broad = ordered(tables["BROAD"], "BROAD", anchors)
    if not len(coord) == len(narrow) == len(broad):
        raise SystemExit(
            f"{anchors}: the tables disagree in length: {len(coord)} coordinates, {len(narrow)} narrow, "
            f"{len(broad)} broad"
        )

    swapped = ""
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
        swapped = f", broad {broad[second]:X} and {broad[first]:X} exchanged"

    out = pathlib.Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for name, values in (("SEG", coord), ("NARROW", narrow), ("BROAD", broad)):
        (out / NAMES[name]).write_text("".join(f"{value:0{WIDTH[name]}X}\n" for value in values))

    rejected = sum(1 for value in narrow if value == REJECT)
    print(f"{len(coord)} anchors, {rejected} of them rejections{swapped}")
    print("  coord  " + " ".join(f"{value:4d}" for value in coord))
    print("  narrow " + " ".join(f"{'REJECT' if value == REJECT else value}" for value in narrow))
    print("  broad  " + " ".join(f"{'REJECT' if value == REJECT else value}" for value in broad))


if __name__ == "__main__":
    sys.exit(main())
