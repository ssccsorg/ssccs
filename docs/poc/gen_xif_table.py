#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-SSCCS-Research-Preview-1.0
# Copyright (c) 2026 Taeho Lee, SSCCS Initiative.
#
# Generate the XIF operation table from _xif_constants.svh. The docs page
# includes the result, so the table cannot drift from the constants.

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "poc" / "baremetal_riscv" / "sv" / "_xif_constants.svh"
OUTPUT = Path(__file__).resolve().parent / "_include" / "xif_table.md"

DEFINE = re.compile(r"`define\s+([A-Z][A-Z0-9_]+)\s+(\d+'[bdh][0-9a-fA-F_]+)")

# Opcode and funct3 that dispatch each sub-operation family.
GROUPS = (
    ("OPCODE_CUSTOM1", "FUNCT3_CONSTRAINT", "OP_CK_", "Constraint"),
    ("OPCODE_CUSTOM1", "FUNCT3_COMPOSE", "OP_COMPOSE_", "Composition"),
    ("OPCODE_CUSTOM2", "FUNCT3_PROJECT", "OP_PROJ_", "Projector"),
)

# Readable labels for the operation suffixes. An unmapped suffix keeps its
# lower-case form, so a new constant needs no script change.
LABELS = {
    "EVEN": "even",
    "RANGE_010": "range_010",
    "RANGE": "range",
    "EQ": "eq",
    "GT": "gt",
    "AND": "and",
    "OR": "or",
    "ID": "identity",
    "SUM2D": "sum2d",
    "SUM3D": "sum3d",
    "PARITY": "parity",
    "NEGATE": "negate",
}


def parse_literal(literal: str) -> int:
    _width, base = literal.split("'")
    digits = base[1:].replace("_", "")
    if base[0] == "b":
        return int(digits, 2)
    if base[0] == "d":
        return int(digits, 10)
    if base[0] == "h":
        return int(digits, 16)
    raise ValueError(f"unsupported literal: {literal}")


def main() -> int:
    text = SOURCE.read_text(encoding="utf-8")
    defines = {m.group(1): m.group(2) for m in DEFINE.finditer(text)}

    mapped: set[str] = set()
    rows: list[str] = []
    for opcode, funct3, prefix, group in GROUPS:
        if opcode not in defines or funct3 not in defines:
            raise SystemExit(f"missing {opcode} or {funct3} in {SOURCE}")
        operations = sorted(
            (
                (parse_literal(value), name[len(prefix):], name)
                for name, value in defines.items()
                if name.startswith(prefix)
            ),
            key=lambda item: item[0],
        )
        if not operations:
            raise SystemExit(f"no operations under {prefix} in {SOURCE}")
        mapped.update(name for _value, _suffix, name in operations)
        labels = ", ".join(
            LABELS.get(suffix, suffix.lower()) for _value, suffix, _name in operations
        )
        funct3_value = parse_literal(defines[funct3])
        encoding = f"{opcode.removeprefix('OPCODE_').lower()}, funct3={funct3_value:03b}"
        rows.append(f"| {encoding} | {group} | {labels} |")

    unmapped = sorted(
        name for name in defines if name.startswith("OP_") and name not in mapped
    )
    if unmapped:
        raise SystemExit(f"unmapped operation constants: {', '.join(unmapped)}")

    table = "\n".join(
        [
            "| Encoding | Group | Operations |",
            "|:---|:---|:---|",
            *rows,
            "",
        ]
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_suffix(".tmp")
    temporary.write_text(table, encoding="utf-8")
    temporary.replace(OUTPUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
