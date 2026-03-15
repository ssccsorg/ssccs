#!/usr/bin/env python3
"""
Standalone utility to determine the main QMD file path for a Quarto project.

Usage:
    python get_qmd_path.py [--input PATH]

If --input is provided, it checks that the file exists.
Otherwise, it checks the environment variable QUARTO_PROJECT_INPUT_FILE.
If that is not set or invalid, it uses the first .qmd file in the current directory.
If no valid file is found, it prints an error message to stderr and exits with code 1.

The resolved path is printed to stdout (useful for shell scripts).
"""

import os
import sys
import argparse

def resolve_qmd_path(input_arg=None):
    """
    Determine the main QMD file path following the same logic as the original script.
    Returns the path as a string, or raises FileNotFoundError if none found.
    """
    qmd_path = input_arg
    if qmd_path:
        if not os.path.isfile(qmd_path):
            raise FileNotFoundError(f"Input file '{qmd_path}' not found.")
        return qmd_path

    # Try environment variable
    qmd_path = os.environ.get('QUARTO_PROJECT_INPUT_FILE')
    if qmd_path and os.path.exists(qmd_path):
        return qmd_path

    # Fallback: first .qmd file in current directory
    qmd_files = [f for f in os.listdir('.') if f.endswith('.qmd')]
    if qmd_files:
        return qmd_files[0]

    raise FileNotFoundError(
        "Cannot determine QMD file. Please specify --input or ensure a "
        ".qmd file exists in the current directory."
    )

def main():
    parser = argparse.ArgumentParser(
        description='Resolve the main QMD file path for a Quarto project.'
    )
    parser.add_argument('--input', '-i', help='Explicit path to the QMD file')
    args = parser.parse_args()

    try:
        path = resolve_qmd_path(args.input)
        # Print only the path; no extra text, so it can be captured cleanly
        print(path)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()