#!/usr/bin/env python3
"""
SSCCS Golden Anchor Consistency Check

Extracts golden anchor values from asm/observe_full.S comments and
compares them against sv/_golden_anchors.svh define directives.

Usage:
    python3 check_golden_anchors.py [--asm-dir ASM_DIR] [--svh SVH_FILE]

Exit code:
    0 — all anchors consistent
    1 — mismatch found

The asm/*.S file is the single source of truth for golden anchor values.
The sv/_golden_anchors.svh must match.
"""

import re
import sys
import os
from pathlib import Path

REJECT_SENTINEL = "0x8000000000000000"
REJECT_DECIMAL = str(-(2 ** 63))


def parse_asm_anchors(asm_path: Path) -> dict[str, list[str]]:
    """Parse GOLDEN TEST ANCHOR block from a .S file.
    Returns dict of anchor_name → list of value strings.
    """
    anchors: dict[str, list[str]] = {}
    in_block = False

    with open(asm_path) as f:
        for line in f:
            stripped = line.strip()
            if "GOLDEN TEST ANCHOR" in stripped:
                in_block = True
                continue
            if not in_block:
                continue
            if not stripped.startswith("#"):
                continue
            m = re.match(r"#\s*GOLDEN_(\w+):\s*(.+)", stripped)
            if m:
                name = m.group(1)
                values = [v.strip() for v in m.group(2).split(",")]
                anchors[name] = values
    return anchors


def parse_svh_defines(svh_path: Path) -> dict[str, str]:
    """Parse `define directives from _golden_anchors.svh.
    Returns dict of GOLDEN_* → value string.
    """
    defines: dict[str, str] = {}
    with open(svh_path) as f:
        for line in f:
            m = re.match(r"`define\s+(GOLDEN_\w+)\s+(.+)", line)
            if m:
                name = m.group(1)
                value = m.group(2).strip()
                defines[name] = value
    return defines


def normalize_svh_value(raw: str) -> str:
    """Normalize a .svh define value to a comparable string."""
    raw = raw.strip()
    # 64'dN or 64'hHEX
    if raw.startswith("64'd"):
        return raw[4:]
    if raw.startswith("64'h"):
        hex_val = raw[4:]
        # convert to signed i64 decimal
        val = int(hex_val, 16)
        if val >= 2 ** 63:
            val -= 2 ** 64
        return str(val)
    return raw


def normalize_asm_value(raw: str) -> str:
    """Normalize an .S anchor value to a comparable decimal string."""
    raw = raw.strip()
    if raw.upper() == "REJECT":
        return REJECT_DECIMAL
    # Try integer
    try:
        return str(int(raw))
    except ValueError:
        return raw


def check_anchors(
    asm_path: Path, svh_path: Path
) -> tuple[int, list[str]]:
    """Check golden anchor consistency between .S and .svh.
    Returns (mismatch_count, error_messages).
    """
    asm_anchors = parse_asm_anchors(asm_path)
    svh_defines = parse_svh_defines(svh_path)

    errors: list[str] = []
    checked = 0

    # Map high-level .S anchor names to .svh define names
    # SEGMENTS → SEG_0..SEG_N
    if "SEGMENTS" in asm_anchors:
        values = asm_anchors["SEGMENTS"]
        for i, val in enumerate(values):
            svh_name = f"GOLDEN_SEG_{i}"
            norm_asm = normalize_asm_value(val)
            if svh_name not in svh_defines:
                errors.append(f"MISSING: {svh_name} in .svh")
                continue
            norm_svh = normalize_svh_value(svh_defines[svh_name])
            if norm_asm != norm_svh:
                errors.append(
                    f"MISMATCH: {svh_name}: .S={norm_asm}, .svh={norm_svh}"
                )
            checked += 1

    # NARROW → NARROW_0..NARROW_N
    if "NARROW" in asm_anchors:
        values = asm_anchors["NARROW"]
        for i, val in enumerate(values):
            svh_name = f"GOLDEN_NARROW_{i}"
            norm_asm = normalize_asm_value(val)
            if svh_name not in svh_defines:
                errors.append(f"MISSING: {svh_name} in .svh")
                continue
            norm_svh = normalize_svh_value(svh_defines[svh_name])
            if norm_asm != norm_svh:
                errors.append(
                    f"MISMATCH: {svh_name}: .S={norm_asm}, .svh={norm_svh}"
                )
            checked += 1

    # BROAD → BROAD_0..BROAD_N
    if "BROAD" in asm_anchors:
        values = asm_anchors["BROAD"]
        for i, val in enumerate(values):
            svh_name = f"GOLDEN_BROAD_{i}"
            norm_asm = normalize_asm_value(val)
            if svh_name not in svh_defines:
                errors.append(f"MISSING: {svh_name} in .svh")
                continue
            norm_svh = normalize_svh_value(svh_defines[svh_name])
            if norm_asm != norm_svh:
                errors.append(
                    f"MISMATCH: {svh_name}: .S={norm_asm}, .svh={norm_svh}"
                )
            checked += 1

    # Scalar anchors: SUM3D_A, SUM3D_B, PARITY_2, PARITY_3
    for scalar_name in ("SUM3D_A", "SUM3D_B", "PARITY_2", "PARITY_3"):
        if scalar_name in asm_anchors:
            values = asm_anchors[scalar_name]
            if len(values) != 1:
                errors.append(f"BAD FORMAT: GOLDEN_{scalar_name} has {len(values)} values")
                continue
            svh_name = f"GOLDEN_{scalar_name}"
            norm_asm = normalize_asm_value(values[0])
            if svh_name not in svh_defines:
                errors.append(f"MISSING: {svh_name} in .svh")
                continue
            norm_svh = normalize_svh_value(svh_defines[svh_name])
            if norm_asm != norm_svh:
                errors.append(
                    f"MISMATCH: {svh_name}: .S={norm_asm}, .svh={norm_svh}"
                )
            checked += 1

    # Check REJECT_SENTINEL consistency
    if "REJECT_SENTINEL" in svh_defines:
        norm = normalize_svh_value(svh_defines["REJECT_SENTINEL"])
        if norm != REJECT_DECIMAL:
            errors.append(
                f"MISMATCH: REJECT_SENTINEL: expected {REJECT_DECIMAL}, "
                f"got {norm}"
            )
        checked += 1

    return len(errors), errors, checked


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    asm_path = script_dir.parent / "asm" / "observe_full.S"
    svh_path = script_dir / "_golden_anchors.svh"

    if not asm_path.exists():
        print(f"ERROR: .S file not found: {asm_path}", file=sys.stderr)
        return 1
    if not svh_path.exists():
        print(f"ERROR: .svh file not found: {svh_path}", file=sys.stderr)
        return 1

    errors_count, errors, checked = check_anchors(asm_path, svh_path)

    print(f"=== Golden Anchor Consistency Check ===")
    print(f"  .S source:  {asm_path.name}")
    print(f"  .svh:       {svh_path.name}")
    print(f"  Anchors checked: {checked}")

    if errors:
        print(f"  MISMATCHES: {errors_count}")
        for err in errors:
            print(f"    {err}")
        print(f"  RESULT: FAILED ({errors_count} mismatch(es))")
        return 1
    else:
        print(f"  RESULT: PASSED (all {checked} consistent)")
        return 0


if __name__ == "__main__":
    sys.exit(main())
