#!/usr/bin/env python3
"""
_title_meta_builder.py – Quarto pre-render helper for title-meta items.

Usage in a .qmd Python cell:
    %run ../_include/_title_meta_builder.py <stem>

Where ``<stem>`` is the document stem (filename without .qmd extension),
e.g. ``riscv_space`` for ``research/riscv_space.qmd``.

This script:
1. Takes the document stem from sys.argv
2. Reads its `title-meta-items` from YAML front matter
3. Auto-generates "Other Formats" cross-links ONLY for declared formats
4. Sets the `title_meta_items` global dict consumed by _title_meta_items_if_*.qmd
"""

import re
import sys
from pathlib import Path

import yaml


def _find_qmd_file(stem: str) -> Path | None:
    """Find the .qmd file with the given stem in the current directory."""
    cwd = Path.cwd()
    qmd_path = cwd / f"{stem}.qmd"
    if qmd_path.exists():
        return qmd_path
    # Try parent directory
    qmd_path = cwd.parent / f"{stem}.qmd"
    if qmd_path.exists():
        return qmd_path
    return None


def _find_project_root(start: Path) -> Path:
    """Walk up from *start* until we find _quarto.yml."""
    for parent in [start] + list(start.parents):
        if (parent / "_quarto.yml").exists():
            return parent
    return start.parent


def _get_front_matter(qmd_path: Path) -> dict:
    with open(qmd_path, encoding="utf-8") as f:
        content = f.read()
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not m:
        return {}
    return yaml.safe_load(m.group(1)) or {}


FORMAT_KEYS = ("html", "pdf", "beamer")


def _extract_format_keys(fmt_block: dict) -> set[str]:
    """Return {html, pdf, ...} for any FORMAT_KEYS present in *fmt_block*."""
    return {k for k in FORMAT_KEYS if k in fmt_block}


def _auto_other_formats(doc_stem: str, current_fmt: str, declared_formats: set[str]) -> list[dict]:
    """Build built-in 'Other Formats' entry."""
    if current_fmt == "html" and "pdf" in declared_formats:
        return [
            {
                "title": "Other Formats",
                "link": f"/{doc_stem}.pdf",
                "content": "PDF",
                "content_class": "bi bi-file-pdf",
            }
        ]
    if current_fmt == "pdf":
        return [
            {
                "title": "Other Formats",
                "link": f"https://docs.ssccs.org/{doc_stem}.html",
                "content": "HTML",
            }
        ]
    return []


def _get_declared_formats(front: dict, project_root: Path) -> set[str]:
    """Return formats declared by the document, falling back to project-level config."""
    fmt_block = front.get("format")
    if fmt_block and isinstance(fmt_block, dict):
        declared = _extract_format_keys(fmt_block)
        if declared:
            return declared

    for config_name in ("_quarto-website.yml", "_quarto.yml"):
        config_path = project_root / config_name
        if config_path.exists():
            try:
                with open(config_path) as f:
                    proj = yaml.safe_load(f) or {}
                proj_fmt = proj.get("format")
                if proj_fmt and isinstance(proj_fmt, dict):
                    declared = _extract_format_keys(proj_fmt)
                    if declared:
                        return declared
            except Exception:
                pass

    return {"html"}


def _has_other_formats(items: list[dict]) -> bool:
    return any(item.get("title") == "Other Formats" for item in items)


def build_title_meta_items(qmd_path: Path) -> dict:
    """Return the complete title_meta_items dict for the given document."""
    front = _get_front_matter(qmd_path)
    custom = front.get("title-meta-items", {}) or {}

    auto_other = custom.get("other-formats", True)
    # Derive document stem relative to the project root
    project_root = _find_project_root(qmd_path.parent.resolve())
    declared_formats = _get_declared_formats(front, project_root)
    try:
        rel = qmd_path.resolve().relative_to(project_root)
        doc_stem = str(rel.with_suffix(""))
    except ValueError:
        doc_stem = qmd_path.stem

    result = {}
    for fmt in ("html", "pdf"):
        items = []
        # 1. Explicit items from YAML
        for item in custom.get(fmt, []):
            entry = {
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "content": item.get("content", ""),
            }
            if item.get("icon"):
                entry["content_class"] = item["icon"]
            items.append(entry)

        # 2. Auto-generated "Other Formats" – only for declared formats
        if auto_other and not _has_other_formats(items):
            items.extend(_auto_other_formats(doc_stem, fmt, declared_formats))

        result[fmt] = items

    return result


# ---------------------------------------------------------------------------
# sys.argv[0] is the script path; sys.argv[1] should be the QMD stem
if len(sys.argv) < 2:
    raise SystemExit(
        "Usage: %run ../_include/_title_meta_builder.py <stem>\n"
        "  e.g. %run ../_include/_title_meta_builder.py riscv_space"
    )

stem = sys.argv[1]
qmd_file = _find_qmd_file(stem)
if qmd_file is None:
    raise FileNotFoundError(
        f"Cannot locate {stem}.qmd. _title_meta_builder.py must be %run from a "
        ".qmd cell in the same directory as the .qmd source."
    )

title_meta_items = build_title_meta_items(qmd_file)
