#!/usr/bin/env python3
import os
import sys
import subprocess
import re
import yaml
from pathlib import Path

def get_front_matter(qmd_path):
    with open(qmd_path, encoding='utf-8') as f:
        content = f.read()
    m = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    if not m:
        return {}
    return yaml.safe_load(m.group(1)) or {}

# Return the path inside \input{...} if it ends with '_metadata.tex', else None.
def find_input_metadata_line(qmd_path):
    with open(qmd_path, encoding='utf-8') as f:
        for line in f:
            m = re.search(r'\\input\{([^}]*_metadata\.tex)\}', line)
            if m:
                return m.group(1)
    return None

def main():
    input_files = os.environ.get("QUARTO_PROJECT_INPUT_FILES", "").splitlines()
    qmd_files = [f for f in input_files if f.endswith('.qmd')]
    if not qmd_files:
        print("No .qmd files to process")
        return

    project_root = Path(os.environ.get("QUARTO_PROJECT_ROOT", ".")).resolve()
    generator = project_root / "_include" / "_generate_metadata_tex.py"

    for qmd in qmd_files:
        qmd_path = Path(qmd).resolve()

        # 1. Find the \input{..._metadata.tex} pattern
        target_rel = find_input_metadata_line(qmd_path)
        if not target_rel:
            print(f"Skipping {qmd_path.name}: no \\input{{..._metadata.tex}} line found.")
            continue

        # 2. Output file path (relative to QMD's directory)
        out_file = (qmd_path.parent / target_rel).resolve()
        out_file.parent.mkdir(parents=True, exist_ok=True)

        # 3. Read front matter
        front = get_front_matter(qmd_path)
        vpre = front.get('version-prefix', None)
        vmark = front.get('version-mark', False)

        # 4. Build command – only add --version_prefix if vpre is not None
        cmd = [sys.executable, str(generator), "--input", str(qmd_path), "--output", str(out_file)]
        if vpre is not None:
            cmd += ["--version_prefix", str(vpre)]
        if vmark:
            cmd.append("--version_mark")

        print(f"Generating {out_file} from {qmd_path.name}")
        subprocess.run(cmd, check=True)

if __name__ == "__main__":
    main()
