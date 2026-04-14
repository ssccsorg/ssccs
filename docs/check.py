#!/usr/bin/env python3
"""
SSCCS Docs Checker

Usage:
    ./check.py # Edit source link + verify
    ./check.py --fix-only # Only perform fixes
    ./check.py --validate-only # Perform verification only
"""

# Additional command for citation consistency check:
#     ./check.py --check-citations # Check citation consistency between .qmd/.md and .bib files

import os
import re
import sys
import time
import requests
from pathlib import Path
from urllib.parse import urlparse
from typing import Dict, List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import fnmatch
import threading

# ============================================================
# Configuration
# ============================================================
IGNORED_DIRS = {
    ".venv",
    ".git",
    "_site",
    ".quarto",
    "node_modules",
    "__pycache__",
    "_cached",
}
VALID_EXTENSIONS = {".md", ".qmd", ".yml", ".yaml", ".json", ".bib"}
SOURCE_EXTENSIONS = {".qmd", ".md", ".rs", ".py", ".yml", ".yaml", ".json", ".toml", ".bib"}
IGNORE_FILES = {"README.md"}
IGNORE_URL_PATTERNS = [
    "*keys.openpgp.org*",
    "*doi.org*",
    "*?token=*",
]


# ============================================================
# Helper functions
# ============================================================
def extract_bibtex_citation_keys(content: str) -> set:
    """
    Extract all citation keys from a BibTeX file.
    Returns a set of citation keys.
    """
    keys = set()
    # Match @type{key, ...} pattern
    citation_pattern = re.compile(r'@\w+\s*\{\s*([^,\s]+)\s*,', re.IGNORECASE)
    for match in citation_pattern.finditer(content):
        keys.add(match.group(1).strip())
    return keys


def extract_quarto_citation_keys(content: str) -> set:
    """
    Extract all citation keys from Quarto/Markdown content.
    Matches @key, [@key], [@key1; @key2], etc.
    Returns a set of citation keys.
    
    Excludes common Quarto/Pandoc variables that use @ syntax.
    """
    keys = set()
    # Common Quarto/Pandoc variables that are NOT BibTeX citations
    excluded_keys = {
        'title', 'subtitle', 'author', 'date', 'abstract', 'keywords',
        'affiliation', 'correspondence', 'acknowledgements', 'references',
        'maketitle', 'ssccs',  # Project-specific variables
    }
    
    # Match @key pattern (with optional brackets and multiple keys)
    # Handles: @key, [@key], [@key1; @key2], [-@key] for negative citations
    # Require at least one digit or colon in the key to match typical BibTeX keys (e.g., author2024, doi:xxx)
    citation_pattern = re.compile(r'@([a-zA-Z][a-zA-Z0-9_:\-]*[0-9:][a-zA-Z0-9_:\-]*)')
    for match in citation_pattern.finditer(content):
        key = match.group(1).strip()
        if key.lower() not in excluded_keys:
            keys.add(key)
    return keys


def extract_yaml_frontmatter_links(content: str) -> List[Tuple[str, int]]:
    """
    Extract links from YAML frontmatter in .qmd and .md files.
    Returns list of (url, line_number) tuples.
    """
    links = []
    # Check if content starts with YAML frontmatter delimiter
    if not content.startswith("---"):
        return links
    
    # Find the end of frontmatter
    lines = content.split('\n')
    frontmatter_end = 0
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            frontmatter_end = i
            break
    
    if frontmatter_end == 0:
        return links
    
    # Parse frontmatter for URLs
    url_pattern = re.compile(r'^(?:\s*[-\w]+:\s*)?(https?://[^\s\'"]+|[^\s\'"]+\.(?:pdf|html|md|qmd|bib))', re.MULTILINE)
    for i, line in enumerate(lines[:frontmatter_end + 1], start=1):
        # Look for URL patterns in YAML values
        # Match common YAML patterns: key: value, - list_item, etc.
        matches = re.findall(r'(?:^|:\s|-)\s*(https?://[^\s\'"]+|[^\s\'"]+\.(?:pdf|html|md|qmd|bib))(?:\s|$)', line)
        for match in matches:
            url = match.strip()
            if url and not url.startswith('#'):
                links.append((url, i))
    
    return links


def extract_bibtex_links(content: str) -> List[Tuple[str, int]]:
    """
    Extract links from BibTeX entries.
    Looks for url, doi, eprint, and file fields.
    Returns list of (url, line_number) tuples.
    """
    links = []
    lines = content.split('\n')
    
    # Patterns for BibTeX fields that contain links
    url_pattern = re.compile(r'^\s*url\s*=\s*\{?([^}\s]+)\}?\s*,?\s*$')
    doi_pattern = re.compile(r'^\s*doi\s*=\s*\{?([^}\s]+)\}?\s*,?\s*$')
    eprint_pattern = re.compile(r'^\s*eprint\s*=\s*\{?([^}\s]+)\}?\s*,?\s*$')
    file_pattern = re.compile(r'^\s*file\s*=\s*\{?([^}\s]+)\}?\s*,?\s*$')
    
    for i, line in enumerate(lines, start=1):
        for pattern in [url_pattern, doi_pattern, eprint_pattern, file_pattern]:
            match = pattern.match(line)
            if match:
                value = match.group(1).strip()
                if value:
                    # Convert DOI to URL if needed
                    if pattern == doi_pattern and not value.startswith('http'):
                        value = f'https://doi.org/{value}'
                    elif pattern == eprint_pattern and not value.startswith('http'):
                        # arXiv eprint - handle various formats:
                        # "arXiv:1234.5678", "1234.5678", "arXiv:1234.5678 [cs.AI]"
                        arxiv_id = value.replace('arXiv:', '').split()[0].strip()
                        # Validate it looks like an arXiv ID (contains a dot)
                        if '.' in arxiv_id:
                            value = f'https://arxiv.org/abs/{arxiv_id}'
                        # Otherwise, keep original value (might be a local path or other format)
                    links.append((value, i))
    
    return links


def get_std_base(name: str) -> str:
    """
    Standardize file names (snake_case, preserve Korean, maintain _ prefix)
    """
    base = os.path.splitext(name)[0]
    if base.upper() == "README":
        return "README"
    prefix = "_" if base.startswith("_") else ""
    actual = base[1:] if base.startswith("_") else base
    new = actual.lower().replace(" ", "_").replace("-", "_")
    new = re.sub(r"[^a-z0-9_\u1100-\u11FF\uAC00-\uD7AF]", "", new)
    new = re.sub(r"_+", "_", new).strip("_")
    return prefix + new


def build_global_inventory(root_path: Path) -> Dict[str, Path]:
    """
    Build a full document inventory (normalized key -> relative path relative to root)
    """
    inventory = {}
    for ext in (".md", ".qmd"):
        for file_path in root_path.rglob(f"*{ext}"):
            # Skip excluded directories
            if any(
                part in IGNORED_DIRS for part in file_path.relative_to(root_path).parts
            ):
                continue
            key = get_std_base(file_path.name)
            rel = file_path.relative_to(root_path)
            # Duplicate key processing (add parent folder name)
            if key in inventory:
                parent = file_path.parent.name
                key = f"{parent}_{key}"
            inventory[key] = rel
    return inventory


def is_likely_shortcode(content: str, match_start: int) -> bool:
    """Check whether there is a Quarto shortcode or include pattern before the match position"""
    start = max(0, match_start - 30)
    before = content[start:match_start]
    # {{< ... >}} or {% include ... %} or raw include pattern
    if re.search(r"{{<.*?>|{%\s*include|<\s*include", before):
        return True
    return False


def normalize_link_to_absolute(
    link: str, source_file: Path, root: Path, inventory: Dict[str, Path]
) -> Optional[str]:
    """
    Convert links to absolute paths (starting with /) (if referencing source files)
    External links, anchors, emails, etc. are not converted.
    """
    # If it is already an absolute path or an external link, it is returned as is.
    if link.startswith(("http://", "https://", "mailto:", "tel:", "#", "/", "data:")):
        return None

    # Anchor/Query Separation
    anchor = ""
    if "#" in link:
        link, anchor = link.split("#", 1)
        anchor = "#" + anchor
    query = ""
    if "?" in link:
        link, query = link.split("?", 1)
        query = "?" + query

    p = Path(link)
    stem = p.stem
    if not stem:
        return None

    # Make sure it's in your inventory
    if stem not in inventory:
        return None

    target_rel = inventory[stem]
    # Create absolute path relative to root (always starts with /)
    abs_path = "/" + str(target_rel).replace("\\", "/")
    # Determine the extension: .html if the original link is .html, otherwise the actual extension.
    orig_ext = p.suffix.lower()
    if orig_ext == ".html":
        abs_path = Path(abs_path).with_suffix(".html")
    else:
        abs_path = Path(abs_path).with_suffix(target_rel.suffix)
    abs_path = str(abs_path).replace("\\", "/")
    return abs_path + query + anchor


# ============================================================
# Sync function
# ============================================================
def sync_all_links(target_dir: str):
    root = Path(target_dir).resolve()
    if not root.exists():
        print(f"ERROR: {root} does not exist")
        return

    print(f"> Building inventory from {root} ...")
    inventory = build_global_inventory(root)
    print(f"> Indexed {len(inventory)} documents")
    print("-" * 60)

    # Regular expression to find an entire Markdown link: [text](url)
    md_link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
    total_fixed = 0
    processed = 0

    for file_path in root.rglob("*"):
        if file_path.suffix not in VALID_EXTENSIONS:
            continue
        if any(part in IGNORED_DIRS for part in file_path.relative_to(root).parts):
            continue

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"> Cannot read {file_path}: {e}")
            continue

        processed += 1
        new_content = content
        offset = 0  # Cumulative position correction

        for match in md_link_pattern.finditer(content):
            full_link = match.group(0)  # [text](url)
            url = match.group(2)  # url part
            start, end = match.span()

            # Never modify URLs (http, https, etc.)
            if url.startswith(
                ("http://", "https://", "mailto:", "tel:", "#", "ftp://", "file://")
            ):
                continue

            # Link replacement based on inventory (local files only)
            new_url = normalize_link_to_absolute(url, file_path, root, inventory)
            if new_url and new_url != url:
                # Create new link
                text = match.group(1)
                new_full = f"[{text}]({new_url})"
                # Replace content (consider offset)
                new_content = (
                    new_content[: start + offset]
                    + new_full
                    + new_content[end + offset :]
                )
                offset += len(new_full) - len(full_link)
                total_fixed += 1

        if new_content != content:
            file_path.write_text(new_content, encoding="utf-8")
            rel = file_path.relative_to(root)
            print(f"> Fixed: {rel}")

    print("-" * 60)
    print(f"> Processed {processed} files, fixed {total_fixed} links.")


# ============================================================
# Validation function with Quarto awareness
# ============================================================
def should_ignore_url(url: str) -> bool:
    for pattern in IGNORE_URL_PATTERNS:
        if fnmatch.fnmatch(url, pattern):
            return True
    return False

def is_valid_quarto_link(link_path: str, source_file: Path, root: Path) -> bool:
    """
    Return True if `link_path` will exist after Quarto rendering.
    Rules:
      - .html links: valid if corresponding .qmd/.md/.bib exists.
      - directory/ links: valid if directory contains index.qmd/index.md.
      - bare names (no extension, no trailing slash): valid only if a .qmd/.md/.bib
        file of that exact name exists (otherwise broken).
      - .bib links: valid if the .bib file exists.
    """
    # List of possible source subdirectories (e.g., 'docs', 'content')
    source_subdirs = ['', 'docs', 'src', 'content']

    def check_exact_file(base: Path) -> bool:
        """Check if base.qmd, base.md, or base.bib exists."""
        return (base.with_suffix('.qmd').exists() or
                base.with_suffix('.md').exists() or
                base.with_suffix('.bib').exists())

    def check_directory_index(dir_path: Path) -> bool:
        """Check if dir_path/index.qmd or index.md exists."""
        return ((dir_path / 'index.qmd').exists() or 
                (dir_path / 'index.md').exists())

    # Normalize the link (remove fragment/query)
    clean = link_path.split('#')[0].split('?')[0]

    # Determine if the link ends with .html or a trailing slash
    is_html = clean.endswith('.html')
    is_dir_slash = clean.endswith('/')
    
    # Check if link has a known source extension
    known_extensions = {'.qmd', '.md', '.bib'}
    has_known_ext = any(clean.endswith(ext) for ext in known_extensions)

    # Handle absolute paths that start with /docs/ (common repo-root pattern)
    if clean.startswith('/docs/'):
        # Try stripping the /docs/ prefix for docs-rooted validation
        # Use string slicing instead of lstrip to avoid character stripping
        alt_clean = clean[6:]  # len('/docs/') == 6
        return is_valid_quarto_link(alt_clean, source_file, root)
    
    # For each possible source base directory
    for sub in source_subdirs:
        if clean.startswith('/'):
            target = root / sub / clean.lstrip('/')
        else:
            # Relative link: resolve from source file's parent
            target = (source_file.parent / clean).resolve()
            if not str(target).startswith(str(root)):
                continue

        if is_html:
            # .html link: look for .qmd/.md/.bib with same name
            if check_exact_file(target.with_suffix('')):
                return True
        elif is_dir_slash:
            # Directory link (ends with /): look for index file inside
            if check_directory_index(target):
                return True
        elif has_known_ext:
            # Link with known extension: check if file exists directly
            if target.exists():
                return True
        else:
            # Bare name (no .html, no trailing slash): exact .qmd/.md/.bib required
            if check_exact_file(target):
                return True
            # Also try under source subdirectories for absolute links
            for alt_sub in source_subdirs:
                if alt_sub == sub:
                    continue
                alt_target = root / alt_sub / clean.lstrip('/')
                if check_exact_file(alt_target):
                    return True

    return False

def validate_all_links(target_dir: str, verbose: bool = False, max_workers: int = 8):
    root = Path(target_dir).resolve()
    if not root.exists():
        print(f"ERROR: {root} does not exist")
        return

    print(f" Validating links in {root} using {max_workers} threads...")
    print(f"   (ignoring {len(IGNORE_URL_PATTERNS)} URL patterns)")
    print("-" * 60)

    md_link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
    html_link_pattern = re.compile(r'(?:href|src)=["\']([^"\']+)["\']', re.IGNORECASE)

    # List of files to check
    files_to_check = []
    for file_path in root.rglob("*"):
        if file_path.suffix not in VALID_EXTENSIONS:
            continue
        if any(part in IGNORED_DIRS for part in file_path.relative_to(root).parts):
            continue
        if file_path.name in IGNORE_FILES:
            continue
        files_to_check.append(file_path)

    total_files = len(files_to_check)
    broken_local = []
    broken_remote = []
    checked_links = 0
    processed_files = 0
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
                files_done = processed_files
                links_done = checked_links
            elapsed = time.time() - start_time
            with print_lock:
                print(
                    f"\r Files: {files_done}/{total_files} | Links: {links_done} | Time: {elapsed:.1f}s",
                    end="",
                    flush=True,
                )

    reporter_thread = threading.Thread(target=status_reporter, daemon=True)
    reporter_thread.start()

    def process_file(file_path: Path):
        nonlocal processed_files, checked_links
        file_broken_local = []
        file_broken_remote = []
        file_links_checked = 0

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            with data_lock:
                processed_files += 1
            return file_broken_local, file_broken_remote

        links = set()
        for match in md_link_pattern.finditer(content):
            url = match.group(2)
            line = content.count('\n', 0, match.start()) + 1
            links.add((url, line))
        for match in html_link_pattern.finditer(content):
            url = match.group(1)
            line = content.count('\n', 0, match.start()) + 1
            links.add((url, line))
        
        # Extract links from YAML frontmatter for .qmd and .md files
        if file_path.suffix in {".qmd", ".md"}:
            frontmatter_links = extract_yaml_frontmatter_links(content)
            links.update(frontmatter_links)
        
        # Extract links from BibTeX files
        if file_path.suffix == ".bib":
            bibtex_links = extract_bibtex_links(content)
            links.update(bibtex_links)

        for url, line in links:
            if not url or url.startswith(("#", "mailto:", "tel:", "data:")):
                continue
            if should_ignore_url(url):
                continue

            # Skip malformed template literals
            if "{" in url or "[" in url:
                continue

            file_links_checked += 1
            clean_url = url.split("#")[0].split("?")[0]
            parsed = urlparse(url)

            if parsed.scheme in ("http", "https"):
                try:
                    resp = session.head(url, timeout=10, allow_redirects=True)
                    if resp.status_code >= 400:
                        file_broken_remote.append(
                            (file_path.relative_to(root), url, resp.status_code, line)
                        )
                    elif resp.status_code == 200:
                        # Heuristic: check if the page might be an error page
                        # Some servers return 200 for custom 404 pages
                        # Perform a GET request limited to first 1KB
                        try:
                            get_resp = session.get(url, timeout=10, allow_redirects=True, stream=True)
                            get_resp.raise_for_status()
                            # Read first 1024 bytes
                            content = next(get_resp.iter_content(1024)).decode('utf-8', errors='ignore')
                            error_patterns = [
                                r'404\s+not\s+found',
                                r'page\s+not\s+found',
                                r'error\s+404',
                                r'file\s+not\s+found',
                                r'doesn’t\s+exist',
                                r'not\s+found',
                            ]
                            if any(re.search(pattern, content, re.IGNORECASE) for pattern in error_patterns):
                                file_broken_remote.append(
                                    (file_path.relative_to(root), url, "Soft 404", line)
                                )
                        except Exception:
                            # If GET fails, treat as broken
                            file_broken_remote.append(
                                (file_path.relative_to(root), url, "GET failed", line)
                            )
                except Exception:
                    file_broken_remote.append(
                        (file_path.relative_to(root), url, "Connection Error", line)
                    )
            elif clean_url:
                if not is_valid_quarto_link(clean_url, file_path, root):
                    file_broken_local.append(
                        (file_path.relative_to(root), url, "Not Found", line)
                    )

        with data_lock:
            processed_files += 1
            checked_links += file_links_checked

        if verbose:
            with print_lock:
                print(
                    f"\n Processed: {file_path.relative_to(root)} ({file_links_checked} links)"
                )

        return file_broken_local, file_broken_remote

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_file, fp): fp for fp in files_to_check}
        for future in as_completed(futures):
            local, remote = future.result()
            broken_local.extend(local)
            broken_remote.extend(remote)

    running = False
    reporter_thread.join(timeout=2.0)
    print()
    print("-" * 60)

    # Report broken links
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
    print(f"\nValidation finished. Checked {checked_links} links, found {len(broken_local)+len(broken_remote)} broken in {elapsed:.1f}s.")


# ============================================================
# Citation consistency check
# ============================================================
def check_citation_consistency(target_dir: str, cleanup: bool = False):
    """
    Check citation consistency between .qmd/.md files and their associated .bib files.
    Reports:
    - Citations in .qmd/.md that are not in the associated .bib file
    - Entries in .bib files that are not cited in ANY referencing .qmd/.md file
    
    For each .bib file, only checks against .qmd/.md files that explicitly reference it.
    For uncited entries, shows which specific documents DO cite each key.
    """
    root = Path(target_dir).resolve()
    if not root.exists():
        print(f"ERROR: {root} does not exist")
        return
    
    print(f" Checking citation consistency in {root}...")
    print("-" * 60)
    
    # Find all .bib files
    bib_files = {}
    for bib_path in root.rglob("*.bib"):
        if any(part in IGNORED_DIRS for part in bib_path.relative_to(root).parts):
            continue
        bib_files[bib_path] = extract_bibtex_citation_keys(bib_path.read_text(encoding="utf-8"))
    
    # Track which documents reference each bib file, and what keys they cite
    # bib_path -> {doc_path -> set of cited keys}
    bib_to_docs: Dict[Path, Dict[Path, set]] = {bib: {} for bib in bib_files}
    
    # Track citations not found in bibliography
    citation_issues = []
    
    for file_path in root.rglob("*"):
        if file_path.suffix not in {".qmd", ".md"}:
            continue
        if any(part in IGNORED_DIRS for part in file_path.relative_to(root).parts):
            continue
        if file_path.name in IGNORE_FILES:
            continue
        
        content = file_path.read_text(encoding="utf-8")
        
        # Check for bibliography in frontmatter
        bib_match = re.search(r'^---\n.*?bibliography:\s*(.+?)\s*$', content, re.MULTILINE | re.DOTALL)
        if not bib_match:
            continue
        
        bib_refs = bib_match.group(1).strip()
        # Handle multiple bibliographies (YAML list or comma-separated)
        bib_paths = []
        if bib_refs.startswith('['):
            # YAML list format
            for item in re.findall(r'-\s*(.+?)(?:\n|$)', bib_refs):
                bib_paths.append(item.strip())
        else:
            # Single file or comma-separated
            for item in bib_refs.split(','):
                bib_paths.append(item.strip())
        
        # Get all cited keys in this document
        cited_keys_in_doc = extract_quarto_citation_keys(content)
        
        # Process each referenced bib file
        for bib_ref in bib_paths:
            bib_path = (file_path.parent / bib_ref).resolve()
            if bib_path not in bib_files:
                continue
            
            # Register this document as referencing the bib file
            bib_to_docs[bib_path][file_path] = cited_keys_in_doc.copy()
            
            # Check for citations not in bib file
            available_keys = bib_files[bib_path]
            missing = cited_keys_in_doc - available_keys
            for key in missing:
                citation_issues.append((file_path.relative_to(root), bib_path.relative_to(root), key))
    
    # Now compute uncited entries for each bib file
    # Only report if NO keys are cited at all (completely unused bib)
    completely_uncited = {}  # bib_path -> set of uncited keys
    
    for bib_path, docs in bib_to_docs.items():
        if not docs:
            continue  # No documents reference this bib file
        
        available_keys = bib_files[bib_path]
        
        # For each key in the bib, find which documents cite it
        key_to_citing_docs: Dict[str, set] = {key: set() for key in available_keys}
        for doc_path, cited_keys in docs.items():
            for key in cited_keys:
                if key in key_to_citing_docs:
                    key_to_citing_docs[key].add(doc_path)
        
        # Find uncited keys (no document cites them)
        uncited_keys = {key for key, citing_docs in key_to_citing_docs.items() if not citing_docs}
        
        # Check if ANY key is cited
        any_cited = any(citing_docs for citing_docs in key_to_citing_docs.values())
        
        if uncited_keys and not any_cited:
            # No keys are cited at all - error
            completely_uncited[bib_path] = uncited_keys
        # If some keys are cited, do NOT report uncited keys (this is normal)
    
    # Perform cleanup if requested
    if cleanup and completely_uncited:
        print("\n" + "=" * 60)
        print(" CLEANUP PHASE")
        print("=" * 60)
        
        for bib_path, keys in list(completely_uncited.items()):
            rel_bib = bib_path.relative_to(root)
            referencing_docs = bib_to_docs.get(bib_path, {})
            
            if len(referencing_docs) == 1:
                doc_path = list(referencing_docs.keys())[0]
                print(f"\n🧹 Cleaning {rel_bib} (no citations from: {doc_path.relative_to(root)})")
                _remove_bib_entries(bib_path, keys)
                print(f"  Removed {len(keys)} uncited entries from {rel_bib}")
        
        print("\nCleanup complete. Re-run validation to verify.")
    
    # Report issues
    has_issues = citation_issues or completely_uncited
    
    if has_issues and not cleanup:
        print("\n" + "=" * 60)
        print(" CITATION CONSISTENCY ISSUES FOUND")
        print("=" * 60)
        
        if citation_issues:
            print(f"\n📄 Citations not found in bibliography ({len(citation_issues)}):")
            for doc_path, bib_path, key in sorted(citation_issues):
                print(f"  {doc_path}: @{key} (not in {bib_path})")
        
        if completely_uncited:
            total_uncited = sum(len(keys) for keys in completely_uncited.values())
            print(f"\n📚 Bibliography entries not cited ({total_uncited}):")
            for bib_path, keys in sorted(completely_uncited.items()):
                rel_bib = bib_path.relative_to(root)
                referencing_docs = bib_to_docs.get(bib_path, {})
                print(f"  {rel_bib}: {len(keys)} uncited entries (referenced by {len(referencing_docs)} document(s))")
                sample = sorted(keys)[:5]
                for key in sample:
                    print(f"    - @{key}")
                if len(keys) > 5:
                    print(f"    ... and {len(keys) - 5} more")
    
    if not has_issues:
        print("\nAll citations are consistent.")
    
    print(f"\nChecked {len(bib_files)} bibliography files.")


def _remove_bib_entries(bib_path: Path, keys_to_remove: set):
    """Helper function to remove BibTeX entries by key."""
    content = bib_path.read_text(encoding="utf-8")
    lines = content.split('\n')
    new_lines = []
    skip_entry = False
    brace_count = 0
    
    for line in lines:
        entry_match = re.match(r'@\w+\s*\{\s*([^,\s]+)\s*,', line, re.IGNORECASE)
        if entry_match:
            current_entry_key = entry_match.group(1).strip()
            if current_entry_key in keys_to_remove:
                skip_entry = True
                brace_count = line.count('{') - line.count('}')
            else:
                skip_entry = False
        
        if skip_entry:
            brace_count += line.count('{') - line.count('}')
            if brace_count <= 0:
                skip_entry = False
        else:
            new_lines.append(line)
    
    bib_path.write_text('\n'.join(new_lines), encoding="utf-8")


# ============================================================
# Main CLI
# ============================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SSCCS Link Manager")
    parser.add_argument(
        "--fix-only", action="store_true", help="Only fix links (skip validation)"
    )
    parser.add_argument(
        "--validate-only", action="store_true", help="Only validate links (includes citation check)"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show detailed validation progress"
    )
    parser.add_argument(
        "--cleanup-uncited", action="store_true", help="Automatically remove uncited entries from .bib files referenced by only 1 document"
    )
    parser.add_argument(
        "--dir", "-d", default="./", help="Target directory (default: ./)"
    )
    args = parser.parse_args()

    if args.validate_only:
        validate_all_links(args.dir, verbose=args.verbose)
        check_citation_consistency(args.dir, cleanup=args.cleanup_uncited)
    elif args.fix_only:
        sync_all_links(args.dir)
    else:
        # Default: Verify after modification
        sync_all_links(args.dir)
        print("\n" + "=" * 60)
        print(" VALIDATION PHASE")
        print("=" * 60 + "\n")
        validate_all_links(args.dir, verbose=args.verbose)
        print("\n" + "=" * 60)
        print(" CITATION CHECK PHASE")
        print("=" * 60 + "\n")
        check_citation_consistency(args.dir, cleanup=args.cleanup_uncited)