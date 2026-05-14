#!/usr/bin/env python3
"""
Generate _include/_updated_docs_list.qmd with the 10 most recently modified
documents.

Called from build.yml's pre_build section. Uses git history to determine
the last modification time of each tracked .qmd/.md file, then writes a
compact Markdown list sorted newest-first.

The script only overwrites the output file when the generated content
differs from what is already on disk, avoiding spurious git diffs.

Exclude patterns are kept in sync with build.yml's 'exclude' list.
"""

import fnmatch
import re
import subprocess
import sys

import yaml

from datetime import datetime
from functools import lru_cache
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


def _normalise_path(raw: str) -> str | None:
    """Convert a git-log file path to a docs-relative path.

    Git may output paths relative to the repo root (``docs/index.qmd``)
    or relative to the cwd (``index.qmd``).  This helper accepts both
    forms and always returns the docs-relative form without the leading
    ``docs/`` prefix, or ``None`` if the path is outside docs/.
    """
    # Strip leading docs/ prefix if present (git output relative to repo root)
    if raw.startswith("docs/"):
        rel = raw[len("docs/") :]
    else:
        # Path is already relative to docs/ (git output relative to cwd)
        rel = raw

    if not (rel.endswith(".qmd") or rel.endswith(".md")):
        return None
    # Reject paths that escape docs/ (e.g. ../README.md)
    if rel.startswith("../") or rel.startswith("/"):
        return None
    return rel


def _is_timestamp_line(line: str) -> bool:
    """Return True if *line* looks like a git iso-stamp line.

    Matches ``YYYY-MM-DD HH:MM:SS ±HHMM`` at the start of the string.
    This is stricter than just checking ``line[0:4].isdigit()`` and
    avoids false-positives on commit subjects that happen to start with
    a date-like token.
    """
    # 19 chars covers "2026-05-04 18:15:09"
    if len(line) < 19:
        return False
    head = line[:19]
    return (
        head[0:4].isdigit()
        and head[4] == "-"
        and head[5:7].isdigit()
        and head[7] == "-"
        and head[8:10].isdigit()
        and head[10] == " "
        and head[11:13].isdigit()
        and head[13] == ":"
        and head[14:16].isdigit()
        and head[16] == ":"
        and head[17:19].isdigit()
    )


def _parse_git_log_nameonly(stdout: str) -> list[tuple[str, str]]:
    """Parse ``git log --name-only`` output into (timestamp, rel_path) pairs."""
    entries: list[tuple[str, str]] = []
    current_ts: str | None = None

    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        if _is_timestamp_line(line):
            current_ts = line.split("  ")[0] if "  " in line else line[:25].rstrip()
            continue
        # File path line
        if current_ts is None:
            continue
        rel = _normalise_path(line)
        if rel is None:
            continue
        if matches_exclude(rel):
            continue
        entries.append((current_ts, rel))

    # Deduplicate by path, keeping the first (newest) occurrence.
    # git log outputs newest-first, so the first entry per path is the latest.
    seen: set[str] = set()
    deduped: list[tuple[str, str]] = []
    for ts, path in entries:
        if path not in seen:
            seen.add(path)
            deduped.append((ts, path))

    return deduped


def _get_current_doc_paths() -> set[str]:
    """Return the set of doc-relative paths currently tracked by git.

    Uses ``git ls-files`` which reflects the authoritative current state,
    so renamed files only appear at their current location.
    """
    _ensure_git_safe()
    result = subprocess.run(
        ["git", "ls-files", "--", "*.qmd", "*.md"],
        cwd=DOCS_ROOT,
        capture_output=True,
        text=True,
    )
    paths: set[str] = set()
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        rel = _normalise_path(line)
        if rel and not matches_exclude(rel):
            paths.add(rel)
    return paths


def _resolve_to_current_paths(
    entries: list[tuple[str, str]], current_paths: set[str]
) -> list[tuple[str, str]]:
    """Remap each entry's path to its current git-tracked location.

    When a file was renamed, ``git log --diff-filter=AM`` only knows
    the old path.  This maps old paths to current paths by matching
    the filename, so the generated link always points to the live
    location.
    """
    fname_to_current: dict[str, str] = {}
    for cp in current_paths:
        fname = Path(cp).name
        fname_to_current[fname] = cp

    resolved: list[tuple[str, str]] = []
    for ts, path in entries:
        if path in current_paths:
            resolved.append((ts, path))
        else:
            cur = fname_to_current.get(Path(path).name)
            if cur is not None:
                resolved.append((ts, cur))

    # After remapping old paths to current paths, multiple entries may
    # resolve to the same current path (e.g. after a rename).  Since
    # entries are newest-first, keep only the first occurrence per path.
    seen: set[str] = set()
    deduped: list[tuple[str, str]] = []
    for ts, path in resolved:
        if path not in seen:
            seen.add(path)
            deduped.append((ts, path))
    return deduped


def get_tracked_doc_files() -> list[tuple[str, str]]:
    """
    Return list of (iso_timestamp, relative_path) for every tracked
    .qmd / .md under docs/, newest first.

    Uses ``git log -n 100 --diff-filter=AM --name-only --pretty=format:%ai``
    to collect the timestamp of every commit that added or modified a
    doc file.  Later commits override earlier ones for the same path,
    giving us the *last* modification time of each file.

    The commit subject is deliberately omitted from the format string
    to avoid false parsing when a subject happens to start with
    ``docs/`` or a date-like token.
    """
    _ensure_git_safe()
    result = subprocess.run(
        [
            "git",
            "log",
            "-n", "100",
            "--diff-filter=AM",
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
        print(
            f"git log failed (exit {result.returncode}): {result.stderr}",
            file=sys.stderr,
        )
        return []

    current_paths = _get_current_doc_paths()
    return _resolve_to_current_paths(
        _parse_git_log_nameonly(result.stdout), current_paths
    )


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
    Return {rel_path: creation_date} for every current doc file.

    Uses a single ``git log --diff-filter=A --name-only`` call across
    all files.  Much faster than per-file ``git log``.
    """
    _ensure_git_safe()
    current_paths = _get_current_doc_paths()
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
        if _is_timestamp_line(line):
            current_ts = line.split()[0]
            continue
        if current_ts is None:
            continue
        rel = _normalise_path(line)
        if rel and rel in current_paths and rel not in created:
            created[rel] = current_ts

    return created


@lru_cache(maxsize=1)
def _latest_commit_date() -> str | None:
    """Return the date (YYYY-MM-DD) of the most recent commit in docs/."""
    _ensure_git_safe()
    result = subprocess.run(
        ["git", "log", "-1", "--pretty=format:%ai", "--", "."],
        cwd=DOCS_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return result.stdout.strip().split()[0]


def is_new_file(rel_path: str, creation_dates: dict[str, str]) -> bool:
    """A file is "new" if its first creation was within 7 days of the latest
    commit date (not wall-clock time), making the output deterministic for
    a given repo state."""
    # Shallow clone guard: if every tracked file has the same creation date,
    # the repo was likely cloned with --depth=1 — skip new-file badges entirely.
    if creation_dates:
        dates = list(creation_dates.values())
        if len(dates) >= 5 and len(set(dates)) == 1:
            return False

    creation = creation_dates.get(rel_path)
    if not creation:
        return False

    ref_date_str = _latest_commit_date()
    if not ref_date_str:
        return False

    try:
        created = datetime.strptime(creation, "%Y-%m-%d")
        ref_date = datetime.strptime(ref_date_str, "%Y-%m-%d")
        return (ref_date - created).days <= 7
    except ValueError:
        return False


def badge_new() -> str:
    """Return an inline HTML badge for "new" indicator."""
    return '<sup style="background:#2c8;color:#fff;font-size:.65em;padding:0 .4em;border-radius:3px;">N</sup>'


def _site_path(p: Path, ext: str) -> str:
    """Build a site-root-absolute path from a relative file path and extension."""
    stem = p.stem
    if stem.lower() == "index":
        parent = str(p.parent)
        if parent == ".":
            return f"/index.{ext}"
        return f"/{parent}/index.{ext}"
    return f"/{p.with_suffix('.' + ext)}"


def doc_to_html(rel_path: str, docs_root: Path = DOCS_ROOT) -> str:
    """Map a .qmd/.md relative path to its absolute site path.

    For beamer-only documents (no html format declared), links to
    the PDF output instead, since no HTML output is generated.
    """
    p = Path(rel_path)
    abs_path = docs_root / rel_path
    if abs_path.suffix == ".qmd":
        try:
            text = abs_path.read_text(encoding="utf-8", errors="ignore")
            fm = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
            if fm:
                front = yaml.safe_load(fm.group(1)) or {}
                fmt = front.get("format", {})
                if isinstance(fmt, dict):
                    if "beamer" in fmt and "html" not in fmt:
                        return _site_path(p, "pdf")
        except Exception:
            # Best-effort parse only: on read/front-matter parse errors,
            # fall back to the default HTML path mapping below.
            pass
    return _site_path(p, "html")


def main() -> None:
    files = get_tracked_doc_files()
    creation_dates = get_creation_dates()

    # New files always come first (preserved for 7 days), then
    # fill remaining slots with the most recently modified old files.
    new_files = [(ts, p) for ts, p in files if is_new_file(p, creation_dates)]
    old_files = [(ts, p) for ts, p in files if not is_new_file(p, creation_dates)]
    # new_files already newest-first from git log; take up to ITEM_LENGTH
    sorted_items = new_files[:ITEM_LENGTH]
    # Fill remaining slots with old files
    remaining = ITEM_LENGTH - len(sorted_items)
    if remaining > 0:
        sorted_items += old_files[:remaining]

    # Build output in memory first so we can compare with on-disk content
    new_content = ""
    if sorted_items:
        new_content += '\n::: {tbl-colwidths="[20, 80]"}\n'
        new_content += "\n| Updated | Document |\n"
        new_content += "|----------|---------|\n"
        for ts, rel_path in sorted_items:
            date = ts.split()[0]  # "2026-05-04"
            title = format_title(rel_path, DOCS_ROOT)
            path_prefix = breadcrumb(rel_path, title)
            html = doc_to_html(rel_path)
            badge = f" {badge_new()}" if is_new_file(rel_path, creation_dates) else ""
            new_content += f"| {date} | {path_prefix}[{title}]({html}){badge} |\n"
        new_content += "\n\n:::"

    # Only overwrite when content actually differs (avoids spurious git diffs)
    INCLUDE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        existing = OUTPUT.read_text(encoding="utf-8")
    except FileNotFoundError:
        existing = ""

    if new_content != existing:
        OUTPUT.write_text(new_content, encoding="utf-8")
        print(f"Updated {OUTPUT} with {len(sorted_items)} entries.")
    else:
        print(
            f"No change – {OUTPUT} is already up to date ({len(sorted_items)} entries)."
        )


if __name__ == "__main__":
    main()
