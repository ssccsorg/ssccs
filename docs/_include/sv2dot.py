#!/usr/bin/env python3
"""SV to DOT — lightweight SystemVerilog module diagram generator.
Usage:
  python3 sv2dot.py path/to/sv/dir/    # all modules, hierarchical
  python3 sv2dot.py path/to/module.sv  # single module
  python3 sv2dot.py path/ --flat       # flat (no subgraph)
"""

import sys, re
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

    # Match: word word (   — only if word is not a keyword and followed by (
    for inst in re.finditer(r'(\w+)\s+(\w+)\s*\(', text):
        name = inst.group(1)
        if name in SKIP_INST:
            continue
        if name[0].isupper() or name[0].islower():
            # Check that this looks like an instantiation (has port connections)
            # by peeking ahead for .identifier( pattern
            rest = text[inst.end():inst.end()+80]
            if re.search(r'\.\w+\s*\(', rest):
                result["instantiations"].append((name, inst.group(2)))
    return result


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
        color = "#d4f1f9"
        lines.append(f'    {mod["module"]} [label="{label}", fillcolor="{color}"];')

    for mod in modules:
        if not mod["module"]:
            continue
        for inst_module, inst_name in mod["instantiations"]:
            # Clean instance name (remove array indices like [0])
            inst_name_clean = re.sub(r'\[\d+\]', '', inst_name)
            if inst_module in module_names:
                lines.append(f'    {mod["module"]} -> {inst_module} [label="{inst_name_clean}"];')
            else:
                e = f'ext_{inst_module.lower()}'
                if e not in module_names:
                    module_names.add(e)

    lines.append("}")
    return "\n".join(lines)


def main():
    path = Path(sys.argv[1])
    if path.is_dir():
        modules = []
        for f in sorted(path.rglob("*.sv")):
            p = parse_sv_file(f)
            if p["module"]:
                modules.append(p)
        print(generate_dot(modules))
    elif path.is_file():
        p = parse_sv_file(path)
        if p["module"]:
            print(generate_dot([p]))
        else:
            print(f"No module found", file=sys.stderr)

if __name__ == "__main__":
    main()
