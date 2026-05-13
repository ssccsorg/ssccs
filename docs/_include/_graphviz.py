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


_FONT_DOT = "Helvetica"  # single font for Graphviz's own rendering (PDF)
_WEB_FONT_STACK = (
    "-apple-system, BlinkMacSystemFont, "
    "'Helvetica Neue', Helvetica, Arial, "
    "'DejaVu Sans', sans-serif"
)


def _normalise_dot_font(code: str) -> str:
    """Ensure every DOT graph uses a cross-platform font stack.

    Replaces ``fontname="Arial"`` (macOS-only) with a fallback chain
    that degrades gracefully on Linux and other systems.  If no
    ``fontname`` is present at all, injects a global graph-level
    default so the rendered output is consistent everywhere.
    """
    import re

    has_font = re.search(r'\bfontname\s*=\s*"', code)
    if not has_font:
        # Inject global default right after the opening brace
        injection = '\n    fontname="' + _FONT_DOT + '"'
        code = re.sub(
            r"((?:digraph|graph)\s+\w+\s*\{)",
            r"\1" + injection,
            code,
            count=1,
        )
        return code

    # Normalise existing fontname values to the cross-platform stack
    new_val = 'fontname="' + _FONT_DOT + '"'
    code = re.sub(
        r'fontname\s*=\s*"[^"]*"',
        new_val,
        code,
    )
    return code


def dot(code):
    src = graphviz.Source(_clean_dot_text(_normalise_dot_font(code)))
    src.format = "pdf"
    with contextlib.redirect_stderr(io.StringIO()):
        return display(src)


def dot_svg(code, h="150px"):
    src = graphviz.Source(_normalise_dot_font(code))
    svg_str = src.pipe(format="svg").decode("utf-8")
    import re
    # Strip Graphviz's hardcoded font-family from every text element
    # so the injected CSS below takes full control across all platforms.
    svg_str = re.sub(r'\bfont-family="[^"]*"', '', svg_str)
    # Inject CSS with browser-native font stack
    style_block = f"<style>text {{ font-family: {_WEB_FONT_STACK}; }}</style>"
    svg_str = re.sub(r'<svg([^>]*)>', rf'<svg\1 style="height:{h}; width:auto;">{style_block}', svg_str)
    return SVG(svg_str)
