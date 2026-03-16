#!/usr/bin/env python3
"""
Generate LaTeX metadata file for Quarto(.qmd) input.
Usage: python generate_metadata.py [--input index.qmd] [--output ./_include/_metadata.tex] [--version_prefix 0.1]
If --input is omitted, uses QUARTO_PROJECT_INPUT_FILE or the first .qmd file in current directory.
"""

import os
import sys
import argparse
import hashlib
import yaml
from datetime import datetime
import textwrap

def extract_front_matter(qmd_path):
    """Extract YAML front matter from a QMD file."""
    with open(qmd_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    in_front = False
    front_lines = []
    for line in lines:
        if line.strip() == '---':
            if not in_front:
                in_front = True
                continue
            else:
                break
        if in_front:
            front_lines.append(line)
    if not front_lines:
        raise ValueError(f"No YAML front matter found in {qmd_path}")
    return yaml.safe_load(''.join(front_lines))

def main():
    parser = argparse.ArgumentParser(description='Generate LaTeX metadata for SSCCS')
    parser.add_argument('--input', '-i', required=False,
                        help='Path to the main QMD file (e.g., index.qmd). If not provided, uses QUARTO_PROJECT_INPUT_FILE or first .qmd in directory.')
    parser.add_argument('--output', '-o', default='./_include/_metadata.tex',
                        help='Output LaTeX metadata file path')
    parser.add_argument('--version_prefix', '-p', default='0.1',
                        help='Version prefix (e.g., 0.1)')
    parser.add_argument('--version_mark', action='store_true',
                        help='Include background version watermark in PDF')
    args = parser.parse_args()

    # ----- Determine input file path -----
    qmd_path = args.input
    if not qmd_path:
        # Try environment variable
        qmd_path = os.environ.get('QUARTO_PROJECT_INPUT_FILE')
        if qmd_path and not os.path.exists(qmd_path):
            qmd_path = None  # invalid path, ignore
        if not qmd_path:
            # Fallback: first .qmd file in current directory
            qmd_files = [f for f in os.listdir('.') if f.endswith('.qmd')]
            qmd_path = qmd_files[0] if qmd_files else None
        if not qmd_path:
            sys.exit("Error: Cannot determine QMD file for hashing. Please specify --input or ensure a .qmd file exists in the current directory.")
    elif not os.path.isfile(qmd_path):
        sys.exit(f"Error: Input file '{qmd_path}' not found.")

    # ----- Compute version -----
    with open(qmd_path, 'rb') as f:
        file_hash = hashlib.sha256(f.read()).hexdigest()
    date_short = datetime.now().strftime("%y%m%d")
    version_str = f"{args.version_prefix}-{date_short}-{file_hash[:6]}"

    # ----- Extract YAML front matter (author/affiliations are optional) -----
    front = extract_front_matter(qmd_path)

    # Default empty values for all author and affiliation fields
    author_name = ''
    author_email = ''
    author_role = ''
    orcid = ''
    affiliation_name = ''
    affiliation_url = ''
    affiliation_domain = ''

    # Check if author information exists and is valid
    if 'author' in front and isinstance(front['author'], list) and len(front['author']) > 0:
        author = front['author'][0]
        author_name = author.get('name', '')
        author_email = author.get('email', '')
        author_role = author.get('role', '')
        orcid = author.get('orcid', '')

        # Check for affiliations within the author
        if 'affiliations' in author and isinstance(author['affiliations'], list) and len(author['affiliations']) > 0:
            aff = author['affiliations'][0]
            affiliation_name = aff.get('name', '')
            affiliation_url = aff.get('url', '')
            affiliation_domain = aff.get('domain', '')

    # ----- Ensure output directory -----
    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    # ----- Write LaTeX macros -----
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(f"\\newcommand{{\\version}}{{{version_str}}}\n")
        f.write(f"\\newcommand{{\\timestamp}}{{{datetime.now()}}}\n")
        f.write(f"\\newcommand{{\\affiliationname}}{{{affiliation_name}}}\n")
        f.write(f"\\newcommand{{\\affiliationurl}}{{{affiliation_url}}}\n")
        f.write(f"\\newcommand{{\\affiliationdomain}}{{{affiliation_domain}}}\n")
        f.write(f"\\newcommand{{\\authorname}}{{{author_name}}}\n")
        f.write(f"\\newcommand{{\\authoremail}}{{{author_email}}}\n")
        f.write(f"\\newcommand{{\\authorrole}}{{{author_role}}}\n")
        f.write(f"\\newcommand{{\\orcid}}{{{orcid}}}\n")
        f.write(f"\\newcommand{{\\filehash}}{{{file_hash}}}\n")
        if args.version_mark:
            f.write(textwrap.dedent("""
                \\usepackage{xcolor}
                \\usepackage{graphicx}
                \\usepackage{background}
                \\backgroundsetup{
                    contents={\\rotatebox{90}{\\ttfamily\\color{lightgray}\\version}},
                        angle=0,
                        scale=1,
                        opacity=1,
                        position=current page.east,
                        vshift=0pt,
                        hshift=-20pt
                }
            \n"""))

    print(f"Metadata written to {args.output}")

if __name__ == '__main__':
    main()