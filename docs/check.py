#!/usr/bin/env python3
"""
SSCCS Link Verifier & Corrector

Usage:
    ./check.py # Edit source link + verify
    ./check.py --fix-only # Only perform fixes
    ./check.py --validate-only # Perform verification only
"""

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
VALID_EXTENSIONS = {".md", ".qmd", ".yml", ".yaml", ".json"}
SOURCE_EXTENSIONS = {".qmd", ".md", ".rs", ".py", ".yml", ".yaml", ".json", ".toml"}
IGNORE_FILES = {"README.md"}
IGNORE_URL_PATTERNS = [
    "*keys.openpgp.org*",
    "*doi.org*",
    "*?token=*",
]


# ============================================================
# Helper functions
# ============================================================
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
      - .html links: valid if corresponding .qmd/.md exists.
      - directory/ links: valid if directory contains index.qmd/index.md.
      - bare names (no extension, no trailing slash): valid only if a .qmd/.md
        file of that exact name exists (otherwise broken).
    """
    # List of possible source subdirectories (e.g., 'docs', 'content')
    source_subdirs = ['', 'docs', 'src', 'content']

    def check_exact_file(base: Path) -> bool:
        """Check if base.qmd or base.md exists."""
        return (base.with_suffix('.qmd').exists() or 
                base.with_suffix('.md').exists())

    def check_directory_index(dir_path: Path) -> bool:
        """Check if dir_path/index.qmd or index.md exists."""
        return ((dir_path / 'index.qmd').exists() or 
                (dir_path / 'index.md').exists())

    # Normalize the link (remove fragment/query)
    clean = link_path.split('#')[0].split('?')[0]

    # Determine if the link ends with .html or a trailing slash
    is_html = clean.endswith('.html')
    is_dir_slash = clean.endswith('/')

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
            # .html link: look for .qmd/.md with same name
            if check_exact_file(target.with_suffix('')):
                return True
        elif is_dir_slash:
            # Directory link (ends with /): look for index file inside
            if check_directory_index(target):
                return True
        else:
            # Bare name (no .html, no trailing slash): exact .qmd/.md required
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
# Main CLI
# ============================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SSCCS Link Manager")
    parser.add_argument(
        "--fix-only", action="store_true", help="Only fix links (skip validation)"
    )
    parser.add_argument(
        "--validate-only", action="store_true", help="Only validate links"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show detailed validation progress"
    )
    parser.add_argument(
        "--dir", "-d", default="./", help="Target directory (default: ./)"
    )
    args = parser.parse_args()

    if args.validate_only:
        validate_all_links(args.dir, verbose=args.verbose)
    elif args.fix_only:
        sync_all_links(args.dir)
    else:
        # Default: Verify after modification
        sync_all_links(args.dir)
        print("\n" + "=" * 60)
        print(" VALIDATION PHASE")
        print("=" * 60 + "\n")
        validate_all_links(args.dir, verbose=args.verbose)