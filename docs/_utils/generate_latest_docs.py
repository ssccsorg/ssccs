#!/usr/bin/env python3
"""
Generate _include/latest_docs.qmd with the 10 most recently modified documents.

Called from build.yml's pre_build section. Uses git history to determine
the last modification time of each tracked .qmd/.md file, then writes a
compact Markdown list sorted newest-first.

Exclude patterns are kept in sync with build.yml's 'exclude' list.
"""

import fnmatch
import subprocess
import sys
from pathlib import Path

DOCS_ROOT = Path(__file__).parent.parent
INCLUDE_DIR = DOCS_ROOT / "_include"
OUTPUT = INCLUDE_DIR / "_updated_docs_list.qmd"
ITEM_LENGTH = 6


def _ensure_git_safe() -> None:
    """Mark the repo root as safe (handles CI owner mismatch) without calling git first."""
    # Register parent (``/work`` in Docker CI) — avoids the fatal git-rev-parse error
    parent = str(DOCS_ROOT.parent.resolve())
    subprocess.run(
        ["git", "config", "--global", "--add", "safe.directory", parent],
        capture_output=True,
        text=True,
    )
    # Walk up to find .git and register it too (covers edge cases)
    candidate = DOCS_ROOT.resolve()
    for _ in range(5):
        if (candidate / ".git").is_dir():
            if str(candidate) != parent:
                subprocess.run(
                    [
                        "git",
                        "config",
                        "--global",
                        "--add",
                        "safe.directory",
                        str(candidate),
                    ],
                    capture_output=True,
                    text=True,
                )
            break
        candidate = candidate.parent


# Mirror of build.yml exclude patterns (only those affecting .qmd/.md files)
EXCLUDE_PATTERNS = [
    "**/README.md",
    "**/*.llms.md",
    "**/llms.txt",
    "**/_include/",
    "**/_extensions/",
    "**/_utils/",
    "**/*_output/",
    "**/*_files/",
    "**/*_cached/",
    "**/*_libs/",
]


def matches_exclude(rel_path: str) -> bool:
    """Check whether a relative doc path matches any exclude pattern."""
    parts = rel_path.split("/")
    for pattern in EXCLUDE_PATTERNS:
        # Directory-only pattern (trailing slash)
        if pattern.endswith("/"):
            # Strip ``**/`` prefix before matching individual components
            dir_pat = pattern.rstrip("/")
            if dir_pat.startswith("**/"):
                dir_pat = dir_pat[3:]
            for part in parts[:-1]:  # all path components except filename
                if fnmatch.fnmatch(part, dir_pat):
                    return True
            continue

        # Full-path match
        if fnmatch.fnmatch(rel_path, pattern):
            return True

        # **/ prefix → match suffix
        if pattern.startswith("**/"):
            sub = pattern[3:]
            for i in range(len(parts)):
                suffix = "/".join(parts[i:])
                if fnmatch.fnmatch(suffix, sub):
                    return True

        # Simple filename (no slash) → match at any level
        if "/" not in pattern and fnmatch.fnmatch(parts[-1], pattern):
            return True

        # /** suffix → match prefix as directory
        if pattern.endswith("/**"):
            prefix = pattern[:-3]
            if rel_path.startswith(prefix + "/"):
                return True

    return False


def get_tracked_doc_files() -> list[tuple[str, str]]:
    """
    Return list of (iso_timestamp, relative_path) for every tracked
    .qmd / .md under docs/, newest first.

    Uses `git log --diff-filter=AM --name-only --pretty=format:%ai`
    to collect the timestamp of every commit that added or modified a
    doc file.  Later commits override earlier ones for the same path,
    giving us the *last* modification time of each file.
    """
    _ensure_git_safe()
    result = subprocess.run(
        [
            "git",
            "log",
            "--diff-filter=AM",
            "--name-only",
            "--pretty=format:%ai  %s",
            "--",
            "*.qmd",
            "*.md",
        ],
        cwd=DOCS_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(
            f"git log failed (exit {result.returncode}): {result.stderr}",
            file=sys.stderr,
        )
        return []

    # Parse the output into (timestamp, path) pairs
    # Format:
    #   2026-05-04 18:15:09 +0200  commit subject
    #   docs/path/file.qmd
    #   docs/path/other.md
    entries: list[tuple[str, str]] = []
    current_ts: str | None = None

    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        # Detect timestamp line (starts with YYYY-MM-DD)
        if line[0:4].isdigit() and line[4] == "-":
            current_ts = line.split("  ")[0]  # keep "2026-05-04 18:15:09 +0200"
            continue
        # Otherwise it's a file path
        if current_ts and line.startswith("docs/"):
            rel = line[len("docs/") :]  # strip leading "docs/"
            # Keep only .qmd / .md (should be redundant, but safe)
            if not (rel.endswith(".qmd") or rel.endswith(".md")):
                continue
            if matches_exclude(rel):
                continue
            entries.append((current_ts, rel))

    # Deduplicate by path keeping the most recent (last seen) timestamp.
    # Since git log outputs newest-first, the first occurrence of each
    # path already has the latest timestamp.
    seen: set[str] = set()
    deduped: list[tuple[str, str]] = []
    for ts, path in entries:
        if path not in seen:
            seen.add(path)
            deduped.append((ts, path))

    # deduped is already newest-first because git log is newest-first
    return deduped


def extract_title_from_file(abs_path: Path) -> str | None:
    """
    Read a .qmd/.md file and return its best available title:

    1. YAML frontmatter ``title:`` field (strips surrounding quotes)
    2. First ATX level-1 heading (``# Heading``)
    3. ``None`` if neither exists
    """
    try:
        text = abs_path.read_text(encoding="utf-8")
    except Exception:
        return None

    # ── 1. YAML frontmatter ──
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            yaml_block = text[3:end]
            for line in yaml_block.splitlines():
                # Match ``title: "..."`` or ``title: ...``
                stripped = line.strip()
                if stripped.startswith("title:"):
                    raw = stripped[len("title:") :].strip()
                    # Strip surrounding single/double quotes
                    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in ('"', "'"):
                        raw = raw[1:-1]
                    if raw:
                        return raw

    # ── 2. First ATX h1 heading ──
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# ") and not stripped.startswith("## "):
            return stripped[2:].strip()

    return None


def format_title(rel_path: str, docs_root: Path) -> str:
    """
    Derive a human-readable title for a document.

    Priority:
    1. YAML frontmatter ``title``
    2. First ``# Heading``
    3. Fallback: path-based heuristic (index \u2192 parent dir name, else filename stem)
    """
    abs_path = docs_root / rel_path
    title = extract_title_from_file(abs_path)
    if title:
        return title

    # Fallback: path-based heuristic
    p = Path(rel_path)
    stem = p.stem
    if stem.lower() == "index":
        title = p.parent.name
    else:
        title = stem
    title = title.replace("_", " ").replace("-", " ").strip()
    return " ".join(w.capitalize() for w in title.split())


def breadcrumb(rel_path: str, title: str) -> str:
    """Return a capitalized path breadcrumb like ``Projects > Nexus > ``.

    If the title matches the immediate parent directory name (case-insensitive),
    that parent is omitted to avoid redundancy (e.g. ``Projects > Nexus > Nexus``
    becomes ``Projects > ``).

    Root-level files return an empty string.
    """
    parts = Path(rel_path).parts
    if len(parts) <= 1:
        return ""

    parents = list(parts[:-1])
    # Skip the last parent if it's just the title repeated
    if parents:
        last = parents[-1].replace("_", " ").replace("-", " ").strip()
        if title.replace(" ", "").lower() == last.replace(" ", "").lower():
            parents = parents[:-1]

    if not parents:
        return ""
    crumbs = " > ".join(
        p.replace("_", " ").replace("-", " ").strip().title() for p in parents
    )
    return f"{crumbs} > "


def get_creation_dates() -> dict[str, str]:
    """
    Return {rel_path: creation_date} for every .qmd/.md file ever created (Added).

    Uses ``git log --diff-filter=A``.  Only the date portion (``YYYY-MM-DD``)
    is kept so it can be compared directly with modification dates.
    """
    _ensure_git_safe()
    result = subprocess.run(
        [
            "git",
            "log",
            "--diff-filter=A",
            "--name-only",
            "--pretty=format:%ai",
            "--",
            "*.qmd",
            "*.md",
        ],
        cwd=DOCS_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return {}

    created: dict[str, str] = {}
    current_ts: str | None = None

    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        if line[0:4].isdigit() and line[4] == "-":
            current_ts = line.split("  ")[0]
            continue
        if current_ts and line.startswith("docs/"):
            rel = line[len("docs/") :]
            if not (rel.endswith(".qmd") or rel.endswith(".md")):
                continue
            if rel not in created:  # keep earliest (first creation)
                created[rel] = current_ts.split()[0]  # date only

    return created


def is_new_file(rel_path: str, creation_dates: dict[str, str]) -> bool:
    """A file is "new" if its first creation was within the last 7 days."""
    from datetime import datetime

    # Shallow clone guard: if every tracked file has the same creation date,
    # the repo was likely cloned with --depth=1 — skip new-file badges entirely.
    if creation_dates:
        dates = list(creation_dates.values())
        if len(dates) >= 5 and len(set(dates)) == 1:
            return False

    creation = creation_dates.get(rel_path)
    if not creation:
        return False
    try:
        created = datetime.strptime(creation, "%Y-%m-%d")
        return (datetime.now() - created).days <= 7
    except ValueError:
        return False


def badge_new() -> str:
    """Return an inline HTML badge for "new" indicator."""
    return '<sup style="background:#2c8;color:#fff;font-size:.65em;padding:0 .4em;border-radius:3px;">N</sup>'


def doc_to_html(rel_path: str) -> str:
    """Map a .qmd/.md relative path to its .html output path."""
    p = Path(rel_path)
    stem = p.stem
    if stem.lower() == "index":
        # docs/foo/index.qmd → foo/index.html → foo/
        # but keep trailing / for directory-index
        parent = str(p.parent)
        if parent == ".":
            return "index.html"
        return f"{parent}/index.html"
    else:
        return str(p.with_suffix(".html"))


def main() -> None:
    files = get_tracked_doc_files()
    creation_dates = get_creation_dates()
    top = files[:ITEM_LENGTH]

    # Sort: new files first, then rest — each group sorted newest-first
    new = [(ts, p) for ts, p in top if is_new_file(p, creation_dates)]
    old = [(ts, p) for ts, p in top if not is_new_file(p, creation_dates)]
    sorted_items = new + old  # each group already newest-first from git log

    INCLUDE_DIR.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT, "w") as f:
        if sorted_items:
            f.write("\n| Updated | Document |\n")
            f.write("|----------|---------|\n")
            for ts, rel_path in sorted_items:
                date = ts.split()[0]  # "2026-05-04"
                title = format_title(rel_path, DOCS_ROOT)
                path_prefix = breadcrumb(rel_path, title)
                html = doc_to_html(rel_path)
                badge = (
                    f" {badge_new()}" if is_new_file(rel_path, creation_dates) else ""
                )
                f.write(f"| {date} | {path_prefix}[{title}]({html}){badge} |\n")

    print(f"Generated {OUTPUT} with {len(top)} entries.")


if __name__ == "__main__":
    main()
