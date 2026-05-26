#!/usr/bin/env python3
"""SV → DOT → QMD pipeline.

Usage:
  python3 poc/sv2dot.py ../poc/baremetal_riscv/sv

Synthesizes each SV module with Yosys, writes DOT files to _sv_dots/,
and regenerates poc/arch_sv_diagram.qmd with inline DOT code blocks.
All metadata (group, description) is extracted from SV file structure
and header comments. No hardcoded module data.
"""

import subprocess, shutil, sys, re  # noqa: E401
from pathlib import Path
from collections import OrderedDict

POC_DIR = Path(__file__).resolve().parent
DOTS_DIR = POC_DIR / "_sv_dots"
QMD_FILE = POC_DIR / "arch_sv_diagram.qmd"


def synthesize(sv_dir: Path) -> list[tuple[str, str, str, str]]:
    """Run Yosys on each .sv file, produce DOT in _sv_dots/.

    Returns [(module_name, group, description, dot_path), ...] for
    successfully synthesized modules.  Group is derived from the SV
    file's parent directory; description from the first // comment.
    """
    DOTS_DIR.mkdir(parents=True, exist_ok=True)
    results = []

    for sv_file in sorted(sv_dir.rglob("*.sv")):
        text = sv_file.read_text()
        m = re.search(r"^\s*module\s+(\w+)", text, re.MULTILINE)
        if not m:
            continue
        mod = m.group(1)

        # Group from directory name (relative to sv_dir)
        rel = sv_file.parent.relative_to(sv_dir)
        group = str(rel).capitalize() if str(rel) != "." else "Top"

        # Description from first // comment line
        desc = ""
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("//") and not stripped.startswith("///"):
                desc = stripped.lstrip("/ ").strip()
                break

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
            results.append((mod, group, desc, str(dot_file)))
        else:
            print(f"  FAIL {mod} ← {sv_file.name}")

    return results


def generate_qmd(modules: list[tuple[str, str, str, str]]) -> None:
    """Regenerate arch_sv_diagram.qmd with inline DOT blocks."""
    grouped: OrderedDict[str, list] = OrderedDict()
    for mod, group, desc, dot_path in modules:
        grouped.setdefault(group, []).append((mod, desc, dot_path))

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

    w("## Module Overview")
    w("")
    w("| Group | Module | Lines | Description |")
    w("|---|---|---|---|")
    for group, mods in grouped.items():
        for mod, desc, dot_path in mods:
            lc = Path(dot_path).read_text().count("\n")
            w(f"| {group} | {mod} | {lc} | {desc} |")
    w("")

    for group, mods in grouped.items():
        w(f"## {group}")
        w("")
        for mod, desc, dot_path in mods:
            dot_text = Path(dot_path).read_text().rstrip()
            n = dot_text.count("\n")
            h = "400px" if n > 500 else "300px" if n > 100 else "150px"
            w(f"### {mod}")
            w("")
            w('```{python}')
            w(f"#| label: fig-{mod}")
            w(f'#| fig-cap: "{mod}"')
            w('dot("""')
            w(dot_text)
            w('""", h="{}")'.format(h))
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

    if shutil.which("yosys"):
        modules = synthesize(sv_dir)
        if modules:
            generate_qmd(modules)
        else:
            generate_placeholder()
    elif any(DOTS_DIR.glob("*.dot")):
        mods_from_dots = [
            (p.stem, "Module", "", str(p))
            for p in sorted(DOTS_DIR.glob("*.dot"))
        ]
        generate_qmd(mods_from_dots)
    else:
        generate_placeholder()
        print("Yosys not found — placeholder QMD generated.")


if __name__ == "__main__":
    main()
