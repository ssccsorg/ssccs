#!/usr/bin/env python3
"""SV → DOT → QMD pipeline.

Usage:
  python3 poc/sv2dot.py ../poc/baremetal_riscv/sv

Synthesizes each SV module with Yosys, writes DOT files to _sv_dots/,
and regenerates poc/arch_sv_diagram.qmd with inline DOT code blocks.
Silent skip when yosys is unavailable (placeholder QMD generated).
"""

import subprocess, shutil, sys, os, re
from pathlib import Path

POC_DIR = Path(__file__).resolve().parent
DOTS_DIR = POC_DIR / "_sv_dots"
QMD_FILE = POC_DIR / "arch_sv_diagram.qmd"
INCLUDE_DIR = POC_DIR.parent / "_include"

MODULES = [
    ("Constraints", [
        ("ck_even",         "200px"),
        ("ck_range_010",    "300px"),
        ("ck_range",        "300px"),
        ("ck_eq",           "300px"),
        ("ck_gt",           "300px"),
    ]),
    ("Composition", [
        ("compose_union",         "150px"),
        ("compose_intersect",     "150px"),
        ("compose_product_2d",    "150px"),
    ]),
    ("Projectors", [
        ("proj_identity",   "150px"),
        ("proj_sum2d",      "400px"),
        ("proj_sum3d",      "400px"),
        ("proj_parity",     "150px"),
        ("proj_negate",     "300px"),
    ]),
    ("Pipeline", [
        ("observe",         "400px"),
    ]),
]

TABLE_ROWS = [
    ("Constraints", "ck_even",          12,   "1-LUT even parity check"),
    ("Constraints", "ck_range_010",    485,   "Hard-coded [0,10] range check"),
    ("Constraints", "ck_range",        365,   "Parameterized [min, max] range check"),
    ("Constraints", "ck_eq",           325,   "64-bit equality check"),
    ("Constraints", "ck_gt",           325,   "64-bit greater-than comparator"),
    ("Composition", "compose_union",           15,    "OR reduction"),
    ("Composition", "compose_intersect",       15,    "AND reduction"),
    ("Composition", "compose_product_2d",      12,    "Axis partition (AND of two constraints)"),
    ("Projectors",  "proj_identity",   10,    "64-bit passthrough"),
    ("Projectors",  "proj_sum2d",    2498,   "64-bit adder"),
    ("Projectors",  "proj_sum3d",    4077,   "128-bit adder chain"),
    ("Projectors",  "proj_parity",     10,    "LSB extract"),
    ("Projectors",  "proj_negate",   1156,   "64-bit negation"),
    ("Pipeline",    "observe",        524,   "Gated projection pipeline"),
]


def synthesize(sv_dir: Path) -> None:
    """Run Yosys on each .sv file, produce DOT in _sv_dots/."""
    DOTS_DIR.mkdir(parents=True, exist_ok=True)
    for sv_file in sorted(sv_dir.rglob("*.sv")):
        text = sv_file.read_text()
        m = re.search(r"^\s*module\s+(\w+)", text, re.MULTILINE)
        if not m:
            continue
        mod = m.group(1)
        dot_file = DOTS_DIR / f"{mod}.dot"
        result = subprocess.run(
            ["yosys", "-q", "-p",
             f"read_verilog -sv {sv_file}; synth -top {mod}; "
             f"show -format dot -prefix {DOTS_DIR}/{mod} {mod};"],
            capture_output=True, text=True,
        )
        if result.returncode == 0 and dot_file.exists():
            lines = dot_file.read_text().count("\n")
            print(f"  {mod} ← {sv_file.name} ({lines} lines)")
        else:
            print(f"  FAIL {mod} ← {sv_file.name}")


def generate_qmd() -> None:
    """Regenerate arch_sv_diagram.qmd with inline DOT blocks."""
    lines = []
    def w(s=""):
        lines.append(s)

    # YAML front matter
    w("---")
    w('title: "PoC SystemVerilog Diagram"')
    w('subtitle: "Synthesized from POC RTL modules"')
    w("date: last-modified")
    w("metadata-files:")
    w("  - ../_include/author.yml")
    w("abstract: |")
    w("  Circuit diagrams for every SSCCS verification module.")
    w("  Each module is synthesized independently and rendered")
    w("  as a directed graph of its logic structure.")
    w("---")
    w("")
    w("{{< include ../_include/_title_meta_items.qmd >}}")
    w("")

    # Graphviz import
    w('```{python}')
    w("#| include: false")
    w("#| context: local")
    w("%run ../_include/_graphviz.py")
    w('```')
    w("")

    # Module overview table
    w("## Module Overview")
    w("")
    w("| Group | Module | Lines | Description |")
    w("|---|---|---|---|")
    for grp, mod, lc, desc in TABLE_ROWS:
        w(f"| {grp} | {mod} | {lc} | {desc} |")
    w("")

    # Per-group diagrams
    for group, mods in MODULES:
        w(f"## {group}")
        w("")
        for mod, height in mods:
            dot_file = DOTS_DIR / f"{mod}.dot"
            if not dot_file.exists():
                w(f"*{mod} not available*")
                w("")
                continue
            w(f"### {mod}")
            w("")
            w('```{python}')
            w(f"#| label: fig-{mod}")
            w(f'#| fig-cap: "{mod}"')
            w('dot("""')
            w(dot_file.read_text().rstrip())
            w('""", h="{}")'.format(height))
            w('```')
            w("")

    QMD_FILE.write_text("\n".join(lines) + "\n")
    print(f"Regenerated: {QMD_FILE}")


def generate_placeholder() -> None:
    """Create minimal QMD when yosys + DOTs are absent."""
    lines = [
        "---",
        'title: "PoC SystemVerilog Diagram"',
        'subtitle: "Synthesized from POC RTL modules"',
        "date: last-modified",
        "metadata-files:",
        "  - ../_include/author.yml",
        "abstract: |",
        "  Circuit diagrams for every SSCCS verification module.",
        "---",
        "",
        "{{< include ../_include/_title_meta_items.qmd >}}",
        "",
        "*SV diagrams are not available — Yosys synthesis engine is not installed.*",
        "",
    ]
    QMD_FILE.write_text("\n".join(lines) + "\n")


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <sv_dir>", file=sys.stderr)
        sys.exit(1)

    sv_dir = Path(sys.argv[1]).resolve()

    has_yosys = shutil.which("yosys") is not None
    has_dots = any(DOTS_DIR.glob("*.dot"))

    if has_yosys:
        synthesize(sv_dir)
        generate_qmd()
    elif has_dots:
        generate_qmd()
    else:
        generate_placeholder()
        print("Yosys not found — placeholder QMD generated.")


if __name__ == "__main__":
    main()
