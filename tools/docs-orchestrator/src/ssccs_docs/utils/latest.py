"""
Generate _include/_updated_docs_list.qmd with the 10 most recently modified
documents.

Derived from docs/_utils/generate_latest_docs.py.
"""

import fnmatch
import re
import subprocess
import logging

import yaml

from datetime import datetime
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

ITEM_LENGTH = 6

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


def _ensure_git_safe(docs_root: Path) -> None:
    """Mark the repo root as safe (handles CI owner mismatch) without calling
    git first."""
    parent = str(docs_root.parent.resolve())
    subprocess.run(
        ["git", "config", "--global", "--add", "safe.directory", parent],
        capture_output=True,
        text=True,
    )
    candidate = docs_root.resolve()
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


def matches_exclude(rel_path: str) -> bool:
    """Check whether a relative doc path matches any exclude pattern."""
    parts = rel_path.split("/")
    for pattern in EXCLUDE_PATTERNS:
        if pattern.endswith("/"):
            dir_pat = pattern.rstrip("/")
            if dir_pat.startswith("**/"):
                dir_pat = dir_pat[3:]
            for part in parts[:-1]:
                if fnmatch.fnmatch(part, dir_pat):
                    return True
            continue

        if fnmatch.fnmatch(rel_path, pattern):
            return True

        if pattern.startswith("**/"):
            sub_pat = pattern[3:]
            for i in range(len(parts)):
                suffix = "/".join(parts[i:])
                if fnmatch.fnmatch(suffix, sub_pat):
                    return True

        if "/" not in pattern and fnmatch.fnmatch(parts[-1], pattern):
            return True

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
    if raw.startswith("docs/"):
        rel = raw[len("docs/"):]
    else:
        rel = raw

    if not (rel.endswith(".qmd") or rel.endswith(".md")):
        return None
    if rel.startswith("../") or rel.startswith("/"):
        return None
    return rel


def _is_timestamp_line(line: str) -> bool:
    """Return True if *line* looks like a git iso-stamp line."""
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
        if current_ts is None:
            continue
        rel = _normalise_path(line)
        if rel is None:
            continue
        if matches_exclude(rel):
            continue
        entries.append((current_ts, rel))

    seen: set[str] = set()
    deduped: list[tuple[str, str]] = []
    for ts, path in entries:
        if path not in seen:
            seen.add(path)
            deduped.append((ts, path))

    return deduped


def _get_current_doc_paths(docs_root: Path) -> set[str]:
    """Return the set of doc-relative paths currently tracked by git."""
    _ensure_git_safe(docs_root)
    result = subprocess.run(
        ["git", "ls-files", "--", "*.qmd", "*.md"],
        cwd=docs_root,
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
    """Remap each entry's path to its current git-tracked location."""
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

    seen: set[str] = set()
    deduped: list[tuple[str, str]] = []
    for ts, path in resolved:
        if path not in seen:
            seen.add(path)
            deduped.append((ts, path))
    return deduped


def get_tracked_doc_files(docs_root: Path) -> list[tuple[str, str]]:
    """
    Return list of (iso_timestamp, relative_path) for every tracked
    .qmd / .md under docs/, newest first.
    """
    _ensure_git_safe(docs_root)
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
        cwd=docs_root,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        logger.error("git log failed (exit %s): %s", result.returncode, result.stderr)
        return []

    current_paths = _get_current_doc_paths(docs_root)
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

    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            yaml_block = text[3:end]
            for line in yaml_block.splitlines():
                stripped = line.strip()
                if stripped.startswith("title:"):
                    raw = stripped[len("title:"):].strip()
                    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in ('"', "'"):
                        raw = raw[1:-1]
                    if raw:
                        return raw

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
    3. Fallback: path-based heuristic (index -> parent dir name, else filename stem)
    """
    abs_path = docs_root / rel_path
    title = extract_title_from_file(abs_path)
    if title:
        return title

    p = Path(rel_path)
    stem = p.stem
    if stem.lower() == "index":
        title = p.parent.name
    else:
        title = stem
    title = title.replace("_", " ").replace("-", " ").strip()
    return " ".join(w.capitalize() for w in title.split())


def breadcrumb(rel_path: str, title: str) -> str:
    """Return a capitalized path breadcrumb like ``Projects > Nexus > ``."""
    parts = Path(rel_path).parts
    if len(parts) <= 1:
        return ""

    parents = list(parts[:-1])
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


def get_creation_dates(docs_root: Path) -> dict[str, str]:
    """
    Return {rel_path: creation_date} for every current doc file.
    """
    _ensure_git_safe(docs_root)
    current_paths = _get_current_doc_paths(docs_root)
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
        cwd=docs_root,
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
def _latest_commit_date(docs_root: Path) -> str | None:
    """Return the date (YYYY-MM-DD) of the most recent commit in docs/."""
    _ensure_git_safe(docs_root)
    result = subprocess.run(
        ["git", "log", "-1", "--pretty=format:%ai", "--", "."],
        cwd=docs_root,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return result.stdout.strip().split()[0]


def is_new_file(
    rel_path: str, creation_dates: dict[str, str], docs_root: Path
) -> bool:
    """A file is "new" if its first creation was within 7 days of the latest
    commit date (not wall-clock time), making the output deterministic for
    a given repo state."""
    if creation_dates:
        dates = list(creation_dates.values())
        if len(dates) >= 5 and len(set(dates)) == 1:
            return False

    creation = creation_dates.get(rel_path)
    if not creation:
        return False

    ref_date_str = _latest_commit_date(docs_root)
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


def doc_to_html(rel_path: str, docs_root: Path) -> str:
    """Map a .qmd/.md relative path to its absolute site path."""
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
            pass
    return _site_path(p, "html")


def generate_latest_docs(docs_root: Path) -> bool:
    """Generate _include/_updated_docs_list.qmd with the 10 most recently
    modified documents.

    Returns True on success.
    """
    files = get_tracked_doc_files(docs_root)
    creation_dates = get_creation_dates(docs_root)

    new_files = [(ts, p) for ts, p in files if is_new_file(p, creation_dates, docs_root)]
    old_files = [(ts, p) for ts, p in files if not is_new_file(p, creation_dates, docs_root)]
    sorted_items = new_files[:ITEM_LENGTH]
    remaining = ITEM_LENGTH - len(sorted_items)
    if remaining > 0:
        sorted_items += old_files[:remaining]

    new_content = ""
    if sorted_items:
        new_content += '\n::: {tbl-colwidths="[20, 80]"}\n'
        new_content += "\n| Updated | Document |\n"
        new_content += "|----------|---------|\n"
        for ts, rel_path in sorted_items:
            date = ts.split()[0]
            title = format_title(rel_path, docs_root)
            path_prefix = breadcrumb(rel_path, title)
            html = doc_to_html(rel_path, docs_root)
            badge = f" {badge_new()}" if is_new_file(rel_path, creation_dates, docs_root) else ""
            new_content += f"| {date} | {path_prefix}[{title}]({html}){badge} |\n"
        new_content += "\n\n:::"

    include_dir = docs_root / "_include"
    output = include_dir / "_updated_docs_list.qmd"

    include_dir.mkdir(parents=True, exist_ok=True)
    try:
        existing = output.read_text(encoding="utf-8")
    except FileNotFoundError:
        existing = ""

    if new_content != existing:
        output.write_text(new_content, encoding="utf-8")
        logger.info("Updated %s with %s entries.", output, len(sorted_items))
    else:
        logger.info(
            "No change - %s is already up to date (%s entries).",
            output,
            len(sorted_items),
        )

    return True
