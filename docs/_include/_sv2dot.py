#!/usr/bin/env python3
"""SV to DOT — lightweight SystemVerilog module diagram generator.
Usage:
  python3 _sv2dot.py path/to/sv/dir/          # all modules → stdout
  python3 _sv2dot.py path/to/sv/dir/ --all    # per-category + all to _include/sv_dots/
  python3 _sv2dot.py path/to/module.sv        # single module → stdout
"""

import sys, re, os
from pathlib import Path

SKIP_INST = {
    "module","endmodule","input","output","inout","logic","wire","reg",
    "assign","always","always_comb","always_ff","initial","genvar",
    "generate","endgenerate","ifdef","ifndef","endif","elsif","else",
    "localparam","parameter","typedef","enum","struct","case","endcase",
    "begin","end","if","else","for","while","repeat","forever",
    "property","endproperty","assert","assume","cover","expect",
    "disable","iff","edge","posedge","negedge","or",",","//","/*",
}

CATEGORY_DIRS = {
    "constraints": ["ck_"],
    "composition": ["compose_"],
    "projectors":  ["proj_"],
    "pipeline":    ["observe"],
    "xif":         ["ssccs_xif", "xif_", "scenario_"],
}

def parse_sv_file(path: Path) -> dict:
    text = path.read_text()
    result = {"file": path.name, "module": None, "ports": [], "instantiations": []}
    m = re.search(r'module\s+(\w+)\s*[#(]', text)
    if not m:
        return result
    result["module"] = m.group(1)

    for port in re.finditer(
        r'(input|output|inout)\s+(logic|wire|reg|bit)?\s*(?:\[(\d+):(\d+)\])?\s*(\w+)', text
    ):
        width = None
        if port.group(3) and port.group(4):
            w = int(port.group(3)) - int(port.group(4)) + 1
            width = w if w > 1 else None
        result["ports"].append((port.group(1), port.group(5), width))

    for inst in re.finditer(r'(\w+)\s+(\w+)\s*\(', text):
        name = inst.group(1)
        if name in SKIP_INST:
            continue
        rest = text[inst.end():inst.end()+80]
        if re.search(r'\.\w+\s*\(', rest):
            result["instantiations"].append((name, inst.group(2)))
    return result


def categorize(mod_name: str) -> str:
    for cat, prefixes in CATEGORY_DIRS.items():
        for p in prefixes:
            if mod_name.startswith(p):
                return cat
    return "other"


def generate_dot(modules: list) -> str:
    lines = []
    lines.append("digraph SVModules {")
    lines.append("    rankdir=TB; splines=ortho; nodesep=0.2; ranksep=0.3;")
    lines.append('    node [shape=box, style="rounded,filled", fontsize=8, width=1.3];')
    lines.append('    edge [fontsize=7];')
    lines.append("")
    module_names = {m["module"] for m in modules if m["module"]}
    for mod in modules:
        if not mod["module"]:
            continue
        ports_str = "\\n".join(
            f"{'→' if d[0]=='o' else '←'} {n}{f'[{w}]' if w else ''}"
            for d,n,w in mod["ports"]
        )
        label = f"{mod['module']}\\n{ports_str}" if ports_str else mod["module"]
        lines.append(f'    {mod["module"]} [label="{label}", fillcolor="#d4f1f9"];')
    for mod in modules:
        if not mod["module"]:
            continue
        for inst_module, inst_name in mod["instantiations"]:
            inst_name_clean = re.sub(r'\[\d+\]', '', inst_name)
            if inst_module in module_names:
                lines.append(f'    {mod["module"]} -> {inst_module} [label="{inst_name_clean}"];')
    lines.append("}")
    return "\n".join(lines)


def _dots_dir() -> str:
    """Return path to sv_dots directory (creates if missing)."""
    d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sv_dots")
    os.makedirs(d, exist_ok=True)
    return d


def list_sv_categories() -> list[str]:
    """Return available DOT category names (for QMD use)."""
    import glob
    d = _dots_dir()
    return sorted(os.path.splitext(os.path.basename(f))[0] for f in glob.glob(os.path.join(d, "*.dot")))


def load_sv_dot(category: str = "all") -> str:
    """Load DOT source by category (for QMD use via %run)."""
    dot_path = os.path.join(_dots_dir(), f"{category}.dot")
    if os.path.exists(dot_path):
        with open(dot_path) as f:
            return f.read()
    return ""


def main():
    path = Path(sys.argv[1])
    do_all = "--all" in sys.argv

    if do_all:
        out_dir = Path(__file__).resolve().parent / "sv_dots"
        out_dir.mkdir(parents=True, exist_ok=True)

        # Per-category
        by_cat: dict[str, list] = {c: [] for c in CATEGORY_DIRS}
        by_cat["all"] = []

        for f in sorted(path.rglob("*.sv")):
            p = parse_sv_file(f)
            if not p["module"]:
                continue
            cat = categorize(p["module"])
            if cat in by_cat:
                by_cat[cat].append(p)
            by_cat["all"].append(p)

        for cat, mods in by_cat.items():
            if not mods:
                continue
            dot_file = out_dir / f"{cat}.dot"
            dot_file.write_text(generate_dot(mods))
            print(f"  → {dot_file}")

    elif path.is_dir():
        modules = [parse_sv_file(f) for f in sorted(path.rglob("*.sv")) if parse_sv_file(f)["module"]]
        print(generate_dot(modules))
    elif path.is_file():
        p = parse_sv_file(path)
        if p["module"]:
            print(generate_dot([p]))

if __name__ == "__main__":
    # When run via `python3 _sv2dot.py ...`, execute CLI.
    # When %run from QMD, main() is guarded — load_sv_dot is the entry point.
    if len(sys.argv) > 1:
        main()
    else:
        # Called via `%run _sv2dot.py` from QMD — no-op, just import functions.
        pass
