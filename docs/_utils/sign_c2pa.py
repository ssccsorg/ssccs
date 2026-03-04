#!/usr/bin/env python3
"""
Create a standalone C2PA manifest for a PDF file using c2patool's built-in test certificate.

This script calculates the SHA-256 hash of the given PDF, injects it as a custom
assertion (org.ssccs.pdfhash) into a C2PA manifest JSON template, then uses
c2patool to generate a sidecar .c2pa manifest file.

It also saves a metadata SVG (containing the PDF hash and the full original manifest JSON)
in the same folder as the output .c2pa file, with the filename pattern: <output_stem>.c2pa_identifier.svg

Usage:
    python sign_c2pa.py --pdf <file.pdf> --manifest <template.json> --output <out.c2pa>

Dependencies:
    - c2patool must be installed and accessible in PATH (or provided via --c2patool)
    - Python 3.6+

License: Apache 2.0
Copyright 2026 SSCCS Foundation
"""

import json
import hashlib
import argparse
import subprocess
import tempfile
import shutil
import sys
from pathlib import Path

def calculate_sha256(file_path):
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)
    return sha256.hexdigest()

def create_metadata_file(path, pdf_hash, manifest_json_path):
    """
    Create an SVG file that contains:
    - a custom attribute pdf:hash with the PDF hash,
    - the full original manifest JSON embedded inside <metadata> as CDATA.
    """
    with open(manifest_json_path, 'r', encoding='utf-8') as f:
        manifest_str = f.read()

    svg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:pdf="https://ssccs.org/ns/pdfhash"
     pdf:hash="sha256:{pdf_hash}">
  <metadata>
    <![CDATA[
{manifest_str}
    ]]>
  </metadata>
</svg>'''
    with open(path, 'w', encoding='utf-8') as f:
        f.write(svg_content)

def main():
    parser = argparse.ArgumentParser(description="Create standalone C2PA manifest for a PDF")
    parser.add_argument("--pdf", required=True, help="Path to PDF file (hash target)")
    parser.add_argument("--manifest", required=True, help="C2PA manifest JSON template")
    parser.add_argument("--output", required=True, help="Output .c2pa file path")
    parser.add_argument("--c2patool", help="Path to c2patool executable (if not in PATH)")
    args = parser.parse_args()

    c2patool = args.c2patool or shutil.which("c2patool")
    if not c2patool:
        print("Error: c2patool not found", file=sys.stderr)
        return 1

    pdf_hash = calculate_sha256(args.pdf)
    print(f"PDF SHA-256: {pdf_hash}")

    with open(args.manifest, 'r', encoding='utf-8') as f:
        manifest_data = json.load(f)

    # Remove signing fields to force built‑in test certificate
    manifest_data.pop("private_key", None)
    manifest_data.pop("sign_cert", None)
    manifest_data.pop("alg", None)

    pdf_hash_assertion = {
        "label": "org.ssccs.pdfhash",
        "data": {
            "hash": f"sha256:{pdf_hash}"
        }
    }

    if "assertions" not in manifest_data:
        manifest_data["assertions"] = []
    found = False
    for i, a in enumerate(manifest_data["assertions"]):
        if a.get("label") == "org.ssccs.pdfhash":
            manifest_data["assertions"][i] = pdf_hash_assertion
            found = True
            break
    if not found:
        manifest_data["assertions"].append(pdf_hash_assertion)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_dir = Path(tmpdir)

        # Create metadata SVG (contains both the PDF hash attribute and the full original JSON)
        metadata_file = tmp_dir / "metadata.svg"
        create_metadata_file(metadata_file, pdf_hash, args.manifest)

        # Save the modified manifest (with pdfhash) as a separate JSON file for c2patool
        manifest_json = tmp_dir / "manifest.json"
        with open(manifest_json, 'w', encoding='utf-8') as f:
            json.dump(manifest_data, f, indent=2)

        output_base = tmp_dir / "output.svg"
        sidecar_c2pa = tmp_dir / "output.c2pa"

        cmd = [
            c2patool, str(metadata_file),
            "-m", str(manifest_json),
            "-s",
            "-o", str(output_base),
            "-f"
        ]
        print("Running:", " ".join(cmd))
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print("c2patool error:", result.stderr, file=sys.stderr)
            return 1

        if sidecar_c2pa.exists():
            shutil.copy2(sidecar_c2pa, args.output)
            print(f"> C2PA manifest created: {args.output}")
        else:
            print(f"Error: {sidecar_c2pa} not generated", file=sys.stderr)
            return 1

        # Copy the metadata SVG to the output folder with a descriptive name
        output_path = Path(args.output)
        identifier_svg_path = output_path.parent / f"{output_path.stem}.c2pa_identifier.svg"
        shutil.copy2(metadata_file, identifier_svg_path)
        print(f"> Identifier SVG saved: {identifier_svg_path}")

    verify_cmd = [c2patool, args.output]
    verify_result = subprocess.run(verify_cmd, capture_output=True, text=True)
    if verify_result.returncode == 0:
        print("> Manifest verification succeeded")
    else:
        print("! Manifest verification failed:", verify_result.stderr, file=sys.stderr)

if __name__ == "__main__":
    sys.exit(main())