#!/usr/bin/env python3
"""
Graphviz DOT Utilities for IPython/Quarto
=========================================
Provides robust rendering of DOT diagrams with encoding safety
and cross-platform font handling.

Functions:
    - dot(code, h="150px"): Renders DOT to SVG with system-native
      font stack.  Accepts optional CSS height via *h* (default 150px).

Features:
    - Auto-normalises Unicode (NFC) to prevent rendering failures.
    - Strips Graphviz's hardcoded font-family and injects CSS for
      consistent system-native typography across macOS and Linux.
    - Suppresses engine warnings (stderr) for clean build logs.
    - Flexible input: Supports both raw logic and full 'digraph' syntax.

Usage Example:
    ```{python}
    dot("A -> B")
    dot("digraph G { A -> B }", h="200px")
    ```
"""

import contextlib
import io
import re

import graphviz
from IPython.display import SVG


def _clean_dot_text(text):
    if not text:
        return ""

    import unicodedata

    text = unicodedata.normalize("NFC", text)

    clean_bytes = text.encode("utf-8", errors="ignore")
    text = clean_bytes.decode("utf-8")
    return text


_FONT_DOT = "sans-serif"  # Graphviz layout font (available everywhere)
_BODY_FONT = "sans-serif"  # matches Quarto body font family


def _normalise_dot_font(code: str) -> str:
    """Ensure every DOT graph uses a cross-platform font.

    Replaces fontname values with ``_FONT_DOT``, or injects a graph-level
    default if none exists.
    """
    has_font = re.search(r'\bfontname\s*=\s*"', code)
    if not has_font:
        injection = '\n    fontname="' + _FONT_DOT + '"'
        code = re.sub(
            r"((?:digraph|graph)\s+\w+\s*\{)",
            r"\1" + injection,
            code,
            count=1,
        )
        return code

    new_val = 'fontname="' + _FONT_DOT + '"'
    code = re.sub(r'fontname\s*=\s*"[^"]*"', new_val, code)
    return code


def _render_svg(code: str, h: str = "") -> str:
    """Render DOT to SVG string, strip Graphviz font-family, inject CSS.

    If *h* is non-empty, injects ``style="height:{h}; width:auto;"``
    into the ``<svg>`` tag.
    """
    src = graphviz.Source(_normalise_dot_font(code))
    svg_str = src.pipe(format="svg").decode("utf-8")
    # Strip Graphviz's hardcoded font-family from every text element
    svg_str = re.sub(r'\bfont-family="[^"]*"', "", svg_str)
    # Inject CSS (right after opening <svg ...> tag)
    style_tag = "<style>text { font-family: " + _BODY_FONT + "; }</style>"
    if h:
        svg_str = re.sub(
            r"<svg ", '<svg style="height:' + h + '; width:auto;" ', svg_str
        )
    svg_str = svg_str.replace("<g ", style_tag + "<g ", 1)
    return svg_str


def dot(code, h="150px"):
    """Render a DOT diagram to SVG with a system-native font stack."""
    with contextlib.redirect_stderr(io.StringIO()):
        return SVG(_render_svg(_clean_dot_text(code), h))
