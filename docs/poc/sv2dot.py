#!/usr/bin/env python3
"""SV → DOT → QMD pipeline.

Usage:
  python3 poc/sv2dot.py ../poc/baremetal_riscv/sv

Synthesizes each SV module with Yosys, writes DOT files to _sv_dots/,
and regenerates poc/arch_sv_diagram.qmd with inline DOT code blocks.
Silent skip when yosys is unavailable (placeholder QMD generated).
"""

import subprocess, shutil, sys, re # noqa: E401
from pathlib import Path

POC_DIR = Path(__file__).resolve().parent
DOTS_DIR = POC_DIR / "_sv_dots"
QMD_FILE = POC_DIR / "arch_sv_diagram.qmd"

# ── Module metadata (description + diagram height) ──────────────────────
# Modules are discovered automatically from _sv_dots/*.dot.
# These dicts supply descriptions and rendering preferences.
META = {
    "ck_even":         ("1-LUT even parity check",           "200px"),
    "ck_range_010":    ("Hard-coded [0,10] range check",     "300px"),
    "ck_range":        ("Parameterized [min, max] range check", "300px"),
    "ck_eq":           ("64-bit equality check",             "300px"),
    "ck_gt":           ("64-bit greater-than comparator",    "300px"),
    "compose_union":       ("OR reduction",                      "150px"),
    "compose_intersect":   ("AND reduction",                     "150px"),
    "compose_product_2d":  ("Axis partition (AND of two constraints)", "150px"),
    "proj_identity":   ("64-bit passthrough",                "150px"),
    "proj_sum2d":      ("64-bit adder",                      "400px"),
    "proj_sum3d":      ("128-bit adder chain",               "400px"),
    "proj_parity":     ("LSB extract",                       "150px"),
    "proj_negate":     ("64-bit negation",                   "300px"),
    "observe":         ("Gated projection pipeline",         "400px"),
}

# ── Grouping: prefix → display name ─────────────────────────────────────
GROUPS = [
    ("Constraints", ["ck_"]),
    ("Composition", ["compose_"]),
    ("Projectors",  ["proj_"]),
    ("Pipeline",    ["observe"]),
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


def _discover_modules() -> dict[str, list[str]]:
    """Return {group_name: [mod_name, ...]} from available DOT files."""
    available = {p.stem for p in DOTS_DIR.glob("*.dot")}
    grouped: dict[str, list[str]] = {}
    for group_name, prefixes in GROUPS:
        mods = []
        for mod in sorted(available):
            if any(mod.startswith(p) or mod == p.rstrip("_") for p in prefixes):
                mods.append(mod)
        if mods:
            grouped[group_name] = mods
    return grouped


def generate_qmd() -> None:
    """Regenerate arch_sv_diagram.qmd with inline DOT blocks."""
    grouped = _discover_modules()
    lines = []
    def w(s=""):
        lines.append(s)

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
    for group_name, _prefixes in GROUPS:
        for mod in grouped.get(group_name, []):
            dot_file = DOTS_DIR / f"{mod}.dot"
            lc = dot_file.read_text().count("\n") if dot_file.exists() else 0
            desc = META.get(mod, ("", ""))[0]
            w(f"| {group_name} | {mod} | {lc} | {desc} |")
    w("")

    # Per-group diagrams
    for group_name, _prefixes in GROUPS:
        mods = grouped.get(group_name, [])
        if not mods:
            continue
        w(f"## {group_name}")
        w("")
        for mod in mods:
            dot_file = DOTS_DIR / f"{mod}.dot"
            if not dot_file.exists():
                w(f"*{mod} not available*")
                w("")
                continue
            height = META.get(mod, ("", "300px"))[1]
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
    QMD_FILE.write_text("\n".join([
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
    ]) + "\n")


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
