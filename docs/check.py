#!/usr/bin/env python3
"""
SSCCS Docs Checker

Usage:
    python check.py                           # Full pipeline: fix + validate + citations
    python check.py --fix-only                # Only link normalization
    python check.py --validate-only           # Link validation + citation consistency
    python check.py --check-uncited           # Find uncited .bib entries with topic categorization
    python check.py --compare-citations A B   # Compare citations between two QMD files
    python check.py --check-section-refs      # Check for unused/broken section cross-references
    python check.py --fix-section-refs        # Auto-comment out unused section definitions
    python check.py --all                     # Run ALL checks including deep uncited analysis
"""

import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

import requests

# ============================================================
# Configuration
# ============================================================
IGNORED_DIRS = {
    ".venv",
    ".git",
    "_site",
    "_pages",
    "_cache*",
    ".quarto",
    "_docsbuild",
    "_llms",
    "node_modules",
    "__pycache__",
    "*_cached",
    "*_files",
    "*_libs",
    "*_output",
    "*_extensions",
    ".*",
    "_jupyter_cache",
}
VALID_EXTENSIONS = {".md", ".qmd", ".yml", ".yaml", ".json", ".bib"}
SOURCE_EXTENSIONS = {
    ".qmd",
    ".md",
    ".rs",
    ".py",
    ".yml",
    ".yaml",
    ".json",
    ".toml",
    ".bib",
}
IGNORE_FILES = {"README.md"}
IGNORE_URL_PATTERNS = ["*keys.openpgp.org*", "*?token=*"]


def _is_ignored_path(file_path: Path, root: Path) -> bool:
    """Return True if any part of file_path matches an IGNORED_DIRS entry.

    Each IGNORED_DIRS entry is matched via fnmatch, so glob patterns
    like ``_llms*`` or ``_cached*`` are supported alongside exact names.
    """
    parts = file_path.relative_to(root).parts
    for part in parts:
        for pattern in IGNORED_DIRS:
            if fnmatch.fnmatch(part, pattern):
                return True
    return False


TOPIC_KEYWORDS = {
    "riscv": ["risc", "openhw", "core-v", "riscv", "spike", "verilator", "risc-v"],
    "space": [
        "radiation",
        "space",
        "tristan",
        "rad-hard",
        "single-event",
        " SEE ",
        " TID ",
        "cosmic",
    ],
    "security": [
        "side-channel",
        "fault-injection",
        "glitch",
        "power-analysis",
        "timing-attack",
    ],
    "formal": ["formal-verif", "coq", "isabelle", "proof", "theorem", "model-check"],
    "embedded": ["embedded", "microcontroller", "firmware", "rtos", "bare-metal"],
}


# ============================================================
# Quarto Metadata Extraction
# ============================================================
_quarto_inspect_cache = {}


def run_quarto_inspect(filepath: Path) -> Optional[Dict]:
    """Cached version of run_quarto_inspect to avoid repeated subprocess calls."""
    if filepath in _quarto_inspect_cache:
        return _quarto_inspect_cache[filepath]
    if not shutil.which("quarto"):
        return None
    try:
        result = subprocess.run(
            ["quarto", "inspect", str(filepath)],
            capture_output=True,
            text=True,
            timeout=5,  # shortened timeout
            check=False,
        )
        if result.returncode != 0:
            return None
        data = json.loads(result.stdout)
        _quarto_inspect_cache[filepath] = data
        return data
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
        return None


def extract_bibliography_from_metadata(metadata: Dict) -> List[str]:
    """
    Extract bibliography paths from Quarto metadata dict.
    Handles string paths, lists of paths, or inline YAML.
    """
    bib_value = metadata.get("bibliography")
    if not bib_value:
        return []

    bib_paths = []
    if isinstance(bib_value, str):
        bib_paths.append(bib_value)
    elif isinstance(bib_value, list):
        for item in bib_value:
            if isinstance(item, str):
                bib_paths.append(item)
    # Inline YAML dict is not a file path, ignored

    return [bp.strip() for bp in bib_paths if bp.endswith(".bib")]


def get_bibliography_files(source_file: Path, root: Path) -> List[Path]:
    """Uses cached quarto inspect to get bibliography paths."""
    metadata = run_quarto_inspect(source_file)
    if metadata:
        bib_refs = extract_bibliography_from_metadata(metadata)
        resolved = []
        for ref in bib_refs:
            p = (source_file.parent / ref).resolve()
            if p.exists():
                resolved.append(p)
        return resolved

    # Fallback regex parsing (unchanged)
    try:
        content = source_file.read_text(encoding="utf-8")
        if not content.startswith("---"):
            return []
        match = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)
        if not match:
            return []
        frontmatter = match.group(1)
        bib_match = re.search(r"^bibliography:\s*(.+?)$", frontmatter, re.MULTILINE)
        if not bib_match:
            return []
        bib_value = bib_match.group(1).strip()
        bib_paths = []
        if bib_value.startswith("["):
            for item in re.findall(r'["\']?([^"\',\]]+\.bib)["\']?', bib_value):
                bib_paths.append(item.strip())
        elif bib_value.endswith(".bib"):
            bib_paths.append(bib_value.strip("\"'"))
        resolved = []
        for ref in bib_paths:
            p = (source_file.parent / ref).resolve()
            if p.exists():
                resolved.append(p)
        return resolved
    except Exception:
        return []


# ============================================================
# Citation Extraction
# ============================================================
def extract_bibtex_citation_keys(content: str) -> Set[str]:
    """Extract all citation keys from BibTeX content."""
    keys = set()
    pattern = re.compile(r"@\w+\s*\{\s*([^,\s]+)\s*,", re.IGNORECASE)
    for match in pattern.finditer(content):
        keys.add(match.group(1).strip())
    return keys


def extract_quarto_citation_keys(content: str) -> Set[str]:
    """
    Extract citation keys from Quarto/Markdown body (excluding frontmatter).
    Filters out cross-references (sec-, fig-, tbl-, eq-, lst-) and common variables.
    """
    keys = set()
    excluded = {
        "title",
        "subtitle",
        "author",
        "date",
        "abstract",
        "keywords",
        "affiliation",
        "correspondence",
        "acknowledgements",
        "references",
        "maketitle",
        "ssccs",
    }
    excluded_prefixes = ("sec-", "fig-", "tbl-", "eq-", "lst-")

    # Match @key requiring at least one digit or colon to reduce false positives
    pattern = re.compile(r"(?<!\[-\*)@([a-zA-Z][a-zA-Z0-9_:\-]*[0-9:][a-zA-Z0-9_:\-]*)")
    for match in pattern.finditer(content):
        key = match.group(1).strip()
        if key.lower() not in excluded and not key.startswith(excluded_prefixes):
            keys.add(key)
    return keys


def extract_citations_from_file(filepath: Path) -> Set[str]:
    """Extract citations from QMD/MD file body (excluding YAML frontmatter)."""
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception:
        return set()

    if content.startswith("---"):
        match = re.search(r"^---\n.*?\n---", content, re.DOTALL)
        if match:
            content = content[match.end() :]

    return extract_quarto_citation_keys(content)


# ============================================================
# Link Extraction Helpers
# ============================================================
def extract_yaml_frontmatter_links(
    content: str, require_delimiters: bool = True
) -> List[Tuple[str, int]]:
    """Extract links from YAML frontmatter (or whole YAML file if require_delimiters=False)."""
    links = []
    lines = content.split("\n")
    start_idx = 0
    end_idx = len(lines)

    if require_delimiters:
        if not content.startswith("---"):
            return links
        # find closing ---
        for i, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                end_idx = i
                break
        if end_idx == len(lines):
            # no closing delimiter found
            return links
        start_idx = 1  # skip opening ---line
    # else treat whole file as frontmatter, start_idx=0, end_idx=len(lines)

    url_pattern = re.compile(
        r'(?:^|:\s|-)\s*(https?://[^\s\'"]+|[^\s\'"]+\.(?:pdf|html|md|qmd|bib))(?:\s|$)'
    )
    for i, line in enumerate(lines[start_idx:end_idx], start=start_idx + 1):
        for match in re.findall(url_pattern, line):
            url = match.strip()
            if url and not url.startswith("#"):
                links.append((url, i))
    return links


def extract_bibtex_links(content: str) -> List[Tuple[str, int]]:
    """Extract URLs/DOIs from BibTeX entries."""
    links = []
    lines = content.split("\n")
    patterns = [
        (re.compile(r"^\s*url\s*=\s*\{?([^}\s]+)\}?\s*,?\s*$", re.I), None),
        (
            re.compile(r"^\s*doi\s*=\s*\{?([^}\s]+)\}?\s*,?\s*$", re.I),
            lambda v: f"https://doi.org/{v}" if not v.startswith("http") else v,
        ),
        (
            re.compile(r"^\s*eprint\s*=\s*\{?([^}\s]+)\}?\s*,?\s*$", re.I),
            lambda v: (
                f"https://arxiv.org/abs/{v.replace('arXiv:', '').split()[0]}"
                if "." in v.replace("arXiv:", "").split()[0]
                else None
            ),
        ),
    ]
    for i, line in enumerate(lines, start=1):
        for pattern, transformer in patterns:
            match = pattern.match(line)
            if match:
                value = match.group(1).strip("{} \t")
                if transformer:
                    transformed = transformer(value)
                    if transformed and transformed.startswith("http"):
                        links.append((transformed, i))
                elif value.startswith("http"):
                    links.append((value, i))
    return links


# ============================================================
# Uncited References Analysis
# ============================================================
def find_uncited_references(
    bib_path: Path, doc_paths: List[Path], verbose: bool = False
) -> Dict[str, List[str]]:
    """Find entries in .bib file not cited in any of the given documents."""
    try:
        bib_content = bib_path.read_text(encoding="utf-8")
    except Exception:
        return {}

    bib_entries = extract_bibtex_citation_keys(bib_content)
    all_cited = set()
    for doc in doc_paths:
        if doc.exists() and doc.suffix in {".qmd", ".md"}:
            all_cited.update(extract_citations_from_file(doc))

    uncited = bib_entries - all_cited
    categorized = {"other": []}

    for key in uncited:
        entry_pattern = re.compile(rf"@[\w]+\s*\{{\s*{re.escape(key)}\s*,", re.I)
        entry_match = entry_pattern.search(bib_content)
        if not entry_match:
            categorized["other"].append(key)
            continue

        start_pos = entry_match.end()
        snippet = bib_content[start_pos : start_pos + 800].lower()

        categorized_flag = False
        for topic, keywords in TOPIC_KEYWORDS.items():
            if any(kw.lower() in snippet for kw in keywords):
                categorized.setdefault(topic, []).append(key)
                categorized_flag = True
                break
        if not categorized_flag:
            categorized["other"].append(key)

    if verbose:
        print(f"\nBibliography Analysis: {bib_path.name}")
        print(
            f"   Total: {len(bib_entries)}, Cited: {len(bib_entries - uncited)}, Uncited: {len(uncited)}"
        )
        for topic, keys in sorted(categorized.items()):
            if keys:
                print(f"   - {topic.upper()}: {len(keys)}")

    return categorized


# ============================================================
# Cross-Document Citation Comparison
# ============================================================
def compare_citations_between_files(
    file_a: Path, file_b: Path, bib_path: Optional[Path] = None, verbose: bool = False
) -> Dict:
    """Compare citation keys between two QMD/MD documents."""
    keys_a = extract_citations_from_file(file_a) if file_a.exists() else set()
    keys_b = extract_citations_from_file(file_b) if file_b.exists() else set()

    result = {
        "only_in_a": keys_a - keys_b,
        "only_in_b": keys_b - keys_a,
        "in_both": keys_a & keys_b,
        "missing_in_bib": {},
    }

    if bib_path and bib_path.exists():
        try:
            bib_keys = extract_bibtex_citation_keys(
                bib_path.read_text(encoding="utf-8")
            )
            for label, keys in [
                ("only_in_a", result["only_in_a"]),
                ("only_in_b", result["only_in_b"]),
            ]:
                missing = keys - bib_keys
                if missing:
                    result["missing_in_bib"][label] = sorted(missing)
        except Exception:
            pass

    if verbose:
        print(f"\nCitation Comparison: {file_a.name} vs {file_b.name}")
        print(f"   {file_a.name}: {len(keys_a)} citations")
        print(f"   {file_b.name}: {len(keys_b)} citations")
        print(
            f"   Shared: {len(result['in_both'])}, Only A: {len(result['only_in_a'])}, Only B: {len(result['only_in_b'])}"
        )

    return result


def show_citation_context(
    filepath: Path, target_keys: Set[str], context_lines: int = 2
):
    """Print lines around each target citation key in a file."""
    if not filepath.exists():
        return
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception:
        return
    lines = content.splitlines()

    for key in sorted(target_keys):
        pattern = f"@{key}"
        for i, line in enumerate(lines):
            if pattern in line:
                start = max(0, i - context_lines)
                end = min(len(lines), i + context_lines + 1)
                print(f"\n{filepath.name}:{i + 1} - @{key}")
                for j in range(start, end):
                    marker = "->" if j == i else " "
                    print(f"{marker} {j + 1:4}: {lines[j]}")
                break


# ============================================================
# Section Cross-Reference Checking
# ============================================================
def extract_section_definitions(content: str) -> Dict[str, Dict]:
    """Extract section definitions: # Header {#sec-foo} (including level 1)"""
    sections = {}
    # Includes level 1 headers ( #{1,6} )
    header_pattern = re.compile(
        r"^(#{1,6})\s+(.+?)\s*\{#(sec-[a-zA-Z0-9_\-]+)\}\s*$", re.MULTILINE
    )
    bare_id_pattern = re.compile(r"^\{#(sec-[a-zA-Z0-9_\-]+)\}\s*$", re.MULTILINE)

    lines = content.split("\n")
    for i, line in enumerate(lines, start=1):
        match = header_pattern.match(line)
        if match:
            sections[match.group(3)] = {
                "title": match.group(2).strip(),
                "level": len(match.group(1)),
                "line": i,
                "type": "header",
            }
            continue
        bare_match = bare_id_pattern.match(line)
        if bare_match:
            sec_id = bare_match.group(1)
            title = "Untitled Section"
            for j in range(i - 2, max(-1, i - 10), -1):
                prev = lines[j].strip()
                if prev and not prev.startswith("#") and not prev.startswith("{#"):
                    title = prev
                    break
            sections[sec_id] = {"title": title, "level": 0, "line": i, "type": "bare"}
    return sections


def extract_section_references(content: str) -> Dict[str, List[Dict]]:
    refs = {}
    lines = content.split("\n")

    # Pattern 1: Quarto @sec-xxx syntax
    pattern_at = re.compile(r"@(sec-[a-zA-Z0-9_\-]+)")

    # Pattern 2: Markdown link syntax [text](#sec-xxx) or [text]( #sec-xxx )
    pattern_md = re.compile(r"\]\(\s*#(sec-[a-zA-Z0-9_\-]+)\s*\)")

    for i, line in enumerate(lines, start=1):
        # @sec-xxx processing
        for match in pattern_at.finditer(line):
            if is_inside_inline_code(line, match.start()):
                continue
            ref_id = match.group(1)
            ref_type = (
                "inline"
                if (match.start() > 0 and line[match.start() - 1] == "[")
                else "citation"
            )
            start_ctx = max(0, match.start() - 20)
            end_ctx = min(len(line), match.end() + 20)
            context = line[start_ctx:end_ctx].strip()
            refs.setdefault(ref_id, []).append(
                {"line": i, "context": context, "type": ref_type}
            )

        # Markdown link handling
        for match in pattern_md.finditer(line):
            if is_inside_inline_code(line, match.start()):
                continue
            ref_id = match.group(1)
            start_ctx = max(0, match.start() - 20)
            end_ctx = min(len(line), match.end() + 20)
            context = line[start_ctx:end_ctx].strip()
            refs.setdefault(ref_id, []).append(
                {"line": i, "context": context, "type": "markdown-link"}
            )

    return refs


def check_all_section_references(target_dir: str, verbose: bool = False) -> Dict:
    """Check section reference consistency across all QMD/MD files."""
    root = Path(target_dir).resolve()
    if not root.exists():
        print(f"ERROR: {root} does not exist")
        return {}

    if verbose:
        print(f"Checking section cross-references in {root}...")
        print("-" * 60)

    global_definitions: Dict[str, Dict] = {}
    global_references: Dict[str, List] = {}

    for file_path in root.rglob("*.qmd"):
        if _is_ignored_path(file_path, root):
            continue
        if file_path.name in IGNORE_FILES:
            continue

        try:
            original_content = file_path.read_text(encoding="utf-8")
        except Exception:
            continue

        # Find the frontmatter end line
        frontmatter_end_line = 0
        if original_content.startswith("---"):
            lines = original_content.split("\n")
            for idx, line in enumerate(lines[1:], start=2):
                if line.strip() == "---":
                    frontmatter_end_line = idx
                    break

        # Extract definitions (use full original)
        defined = extract_section_definitions(original_content)
        # Reference extraction (use full original)
        referenced = extract_section_references(original_content)

        # Remove internal references to Frontmatter
        referenced_filtered = {}
        for sec_id, usages in referenced.items():
            filtered = [u for u in usages if u["line"] > frontmatter_end_line]
            if filtered:
                referenced_filtered[sec_id] = filtered

        # Add to global map
        for sec_id, meta in defined.items():
            if sec_id not in global_definitions:
                global_definitions[sec_id] = {**meta, "source_file": file_path}

        for sec_id, usages in referenced_filtered.items():
            for usage in usages:
                global_references.setdefault(sec_id, []).append(
                    {**usage, "source_file": file_path}
                )

    defined_ids = set(global_definitions.keys())
    referenced_ids = set(global_references.keys())
    unused = sorted(defined_ids - referenced_ids)
    broken = sorted(referenced_ids - defined_ids)

    print("\nSection Reference Summary:")
    print(f"   Total defined sections: {len(defined_ids)}")
    print(f"   Total referenced sections: {len(referenced_ids)}")
    print(f"   Unused definitions: {len(unused)}")
    print(f"   Broken references: {len(broken)}")

    if unused and verbose:
        print("\nUnused Section Definitions:")
        for sec_id in unused:
            meta = global_definitions[sec_id]
            rel_file = meta["source_file"].relative_to(root)
            print(f'   - {sec_id} in {rel_file}:{meta["line"]} ("{meta["title"]}")')
    elif unused and not verbose:
        # Only partially visible in non-detailed mode
        print("\nUnused Section Definitions (first 10):")
        for sec_id in unused[:10]:
            meta = global_definitions[sec_id]
            rel_file = meta["source_file"].relative_to(root)
            print(f"   - {sec_id} in {rel_file}:{meta['line']}")
        if len(unused) > 10:
            print(f"   ... and {len(unused) - 10} more")

    if broken and verbose:
        print("\nBroken Section References:")
        for sec_id in broken:
            usage = global_references[sec_id][0]
            rel_file = usage["source_file"].relative_to(root)
            print(f"   - {sec_id} in {rel_file}:{usage['line']} ({usage['context']})")
    elif broken and not verbose:
        print("\nBroken Section References (first 10):")
        for sec_id in broken[:10]:
            usage = global_references[sec_id][0]
            rel_file = usage["source_file"].relative_to(root)
            print(f"   - {sec_id} in {rel_file}:{usage['line']}")
        if len(broken) > 10:
            print(f"   ... and {len(broken) - 10} more")

    return {
        "unused": unused,
        "broken": broken,
        "definitions": global_definitions,
        "references": global_references,
    }


def _comment_out_section_id(file_path: Path, sec_id: str, target_line: int):
    """Convert: ## Title {#sec-foo} -> ## Title <!--{#sec-foo} -->"""
    try:
        content = file_path.read_text(encoding="utf-8")
        lines = content.split("\n")
        if 0 < target_line <= len(lines):
            line_idx = target_line - 1
            modified = re.sub(
                r"\{#(" + re.escape(sec_id) + r")\}",
                r"<!-- {\#\1} -->",
                lines[line_idx],
            )
            if modified != lines[line_idx]:
                lines[line_idx] = modified
                file_path.write_text("\n".join(lines), encoding="utf-8")
    except Exception as e:
        print(f"Warning: Could not modify {file_path}: {e}")


# ============================================================
# Link Normalization & Validation
# ============================================================
def get_std_base(name: str) -> str:
    base = os.path.splitext(name)[0]
    if base.upper() == "README":
        return "README"
    prefix = "_" if base.startswith("_") else ""
    actual = base[1:] if base.startswith("_") else base
    new = actual.lower().replace(" ", "_").replace("-", "_")
    new = re.sub(r"[^a-z0-9_\u1100-\u11FF\uAC00-\uD7AF]", "", new)
    new = re.sub(r"_+", "_", new).strip("_")
    return prefix + new if prefix else new


def build_global_inventory(root_path: Path) -> Dict[str, Path]:
    inventory = {}
    for ext in (".md", ".qmd"):
        for file_path in root_path.rglob(f"*{ext}"):
            if _is_ignored_path(file_path, root_path):
                continue
            key = get_std_base(file_path.name)
            rel = file_path.relative_to(root_path)
            if key in inventory:
                parent = file_path.parent.name
                key = f"{parent}_{key}"
            inventory[key] = rel
    return inventory


def is_inside_inline_code(content: str, match_start: int) -> bool:
    before = content[:match_start]
    backticks = [i for i, c in enumerate(before) if c == "`"]
    return len(backticks) % 2 == 1


def normalize_link_to_absolute(
    link: str, source_file: Path, root: Path, inventory: Dict[str, Path]
) -> Optional[str]:
    if link.startswith(
        ("http://", "https://", "mailto:", "tel:", "#", "/", "data:", "ftp://")
    ):
        return None
    anchor = query = ""
    if "#" in link:
        link, anchor = link.split("#", 1)
        anchor = "#" + anchor
    if "?" in link:
        link, query = link.split("?", 1)
        query = "?" + query
    p = Path(link)
    if not p.stem or p.stem not in inventory:
        return None
    target_rel = inventory[p.stem]
    abs_path = "/" + str(target_rel).replace("\\", "/")
    orig_ext = p.suffix.lower()
    if orig_ext == ".html":
        abs_path = Path(abs_path).with_suffix(".html")
    else:
        abs_path = Path(abs_path).with_suffix(target_rel.suffix)
    return str(abs_path).replace("\\", "/") + query + anchor


def sync_all_links(target_dir: str):
    root = Path(target_dir).resolve()
    if not root.exists():
        print(f"ERROR: {root} does not exist")
        return
    print(f"Building inventory from {root} ...")
    inventory = build_global_inventory(root)
    print(f"Indexed {len(inventory)} documents")
    print("-" * 60)
    md_link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
    total_fixed = 0
    processed = 0
    for file_path in root.rglob("*"):
        if file_path.suffix not in VALID_EXTENSIONS:
            continue
        if _is_ignored_path(file_path, root):
            continue
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"Cannot read {file_path}: {e}")
            continue
        processed += 1
        new_content = content
        offset = 0
        for match in md_link_pattern.finditer(content):
            url = match.group(2)
            start, end = match.span()
            if url.startswith(
                ("http://", "https://", "mailto:", "tel:", "#", "ftp://", "file://")
            ):
                continue
            new_url = normalize_link_to_absolute(url, file_path, root, inventory)
            if new_url and new_url != url:
                text = match.group(1)
                new_full = f"[{text}]({new_url})"
                new_content = (
                    new_content[: start + offset]
                    + new_full
                    + new_content[end + offset :]
                )
                offset += len(new_full) - len(match.group(0))
                total_fixed += 1
        if new_content != content:
            file_path.write_text(new_content, encoding="utf-8")
            print(f"Fixed: {file_path.relative_to(root)}")
    print("-" * 60)
    print(f"Processed {processed} files, fixed {total_fixed} links.")


def should_ignore_url(url: str) -> bool:
    return any(fnmatch.fnmatch(url, pattern) for pattern in IGNORE_URL_PATTERNS)


def is_valid_quarto_link(link_path: str, source_file: Path, root: Path) -> bool:
    """Securely verify local links (including .html) in Quarto projects
    -/docs/report/poc_diagnosis.html → Check whether docs/report/poc_diagnosis.qmd/md exists
    -Minimize side effects: handle all out-of-root links, relative paths, and directory indexes
    """
    clean = link_path.split("#")[0].split("?")[0].strip()
    if not clean or clean.startswith(
        ("#", "mailto:", "tel:", "data:", "http", "https")
    ):
        return True  # External links or anchors are not subject to separate inspection.

    is_html = clean.endswith(".html")
    is_dir_slash = clean.endswith("/")
    known_ext = clean.endswith((".qmd", ".md", ".bib"))

    # 1. Path normalization (based on root)
    try:
        if clean.startswith("/"):
            # Absolute path (root-relative path starting with /in Quarto)
            target_path = clean.lstrip("/")
        else:
            # Relative path → resolve based on source_file
            target_path = str((source_file.parent / clean).resolve().relative_to(root))
    except (ValueError, FileNotFoundError):
        # Path outside the root → invalid (handled safely)
        return False

    target = root / target_path

    # 2. .html → source file mapping (the most important part)
    if is_html:
        base = target.with_suffix("")  # remove .html
        if base.with_suffix(".qmd").exists() or base.with_suffix(".md").exists():
            return True

        # Safety device: Search again under docs/(when the project structure is docs/)
        if not str(target_path).startswith("docs/"):
            alt_base = (root / "docs" / target_path).with_suffix("")
            if (
                alt_base.with_suffix(".qmd").exists()
                or alt_base.with_suffix(".md").exists()
            ):
                return True

    # 3. Directory index (e.g. /report/→ index.qmd)
    elif is_dir_slash:
        if (target / "index.qmd").exists() or (target / "index.md").exists():
            return True

    # 4. If you already have an extension
    elif known_ext:
        return target.exists()

    # 5. Automatic matching of .qmd/.md if there is no extension
    else:
        if target.with_suffix(".qmd").exists() or target.with_suffix(".md").exists():
            return True

    # 6. Final fallback (docs, src, content)
    for sub in ("", "docs", "src", "content"):
        alt = root / sub / target_path
        if is_html:
            base = alt.with_suffix("")
            if base.with_suffix(".qmd").exists() or base.with_suffix(".md").exists():
                return True
        elif (
            alt.exists()
            or alt.with_suffix(".qmd").exists()
            or alt.with_suffix(".md").exists()
        ):
            return True

    return False


def validate_all_links(target_dir: str, verbose: bool = False, max_workers: int = 8):
    root = Path(target_dir).resolve()
    if not root.exists():
        print(f"ERROR: {root} does not exist")
        return
    print(f"Validating links in {root} using {max_workers} threads...")
    print(f"  (ignoring {len(IGNORE_URL_PATTERNS)} URL patterns)")
    print("-" * 60)
    md_link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
    html_link_pattern = re.compile(r'(?:href|src)=["\']([^"\']+)["\']', re.I)
    files_to_check = [
        fp
        for fp in root.rglob("*")
        if fp.suffix in VALID_EXTENSIONS
        and not _is_ignored_path(fp, root)
        and fp.name not in IGNORE_FILES
    ]
    total_files = len(files_to_check)
    broken_local, broken_remote = [], []
    checked_links = processed_files = 0
    start_time = time.time()
    data_lock = Lock()
    print_lock = Lock()
    session = requests.Session()
    session.headers.update({"User-Agent": "SSCCS-LinkChecker/1.0"})
    running = True

    def status_reporter():
        while running:
            time.sleep(1.0)
            with data_lock:
                fd, ld = processed_files, checked_links
            elapsed = time.time() - start_time
            with print_lock:
                print(
                    f"\r Files: {fd}/{total_files} | Links: {ld} | Time: {elapsed:.1f}s",
                    end="",
                    flush=True,
                )

    threading.Thread(target=status_reporter, daemon=True).start()

    def process_file(file_path: Path):
        nonlocal processed_files, checked_links
        file_broken_local, file_broken_remote = [], []
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            with data_lock:
                processed_files += 1
            return [], []
        links = set()
        for match in md_link_pattern.finditer(content):
            if is_inside_inline_code(content, match.start()):
                continue
            links.add((match.group(2), content.count("\n", 0, match.start()) + 1))
        for match in html_link_pattern.finditer(content):
            if is_inside_inline_code(content, match.start()):
                continue
            links.add((match.group(1), content.count("\n", 0, match.start()) + 1))
        if file_path.suffix in {".qmd", ".md"}:
            links.update(extract_yaml_frontmatter_links(content))
        if file_path.suffix in {".yml", ".yaml"}:
            links.update(
                extract_yaml_frontmatter_links(content, require_delimiters=False)
            )
        if file_path.suffix == ".bib":
            links.update(extract_bibtex_links(content))
        for url, line in links:
            if (
                not url
                or url.startswith(("#", "mailto:", "tel:", "data:"))
                or should_ignore_url(url)
                or "{" in url
                or "[" in url
            ):
                continue
            checked_links += 1
            clean_url = url.split("#")[0].split("?")[0]
            parsed = urlparse(url)
            if parsed.scheme in ("http", "https"):
                try:
                    resp = session.head(url, timeout=10, allow_redirects=True)
                    if resp.status_code >= 400:
                        try:
                            get_resp = session.get(
                                url, timeout=10, allow_redirects=True, stream=True
                            )
                            first_bytes = next(get_resp.iter_content(1024))
                            if first_bytes and (
                                first_bytes.startswith(b"%PDF")
                                or first_bytes[0:2] in (b"PK", b"\x89H")
                            ):
                                continue
                            if resp.status_code in (403, 418):
                                continue
                            # Any 4xx/5xx is considered broken
                            file_broken_remote.append(
                                (
                                    file_path.relative_to(root),
                                    url,
                                    f"{resp.status_code}",
                                    line,
                                )
                            )
                        except Exception:
                            if resp.status_code in (403, 418):
                                continue
                            file_broken_remote.append(
                                (
                                    file_path.relative_to(root),
                                    url,
                                    f"{resp.status_code} (GET failed)",
                                    line,
                                )
                            )

                except Exception:
                    file_broken_remote.append(
                        (file_path.relative_to(root), url, "Connection Error", line)
                    )
            elif clean_url and not is_valid_quarto_link(clean_url, file_path, root):
                file_broken_local.append(
                    (file_path.relative_to(root), url, "Not Found", line)
                )
        with data_lock:
            processed_files += 1
        return file_broken_local, file_broken_remote

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_file, fp): fp for fp in files_to_check}
        for future in as_completed(futures):
            local, remote = future.result()
            broken_local.extend(local)
            broken_remote.extend(remote)

    running = False
    print()
    print("-" * 60)
    if broken_local or broken_remote:
        print("\n" + "=" * 60)
        print(" BROKEN LINKS FOUND")
        print("=" * 60)
        if broken_local:
            print(f"\nLocal broken links ({len(broken_local)}):")
            for rel_path, url, reason, line in broken_local:
                print(f"  {rel_path}:{line}: {url} ({reason})")
        if broken_remote:
            print(f"\nRemote broken links ({len(broken_remote)}):")
            for rel_path, url, reason, line in broken_remote:
                print(f"  {rel_path}:{line}: {url} ({reason})")
    else:
        print("\nAll links are valid.")
    elapsed = time.time() - start_time
    print(
        f"\nValidation finished. Checked {checked_links} links, found {len(broken_local) + len(broken_remote)} broken in {elapsed:.1f}s."
    )


# ============================================================
# Citation Consistency Check
# ============================================================
def check_citation_consistency(
    target_dir: str, cleanup: bool = False, verbose: bool = False
):
    root = Path(target_dir).resolve()
    if not root.exists():
        print(f"ERROR: {root} does not exist")
        return

    if verbose:
        print(f"Checking citation consistency in {root}...")
        print("-" * 60)

    bib_files: Dict[Path, Set[str]] = {}
    for bib_path in root.rglob("*.bib"):
        if _is_ignored_path(bib_path, root):
            continue
        try:
            bib_files[bib_path] = extract_bibtex_citation_keys(
                bib_path.read_text(encoding="utf-8")
            )
        except Exception:
            continue

    bib_to_docs: Dict[Path, Dict[Path, Set[str]]] = {bib: {} for bib in bib_files}
    citation_issues = []

    # Process each .qmd/.md file
    for file_path in root.rglob("*"):
        if file_path.suffix not in {".qmd", ".md"}:
            continue
        if _is_ignored_path(file_path, root) or file_path.name in IGNORE_FILES:
            continue

        bib_refs = get_bibliography_files(file_path, root)  # Use cached version
        if not bib_refs:
            continue

        cited_keys = extract_citations_from_file(file_path)
        for bib_path in bib_refs:
            if bib_path not in bib_files:
                continue
            bib_to_docs[bib_path][file_path] = cited_keys.copy()
            missing = cited_keys - bib_files[bib_path]
            for key in missing:
                citation_issues.append(
                    (file_path.relative_to(root), bib_path.relative_to(root), key)
                )

    completely_uncited = {}
    for bib_path, docs in bib_to_docs.items():
        if not docs:
            continue
        key_to_citing_docs = {key: set() for key in bib_files[bib_path]}
        for doc_path, cited_keys in docs.items():
            for key in cited_keys:
                if key in key_to_citing_docs:
                    key_to_citing_docs[key].add(doc_path)
        uncited = {k for k, v in key_to_citing_docs.items() if not v}
        if uncited and not any(key_to_citing_docs.values()):
            completely_uncited[bib_path] = uncited

    if cleanup and completely_uncited:
        print("\n" + "=" * 60)
        print(" CLEANUP PHASE")
        print("=" * 60)
        for bib_path, keys in list(completely_uncited.items()):
            rel_bib = bib_path.relative_to(root)
            docs = bib_to_docs.get(bib_path, {})
            if len(docs) == 1:
                print(
                    f"\nCleaning {rel_bib} (no citations from: {list(docs.keys())[0].relative_to(root)})"
                )
                _remove_bib_entries(bib_path, keys)
                print(f"  Removed {len(keys)} uncited entries")
        print("\nCleanup complete. Re-run validation to verify.")

    has_issues = citation_issues or completely_uncited
    if has_issues:
        print("\n" + "=" * 60)
        print(" CITATION CONSISTENCY ISSUES FOUND")
        print("=" * 60)
        if citation_issues:
            print(f"\nCitations not in bibliography ({len(citation_issues)}):")
            for doc_path, bib_path, key in sorted(citation_issues):
                print(f"  {doc_path}: @{key} (not in {bib_path})")
        if completely_uncited:
            total = sum(len(v) for v in completely_uncited.values())
            print(f"\nCompletely uncited bibliography entries ({total}):")
            for bib_path, keys in sorted(completely_uncited.items()):
                rel = bib_path.relative_to(root)
                docs = bib_to_docs.get(bib_path, {})
                print(
                    f"  {rel}: {len(keys)} uncited (referenced by {len(docs)} doc(s))"
                )
                if verbose:
                    for key in sorted(keys):
                        print(f"    - @{key}")
                else:
                    for key in sorted(keys)[:5]:
                        print(f"    - @{key}")
                    if len(keys) > 5:
                        print(f"    ... and {len(keys) - 5} more")
    else:
        print("\nAll citations are consistent.")
    print(f"\nChecked {len(bib_files)} bibliography files.")


def _remove_bib_entries(bib_path: Path, keys_to_remove: Set[str]):
    try:
        content = bib_path.read_text(encoding="utf-8")
    except Exception:
        return
    lines = content.split("\n")
    new_lines, skip_entry, brace_count = [], False, 0
    for line in lines:
        entry_match = re.match(r"@\w+\s*\{\s*([^,\s]+)\s*,", line, re.I)
        if entry_match:
            current_key = entry_match.group(1).strip()
            if current_key in keys_to_remove:
                skip_entry = True
                brace_count = line.count("{") - line.count("}")
            else:
                skip_entry = False
        if skip_entry:
            brace_count += line.count("{") - line.count("}")
            if brace_count <= 0:
                skip_entry = False
        else:
            new_lines.append(line)
    bib_path.write_text("\n".join(new_lines), encoding="utf-8")

def validate_yaml_relative_paths(target_dir: str):
    """Validate relative paths in YAML front matter of QMD/MD files."""
    import yaml

    root = Path(target_dir).resolve()
    print(f"\n{'='*60}\n YAML RELATIVE PATH VALIDATION\n{'='*60}\n")

    PATH_KEYS = {"metadata-files", "bibliography", "csl"}
    META_LINK_KEYS = {"link"}

    errors = 0
    checked = 0

    for qmd in sorted(root.rglob("*.qmd")):
        if _is_ignored_path(qmd, root):
            continue
        try:
            text = qmd.read_text(encoding="utf-8")
        except Exception:
            continue
        if not text.startswith("---"):
            continue
        m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
        if not m:
            continue
        try:
            fm = yaml.safe_load(m.group(1)) or {}
        except Exception:
            continue
        if not isinstance(fm, dict):
            continue

        doc_dir = qmd.parent
        checked += 1

        def check_path(val, key_name):
            nonlocal errors
            if isinstance(val, str):
                if val.startswith("http") or val.startswith("mailto:"):
                    return
                p = (doc_dir / val).resolve()
                if not p.exists():
                    rel = qmd.relative_to(root)
                    print(f"  {rel}: {key_name} -> {val}  [NOT FOUND]")
                    errors += 1
            elif isinstance(val, list):
                for v in val:
                    check_path(v, key_name)

        for key in PATH_KEYS:
            if key in fm:
                check_path(fm[key], key)

        ctm = fm.get("custom-title-meta")
        if isinstance(ctm, dict):
            for fmt in ("html", "pdf"):
                items = ctm.get(fmt)
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict):
                            for lk in META_LINK_KEYS:
                                if lk in item:
                                    check_path(item[lk], f"custom-title-meta.{fmt}.{lk}")

    print(f"\n  Checked {checked} files, {errors} broken relative path(s)")
    return errors



# ============================================================
# CLI Entry Point
# ============================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SSCCS Quarto Docs Checker")
    parser.add_argument("--fix-only", action="store_true", help="Only fix links")
    parser.add_argument(
        "--validate-only", action="store_true", help="Only validate links + citations"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--cleanup-uncited",
        action="store_true",
        help="Auto-remove completely uncited .bib entries",
    )
    parser.add_argument(
        "--check-uncited",
        action="store_true",
        help="Find uncited .bib entries with topic categorization",
    )
    parser.add_argument(
        "--compare-citations",
        nargs=2,
        metavar=("FILE_A", "FILE_B"),
        help="Compare citations between two files",
    )
    parser.add_argument(
        "--show-context",
        action="store_true",
        help="Show context lines for missing citations",
    )
    parser.add_argument(
        "--check-section-refs",
        action="store_true",
        help="Check unused/broken section cross-references",
    )
    parser.add_argument(
        "--fix-section-refs",
        action="store_true",
        help="Comment out unused section definitions",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview changes without modifying files"
    )
    parser.add_argument("--all", action="store_true", help="Run ALL checks")
    parser.add_argument("--dir", "-d", default="./", help="Target directory")
    parser.add_argument("--bib", type=str, help="Specific .bib file path")
    args = parser.parse_args()

    root = Path(args.dir).resolve()

    # -----Action flags determination -----
    action_flags = [
        args.check_section_refs,
        args.fix_section_refs,
        args.check_uncited,
        args.compare_citations,
        args.all,
        args.validate_only,
        args.fix_only,
    ]
    no_action_given = not any(action_flags)

    if args.check_section_refs:
        result = check_all_section_references(args.dir, verbose=True)
        sys.exit(1 if (result["unused"] or result["broken"]) else 0)

    if args.fix_section_refs:
        result = check_all_section_references(args.dir, verbose=False)
        if not result["unused"]:
            print("No unused section definitions found.")
            sys.exit(0)
        print(f"\nFound {len(result['unused'])} unused section definitions:")
        for sec_id in result["unused"]:
            meta = result["definitions"][sec_id]
            file_path = meta["source_file"]
            rel_path = file_path.relative_to(root)
            if args.dry_run:
                print(
                    f"  [DRY-RUN] Would comment out: {rel_path}:{meta['line']} @{sec_id}"
                )
            else:
                _comment_out_section_id(file_path, sec_id, meta["line"])
                print(f"  Commented out: {rel_path}:{meta['line']} @{sec_id}")
        if not args.dry_run:
            print("\nCleanup complete. Re-run --check-section-refs to verify.")
        sys.exit(0)

    if args.check_uncited:
        bib = Path(args.bib) if args.bib else None
        bib_files_to_check = []
        if bib and bib.exists():
            bib_files_to_check.append(bib)
        else:
            for qmd in root.rglob("*.qmd"):
                if _is_ignored_path(qmd, root):
                    continue
                refs = get_bibliography_files(qmd, root)
                bib_files_to_check.extend(refs)
            bib_files_to_check = list(set(bib_files_to_check))

        if not bib_files_to_check:
            print("No bibliography files found. Use --bib to specify.")
            sys.exit(1)

        for bib_path in bib_files_to_check:
            docs = [
                fp
                for fp in root.rglob("*.qmd")
                if bib_path in get_bibliography_files(fp, root)
                and not _is_ignored_path(fp, root)
            ]
            if not docs:
                print(f"Warning: No documents reference {bib_path.relative_to(root)}")
                continue
            find_uncited_references(bib_path, docs, verbose=True)
        sys.exit(0)

    if args.compare_citations:
        file_a, file_b = (
            Path(args.compare_citations[0]),
            Path(args.compare_citations[1]),
        )
        bib = Path(args.bib) if args.bib else None
        if not bib:
            common = set(get_bibliography_files(file_a, root)) & set(
                get_bibliography_files(file_b, root)
            )
            if common:
                bib = list(common)[0]

        result = compare_citations_between_files(file_a, file_b, bib, verbose=True)
        if result["only_in_a"]:
            print(f"\nOnly in {file_a.name}:")
            for k in sorted(result["only_in_a"]):
                print(f"  - @{k}")
        if result["only_in_b"]:
            print(f"\nOnly in {file_b.name}:")
            for k in sorted(result["only_in_b"]):
                print(f"  - @{k}")
        if args.show_context:
            if result["only_in_a"]:
                show_citation_context(file_a, result["only_in_a"])
            if result["only_in_b"]:
                show_citation_context(file_b, result["only_in_b"])
        sys.exit(0)

    # --all or no action flag → run all functions
    if args.all or no_action_given:
        sync_all_links(args.dir)
        print("\n" + "=" * 60 + "\n VALIDATION PHASE\n" + "=" * 60 + "\n")
        validate_all_links(args.dir, verbose=args.verbose)
        validate_yaml_relative_paths(args.dir)
        validate_yaml_relative_paths(args.dir)
        print("\n" + "=" * 60 + "\n CITATION CHECK PHASE\n" + "=" * 60 + "\n")
        check_citation_consistency(args.dir, cleanup=args.cleanup_uncited)
        print("\n" + "=" * 60 + "\n SECTION REFERENCE CHECK\n" + "=" * 60 + "\n")
        check_all_section_references(args.dir, verbose=True)
        sys.exit(0)

    if args.validate_only:
        validate_all_links(args.dir, verbose=args.verbose)
        validate_yaml_relative_paths(args.dir)
        validate_yaml_relative_paths(args.dir)
        check_citation_consistency(args.dir, cleanup=args.cleanup_uncited)
    elif args.fix_only:
        sync_all_links(args.dir)
