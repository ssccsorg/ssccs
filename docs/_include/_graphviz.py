#!/usr/bin/env python3
"""
Graphviz DOT Utilities for IPython/Quarto
=========================================
Provides robust rendering of DOT diagrams with encoding safety and layout control.

Functions:
    - dot(code): Renders to PDF format. Best for high-quality static exports.
    - dot_svg(code, h): Renders to SVG with CSS height control. Ideal for web/Quarto layouts.

Features:
    - Auto-normalizes Unicode (NFC) to prevent rendering failures.
    - Suppresses engine warnings (stderr) for clean build logs.
    - Flexible input: Supports both raw logic and full 'digraph' syntax.

Usage Example:
    ```{python}
    # For standard output
    dot("A -> B")

    # For responsive web layouts in .qmd
    dot_svg("A -> B", h="150px")
    ```
"""

import contextlib
import io

import graphviz
from IPython.display import SVG, display


def _extract_inner_dot(code):
    """Extract content inside the first '{' and last '}' if the code starts with 'digraph'."""
    code = code.strip()
    if code.startswith("digraph"):
        start = code.find("{")
        end = code.rfind("}")
        if start != -1 and end != -1 and end > start:
            return code[start + 1 : end].strip()
    return code


def _clean_dot_text(text):
    if not text:
        return ""

    import unicodedata

    text = unicodedata.normalize("NFC", text)

    clean_bytes = text.encode("utf-8", errors="ignore")
    text = clean_bytes.decode("utf-8")
    return text


def dot(code):
    src = graphviz.Source(_clean_dot_text(code))
    src.format = "pdf"  # or 'svg' depending on your needs
    with contextlib.redirect_stderr(io.StringIO()):
        return display(src)


def dot_svg(code, h="150px"):
    src = graphviz.Source(code)
    svg_str = src.pipe(format="svg").decode("utf-8")
    styled_svg = svg_str.replace("<svg ", f'<svg style="height:{h}; width:auto;" ')
    return SVG(styled_svg)
