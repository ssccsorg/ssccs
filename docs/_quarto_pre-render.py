#!/usr/bin/env python3
import os, sys, subprocess, re, yaml
from pathlib import Path

def get_front_matter(qmd_path):
    with open(qmd_path, encoding='utf-8') as f:
        content = f.read()
    m = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    if not m:
        return {}
    return yaml.safe_load(m.group(1)) or {}

def main():
    input_files = os.environ.get("QUARTO_PROJECT_INPUT_FILES", "").splitlines()
    qmd_files = [f for f in input_files if f.endswith('.qmd')]
    if not qmd_files:
        print("No .qmd files to process")
        return

    # 프로젝트 루트에서 _generate_metadata_tex.py 찾기
    project_root = Path(os.environ.get("QUARTO_PROJECT_ROOT", ".")).resolve()
    generator = project_root / "_include" / "_generate_metadata_tex.py"

    for qmd in qmd_files:
        qmd_path = Path(qmd).resolve()
        front = get_front_matter(qmd_path)
        
        vpre = front.get('version-prefix', None)
        vmark = front.get('version-mark', False)
        
        # QMD 파일이 있는 디렉토리 아래의 _files 폴더 사용
        doc_dir = qmd_path.parent
        out_dir = doc_dir / "_files"
        out_dir.mkdir(exist_ok=True)
        out_file = out_dir / f"{qmd_path.stem}_metadata.tex"
        
        cmd = [sys.executable, str(generator), "--input", str(qmd_path), "--output", str(out_file)]
        if vpre is not None:
            cmd += ["--version_prefix", str(vpre)]
        if vmark:
            cmd.append("--version_mark")
        
        print(f"Generating {out_file} from {qmd_path.name}")
        subprocess.run(cmd, check=True)

if __name__ == "__main__":
    main()