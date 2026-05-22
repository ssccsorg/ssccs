"""
Graphviz DOT Utilities for Quarto
Provides robust rendering of DOT diagrams with encoding safety
and cross-platform font handling.
"""

import contextlib
import io
import re

import graphviz
from IPython.display import SVG


def dot(code, h="150px"):
    """Render a DOT diagram to SVG with a system-native font stack."""
    import unicodedata
    code = unicodedata.normalize("NFC", code) if code else ""
    has_font = re.search(r'\bfontname\s*=\s*"', code)
    if not has_font:
        injection = '\n    fontname="sans-serif"'
        code = re.sub(r"((?:digraph|graph)\s+\w+\s*\{)", r"\1" + injection, code, count=1)
    src = graphviz.Source(code)
    svg_str = src.pipe(format="svg").decode("utf-8")
    svg_str = re.sub(r'\bfont-family="[^"]*"', "", svg_str)
    style_tag = "<style>text { font-family: sans-serif; }</style>"
    if h:
        svg_str = re.sub(r"<svg ", '<svg style="height:' + h + '; width:auto;" ', svg_str)
    svg_str = svg_str.replace("<g ", style_tag + "<g ", 1)
    with contextlib.redirect_stderr(io.StringIO()):
        return SVG(svg_str)
