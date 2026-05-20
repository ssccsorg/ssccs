#!/usr/bin/env python3
"""
Resolve broken ``../`` relative asset paths in QMD files.

Reads ``build.yml`` for ``exclude`` patterns (gitignore-style), so it
respects the same exclusion rules as ``build.py`` without depending on it.

Architecture
  Single-file multi-resolver: ``PathResolver`` handles the current
  ``../`` asset-path correction.  Future resolvers can be added as
  additional classes in this file and dispatched from ``main()``.

Usage::

    python resolve.py              # fix broken paths in-place
    python resolve.py --dry-run    # show what would change
    python resolve.py --verbose    # show every file checked
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


# ======================================================================
# _BaseResolver — shared foundation for all resolvers
# ======================================================================
class _BaseResolver:
    """Shared foundation for all resolvers.

    Provides build.yml inheritance, file discovery, path resolution, and
    parallel execution scaffolding.  Subclasses set ``SOURCE_EXTENSIONS``
    and control whether build.yml exclude patterns apply via
    ``_APPLY_BUILD_YML_EXCLUDE``.
    """

    SYSTEM_IGNORED_DIRS: Set[str] = {
        ".venv", ".git", ".quarto", "_site", "_llms",
        "node_modules", "__pycache__", ".*",
    }
    SOURCE_EXTENSIONS: Set[str] = set()  # subclasses MUST set this
    _APPLY_BUILD_YML_EXCLUDE: bool = True
    LOCAL_EXCLUDE: List[str] = []  # per-resolver file patterns (relative to root)

    # ------------------------------------------------------------------
    # build.yml helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _load_build_yml(root: Path) -> Dict[str, object]:
        config_path = root / "build.yml"
        if not config_path.exists():
            return {}
        try:
            import yaml
            with open(config_path, "r") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return {}

    @staticmethod
    def _load_exclude_patterns(root: Path) -> List[str]:
        cfg = _BaseResolver._load_build_yml(root)
        patterns = cfg.get("exclude", [])
        return patterns if isinstance(patterns, list) else []

    @staticmethod
    def _matches_gitignore_pattern(
        rel_path: Path, patterns: List[str]
    ) -> bool:
        """Mirrors ``build.py:matches_gitignore_pattern``."""
        path_str = str(rel_path).replace("\\", "/")
        name = rel_path.name
        for pattern in patterns:
            pattern = pattern.strip()
            if not pattern:
                continue
            is_dir_only = pattern.endswith("/")
            if is_dir_only:
                pattern = pattern[:-1]
                parts = path_str.split("/")
                for i in range(len(parts) - 1):
                    part = parts[i]
                    if fnmatch.fnmatch(part, pattern) or fnmatch.fnmatch(
                        parts[i],
                        pattern.split("/")[-1] if "/" in pattern else pattern,
                    ):
                        return True
                continue
            if fnmatch.fnmatch(path_str, pattern):
                return True
            if "/" not in pattern and "\\" not in pattern:
                if fnmatch.fnmatch(name, pattern):
                    return True
            if pattern.startswith("**/"):
                subpattern = pattern[3:]
                if fnmatch.fnmatch(name, subpattern):
                    return True
                parts = path_str.split("/")
                for i in range(len(parts)):
                    if fnmatch.fnmatch("/".join(parts[i:]), subpattern):
                        return True
            if pattern.endswith("/**"):
                if path_str.startswith(pattern[:-3] + "/"):
                    return True
        return False

    # ------------------------------------------------------------------
    # File filtering and discovery
    # ------------------------------------------------------------------
    def _is_ignored(
        self, file_path: Path, root: Path, exclude_patterns: List[str]
    ) -> bool:
        parts = file_path.relative_to(root).parts
        for part in parts:
            for pattern in self.SYSTEM_IGNORED_DIRS:
                if fnmatch.fnmatch(part, pattern):
                    return True
        if self._APPLY_BUILD_YML_EXCLUDE and exclude_patterns:
            if self._matches_gitignore_pattern(
                file_path.relative_to(root), exclude_patterns
            ):
                return True
        if self.LOCAL_EXCLUDE:
            if self._matches_gitignore_pattern(
                file_path.relative_to(root), self.LOCAL_EXCLUDE
            ):
                return True
        return False

    def discover_files(
        self, root: Path, scan_root: Path, exclude_patterns: List[str]
    ) -> List[Path]:
        return sorted(
            p
            for p in scan_root.rglob("*")
            if p.suffix in self.SOURCE_EXTENSIONS
            and not self._is_ignored(p, root, exclude_patterns)
        )

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _is_url_or_absolute(val: str) -> bool:
        return (
            val.startswith(("http://", "https://", "mailto:", "#"))
            or Path(val).is_absolute()
        )

    @staticmethod
    def _parse_frontmatter(text: str):
        m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
        if not m:
            return None, 0
        try:
            import yaml
            return yaml.safe_load(m.group(1)) or {}, m.end()
        except Exception:
            return None, 0

    @staticmethod
    def _search_upward(
        start_dir: Path, rel: str, root: Path
    ) -> Optional[Path]:
        rel_path = Path(rel)
        parts = rel_path.parts
        for i, part in enumerate(parts):
            if part != "..":
                target = Path(*parts[i:])
                break
        else:
            return None

        cur = start_dir
        while cur >= root:
            candidate = (cur / target).resolve()
            if candidate.exists():
                return candidate
            if cur == root:
                break
            cur = cur.parent
        return None

    @staticmethod
    def _compute_rel_path(from_dir: Path, to_path: Path) -> str:
        from_parts = from_dir.resolve().parts
        to_parts = to_path.resolve().parts
        i = 0
        for a, b in zip(from_parts, to_parts):
            if a != b:
                break
            i += 1
        up = len(from_parts) - i
        down = "/".join(to_parts[i:])
        prefix = "../" * up if up > 0 else "./"
        return f"{prefix}{down}" if down else prefix.rstrip("/")

    # ------------------------------------------------------------------
    # Parallel execution scaffolding
    # ------------------------------------------------------------------
    def _run_fix_all(
        self,
        root: Path,
        scan_root: Path,
        dry_run: bool,
        verbose: bool,
        label: str,
    ) -> Tuple[int, int]:
        exclude_patterns = self._load_exclude_patterns(root)
        files = self.discover_files(root, scan_root, exclude_patterns)

        if not files:
            return 0, 0

        mode = "DRY-RUN" if dry_run else "FIXING"
        print(f"{label} ({mode}) - {len(files)} file(s)\n")

        total_fixes = 0
        processed = 0

        if len(files) <= 1:
            for fp in files:
                n = self.fix_one_file(fp, root, dry_run, verbose)
                if n:
                    total_fixes += n
                processed += 1
        else:
            with ThreadPoolExecutor() as ex:
                futures = {
                    ex.submit(
                        self.fix_one_file, fp, root, dry_run, verbose
                    ): fp
                    for fp in files
                }
                for fut in as_completed(futures):
                    fp = futures[fut]
                    try:
                        n = fut.result()
                    except Exception as e:
                        print(
                            f"  ERROR processing {fp.relative_to(root)}: {e}",
                            file=sys.stderr,
                        )
                        n = 0
                    if n:
                        total_fixes += n
                    processed += 1

        print(f"{'=' * 60}")
        print(f"{label}: processed {processed} file(s), fixed {total_fixes} broken path(s)")
        if dry_run and total_fixes:
            print("(dry-run -- no files were modified)")

        return processed, total_fixes


# ======================================================================
# PathResolver — fix broken ../ relative asset paths
# ======================================================================
class PathResolver(_BaseResolver):
    """Detect and correct ``../`` relative asset paths that broke after a
    ``.qmd`` file was moved.

    Covers:
    * YAML frontmatter: ``metadata-files``, ``bibliography``, ``csl``
    * Jupyter ``%run`` directives inside code cells

    Inherits build.yml exclusion rules as-is: files like ``README.md``
    that are excluded from the build are also excluded from asset-path
    scanning (they contain no ``%run`` directives).
    """

    _APPLY_BUILD_YML_EXCLUDE = True
    SOURCE_EXTENSIONS: Set[str] = {".qmd"}
    PATH_KEYS: Set[str] = {"metadata-files", "bibliography", "csl"}
    RE_RUN = re.compile(r"^\s*%run\s+([^\s#]+)", re.MULTILINE)

    # ------------------------------------------------------------------
    # Extract relative paths from a single file
    # ------------------------------------------------------------------
    def _extract_paths(self, file_path: Path) -> List[Tuple[str, int, int]]:
        results: List[Tuple[str, int, int]] = []
        try:
            text = file_path.read_text(encoding="utf-8")
        except Exception:
            return results

        fm, body_start = self._parse_frontmatter(text)
        if fm and isinstance(fm, dict):
            for key in self.PATH_KEYS:
                vals = fm.get(key)
                if vals is None:
                    continue
                if isinstance(vals, str):
                    vals = [vals]
                if not isinstance(vals, list):
                    continue
                for val in vals:
                    if not isinstance(val, str) or self._is_url_or_absolute(val):
                        continue
                    for m in re.finditer(re.escape(val), text[:body_start]):
                        results.append((val, m.start(), m.end()))

        for m in re.finditer(r"```\{.*?\}\s*\n(.*?)```", text, re.DOTALL):
            cell_body = m.group(1)
            cell_start = m.start(1)
            for run_m in self.RE_RUN.finditer(cell_body):
                run_path = run_m.group(1)
                if self._is_url_or_absolute(run_path):
                    continue
                results.append((
                    run_path,
                    cell_start + run_m.start(1),
                    cell_start + run_m.end(1),
                ))

        return results

    # ------------------------------------------------------------------
    # Fix a single file
    # ------------------------------------------------------------------
    def fix_one_file(
        self, file_path: Path, root: Path, dry_run: bool, verbose: bool
    ) -> int:
        paths = self._extract_paths(file_path)
        if not paths:
            return 0
        try:
            text = file_path.read_text(encoding="utf-8")
        except Exception:
            return 0

        doc_dir = file_path.parent
        fixes: List[Tuple[int, int, str]] = []

        for rel, start, end in paths:
            if (doc_dir / rel).resolve().exists():
                continue
            found = self._search_upward(doc_dir, rel, root)
            if found is None:
                if verbose:
                    print(f"  {file_path.relative_to(root)}: {rel}  -> [NOT FOUND]")
                continue
            new_rel = self._compute_rel_path(doc_dir, found)
            if new_rel == rel:
                continue
            fixes.append((start, end, new_rel))

        if not fixes:
            return 0

        fixes.sort(key=lambda x: x[0], reverse=True)
        new_text = text
        for start, end, new_val in fixes:
            new_text = new_text[:start] + new_val + new_text[end:]

        rel_display = file_path.relative_to(root)
        if dry_run:
            print(f"\n[{rel_display}]")
            for start, end, new_val in sorted(fixes, key=lambda x: x[0]):
                print(f"  - {text[start:end]}")
                print(f"  + {new_val}")
        else:
            try:
                file_path.write_text(new_text, encoding="utf-8")
            except Exception as e:
                print(f"  ERROR writing {rel_display}: {e}", file=sys.stderr)
                return 0
            for start, end, new_val in sorted(fixes, key=lambda x: x[0]):
                print(f"  {rel_display}: {text[start:end]} -> {new_val}")

        return len(fixes)

    # ------------------------------------------------------------------
    # Batch entry point
    # ------------------------------------------------------------------
    def resolve_all(
        self,
        root: Path,
        scan_root: Path,
        dry_run: bool,
        verbose: bool,
    ) -> Tuple[int, int]:
        exclude_patterns = self._load_exclude_patterns(root)
        files = self.discover_files(root, scan_root, exclude_patterns)

        if not files:
            print("No files to check.")
            return 0, 0

        mode = "DRY-RUN" if dry_run else "FIXING"
        print(f"Resolving broken paths ({mode}) — {len(files)} file(s)\n")

        total_fixes = 0
        processed = 0

        if len(files) <= 1:
            for fp in files:
                n = self.fix_one_file(fp, root, dry_run, verbose)
                if n:
                    total_fixes += n
                processed += 1
                if verbose and n == 0:
                    print(f"  {fp.relative_to(root)}: OK")
        else:
            with ThreadPoolExecutor() as ex:
                futures = {
                    ex.submit(self.fix_one_file, fp, root, dry_run, verbose): fp
                    for fp in files
                }
                for fut in as_completed(futures):
                    fp = futures[fut]
                    try:
                        n = fut.result()
                    except Exception as e:
                        print(
                            f"  ERROR processing {fp.relative_to(root)}: {e}",
                            file=sys.stderr,
                        )
                        n = 0
                    if n:
                        total_fixes += n
                    processed += 1

        print(f"\n{'='*60}")
        print(f"Processed {processed} file(s), fixed {total_fixes} broken path(s)")
        if dry_run and total_fixes:
            print("(dry-run – no files were modified)")

        return processed, total_fixes


# ======================================================================
# LinkResolver — fix broken internal markdown links
# ======================================================================
class LinkResolver(_BaseResolver):
    """Detect and correct broken internal markdown links in .qmd and .md
    files.

    Handles links such as ``[text](/docs/file.md)`` where the target file
    has been moved to a different location (e.g., ``direction.md``
    became ``direction/index.md``).

    Extends build.yml exclusion rules: unlike ``PathResolver``, this
    resolver scans ``.md`` files too (including ``README.md``) because
    they contain markdown links that need checking.
    """

    _APPLY_BUILD_YML_EXCLUDE = False
    SOURCE_EXTENSIONS: Set[str] = {".qmd", ".md"}

    # Match [text](path), [text](<path>), [text](path "title"),
    # [text](path 'title')
    RE_LINK = re.compile(r'\[([^\]]*)\]\(([^)]+)\)')

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _clean_url(raw: str) -> str:
        """Extract the bare file path from a markdown link URL, stripping
        ``<>`` angle brackets and trailing ``"title"`` / ``'title'``."""
        url = raw.strip()
        if url.startswith("<") and ">" in url:
            url = url[1:url.index(">")]
        for q in ('"', "'"):
            idx = url.find(q)
            if idx > 0 and url.rstrip().endswith(q):
                url = url[:idx].rstrip()
        return url.strip()

    @staticmethod
    def _skip_link(url: str) -> bool:
        return bool(
            url.startswith(("http://", "https://", "mailto:", "#", "data:"))
        )

    @staticmethod
    def _try_migration(base_dir: Path, rel: str) -> Optional[Path]:
        """Check the ``<stem>/index.<ext>`` migration pattern.

        When ``direction.md`` no longer exists but ``direction/index.md``
        does, this method finds it.
        """
        p = Path(rel)
        stem = p.stem
        ext = p.suffix
        if ext not in (".md", ".qmd"):
            return None
        candidate = (base_dir / stem / f"index{ext}").resolve()
        if candidate.exists():
            return candidate
        alt_ext = ".qmd" if ext == ".md" else ".md"
        candidate = (base_dir / stem / f"index{alt_ext}").resolve()
        if candidate.exists():
            return candidate
        return None

    # ------------------------------------------------------------------
    # Extract markdown links from a single file
    # ------------------------------------------------------------------
    def _extract_links(
        self, file_path: Path
    ) -> List[Tuple[str, int, int]]:
        results: List[Tuple[str, int, int]] = []
        try:
            text = file_path.read_text(encoding="utf-8")
        except Exception:
            return results

        for m in self.RE_LINK.finditer(text):
            raw_url = m.group(2)
            url = self._clean_url(raw_url)
            if not url or self._skip_link(url):
                continue
            if not url.endswith((".md", ".qmd")):
                continue
            results.append((url, m.start(2), m.end(2)))

        return results

    # ------------------------------------------------------------------
    # Resolve a single link to an existing target
    # ------------------------------------------------------------------
    def _resolve_link(
        self, link_path: str, file_dir: Path, root: Path
    ) -> Optional[Tuple[Path, str]]:
        """Try to resolve ``link_path`` to a real file on disk.

        Returns ``(found_abs_path, corrected_link_path)`` if the link
        can be fixed, or ``None`` if it should be left alone.
        """
        if link_path.startswith("/"):
            rel = link_path.lstrip("/")
            if rel.startswith("docs/"):
                rel = rel[5:]
            candidate = (root / rel).resolve()
            if candidate.exists():
                return None
            found = self._try_migration(root, rel)
            if found is not None:
                found_rel = found.relative_to(root)
                new_link = f"/docs/{found_rel}"
                return found, new_link
        else:
            candidate = (file_dir / link_path).resolve()
            if candidate.exists():
                return None
            found = _BaseResolver._search_upward(
                file_dir, link_path, root
            )
            if found is not None:
                new_rel = _BaseResolver._compute_rel_path(
                    file_dir, found
                )
                return found, new_rel
            found = self._try_migration(file_dir, link_path)
            if found is not None:
                new_rel = _BaseResolver._compute_rel_path(
                    file_dir, found
                )
                return found, new_rel

        return None

    # ------------------------------------------------------------------
    # Fix a single file
    # ------------------------------------------------------------------
    def fix_one_file(
        self, file_path: Path, root: Path, dry_run: bool, verbose: bool
    ) -> int:
        links = self._extract_links(file_path)
        if not links:
            return 0

        try:
            text = file_path.read_text(encoding="utf-8")
        except Exception:
            return 0

        doc_dir = file_path.parent
        fixes: List[Tuple[int, int, str]] = []

        for link_path, start, end in links:
            result = self._resolve_link(link_path, doc_dir, root)
            if result is None:
                continue
            found, new_link = result
            if new_link == link_path:
                continue
            fixes.append((start, end, new_link))

        if not fixes:
            return 0

        fixes.sort(key=lambda x: x[0], reverse=True)
        new_text = text
        for start, end, new_val in fixes:
            new_text = new_text[:start] + new_val + new_text[end:]

        rel_display = file_path.relative_to(root)
        if dry_run:
            print(f"\n[{rel_display}]")
            for start, end, new_val in sorted(fixes, key=lambda x: x[0]):
                print(f"  - {text[start:end]}")
                print(f"  + {new_val}")
        else:
            try:
                file_path.write_text(new_text, encoding="utf-8")
            except Exception as e:
                print(
                    f"  ERROR writing {rel_display}: {e}", file=sys.stderr
                )
                return 0
            for start, end, new_val in sorted(fixes, key=lambda x: x[0]):
                print(
                    f"  {rel_display}: {text[start:end]} -> {new_val}"
                )

        return len(fixes)

    # ------------------------------------------------------------------
    # Batch entry point
    # ------------------------------------------------------------------
    def resolve_all(
        self,
        root: Path,
        scan_root: Path,
        dry_run: bool,
        verbose: bool,
    ) -> Tuple[int, int]:
        return self._run_fix_all(
            root, scan_root, dry_run, verbose, "Resolving broken markdown links"
        )


# ======================================================================
# CLI
# ======================================================================
def _run_check_only(
    headers: List[str],
    resolvers: List,
    root: Path,
    scan_root: Path,
    args: argparse.Namespace,
) -> int:
    """Check mode: run all resolvers without modifying files and report
    issues.  Exits with return code 1 if any broken paths are found.
    """
    total_broken = 0
    for name, resolver in zip(headers, resolvers):
        exclude_patterns = PathResolver._load_exclude_patterns(root)
        files = resolver.discover_files(root, scan_root, exclude_patterns)
        if not files:
            continue
        for fp in files:
            n = resolver.fix_one_file(fp, root, dry_run=True, verbose=False)
            if n:
                total_broken += n
    if total_broken:
        print(f"\n{'=' * 60}")
        print(f"FOUND {total_broken} BROKEN PATH(S)")
    else:
        print("All paths valid.")
    return 1 if total_broken else 0


# ======================================================================
# IncludeResolver — ensure _title_meta_items.qmd include is present
# ======================================================================
class IncludeResolver(_BaseResolver):
    """Ensure every ``.qmd`` file includes the title-meta-items template.

    If a ``.qmd`` file has no ``{{< include ... _title_meta_items.qmd >}}``
    directive, inserts one right after the YAML frontmatter, with the
    relative path computed from the file's location.
    """

    _APPLY_BUILD_YML_EXCLUDE = True
    SOURCE_EXTENSIONS: Set[str] = {".qmd"}
    INCLUDE_FILE = "_include/_title_meta_items.qmd"

    RE_INCLUDE = re.compile(
        r"\{\{<\s*include\s+[^>]*_title_meta_items\.qmd\s*>\}\}"
    )

    @staticmethod
    def _is_beamer_only(text: str) -> bool:
        """Return True if the file declares beamer format without html."""
        fm_data, _ = _BaseResolver._parse_frontmatter(text)
        if not fm_data or not isinstance(fm_data, dict):
            return False
        fmt = fm_data.get("format", {})
        if isinstance(fmt, dict):
            return "beamer" in fmt and "html" not in fmt
        return False

    # ------------------------------------------------------------------
    # Fix a single file
    # ------------------------------------------------------------------
    def fix_one_file(
        self, file_path: Path, root: Path, dry_run: bool, verbose: bool
    ) -> int:
        try:
            text = file_path.read_text(encoding="utf-8")
        except Exception:
            return 0

        # Beamer-only documents have no HTML output — no header needed.
        # Remove any existing include so it won't render in beamer PDFs.
        if self._is_beamer_only(text):
            m = self.RE_INCLUDE.search(text)
            if m:
                # Remove the include directive (and trailing newlines)
                new_text = self.RE_INCLUDE.sub("", text, count=1).strip()
                rel_display = file_path.relative_to(root)
                if dry_run:
                    print(f"\n[{rel_display}]")
                    print(f"  - {m.group(0)}")
                    print(f"  + (removed — beamer-only)")
                else:
                    try:
                        file_path.write_text(new_text, encoding="utf-8")
                    except Exception as e:
                        print(f"  ERROR writing {rel_display}: {e}", file=sys.stderr)
                        return 0
                    print(f"  {rel_display}: removed {{< include ... >}} (beamer-only)")
                return 1
            return 0

        # Compute correct relative path from file to _include/_title_meta_items.qmd
        include_abs = (root / self.INCLUDE_FILE).resolve()
        doc_dir = file_path.parent.resolve()
        correct_rel = self._compute_rel_path(doc_dir, include_abs)

        # Check if include already exists with a possibly wrong path
        m = self.RE_INCLUDE.search(text)
        if m:
            existing = m.group(0)
            expected = "{{< include " + correct_rel + " >}}"
            if existing == expected:
                return 0  # correct path already in place
            # Replace wrong path with correct one
            new_text = text[: m.start()] + expected + text[m.end() :]
            rel_display = file_path.relative_to(root)
            if dry_run:
                print(f"\n[{rel_display}]")
                print(f"  - {existing}")
                print(f"  + {expected}")
            else:
                try:
                    file_path.write_text(new_text, encoding="utf-8")
                except Exception as e:
                    print(
                        f"  ERROR writing {rel_display}: {e}", file=sys.stderr
                    )
                    return 0
                print(f"  {rel_display}: {existing} -> {expected}")
            return 1

        # Include does not exist — insert after YAML frontmatter
        # Skip auto-insertion for root index.qmd (homepage)
        if file_path.parent == root and file_path.name == "index.qmd":
            return 0

        m = re.match(r"^---\s*\n.*?\n(?:---)\s*\n?", text, re.DOTALL)
        if not m:
            return 0

        directive = f"\n{{{{< include {correct_rel} >}}}}\n"
        insert_at = m.end()
        new_text = text[:insert_at] + directive + text[insert_at:]

        rel_display = file_path.relative_to(root)
        if dry_run:
            print(f"\n[{rel_display}]")
            print(f"  + {directive.strip()}")
        else:
            try:
                file_path.write_text(new_text, encoding="utf-8")
            except Exception as e:
                print(
                    f"  ERROR writing {rel_display}: {e}", file=sys.stderr
                )
                return 0
            print(f"  {rel_display}: added {{< include {correct_rel} >}}")

        return 1

    # ------------------------------------------------------------------
    # Batch entry point
    # ------------------------------------------------------------------
    def resolve_all(
        self,
        root: Path,
        scan_root: Path,
        dry_run: bool,
        verbose: bool,
    ) -> Tuple[int, int]:
        return self._run_fix_all(
            root,
            scan_root,
            dry_run,
            verbose,
            "Adding missing title-meta-items include",
        )


# ======================================================================
# DocExtResolver — fix .qmd/.md links to .html
# ======================================================================
class DocExtResolver(_BaseResolver):
    """Replace ``.qmd`` / ``.md`` extensions with ``.html`` in markdown
    links throughout ``.qmd`` and ``.md`` files.

    Links like ``[text](notes/file.qmd)`` or
    ``[text](/docs/file.md)`` point to editable sources but should
    point to the rendered ``.html`` output instead.
    """

    _APPLY_BUILD_YML_EXCLUDE = True
    SOURCE_EXTENSIONS: Set[str] = {".qmd", ".md"}

    RE_LINK = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")

    def _extract_links(
        self, file_path: Path
    ) -> List[Tuple[str, int, int, str]]:
        """Return ``(url, start, end, corrected_url)`` for each link
        whose target ends with ``.qmd`` or ``.md``."""
        results: List[Tuple[str, int, int, str]] = []
        try:
            text = file_path.read_text(encoding="utf-8")
        except Exception:
            return results

        for m in self.RE_LINK.finditer(text):
            raw_url = m.group(2).strip()
            url = LinkResolver._clean_url(raw_url)
            if not url or LinkResolver._skip_link(url):
                continue
            # Check if it ends with .qmd or .md (optionally followed by #anchor)
            old_path = url.split("#", 1)[0] if "#" in url else url
            anchor = "#" + url.split("#", 1)[1] if "#" in url else ""
            if not old_path.endswith((".qmd", ".md")):
                continue
            # Skip .llms.md — those stay as .llms.md
            if old_path.endswith(".llms.md"):
                continue
            new_path = old_path.rsplit(".", 1)[0] + ".html" + anchor
            # Preserve any < > or title suffix from raw_url
            if new_path != url:
                # Rebuild raw replacement preserving original formatting
                # (angle brackets, title quotes) around the new path
                new_raw = raw_url.replace(url, new_path, 1)
                results.append((url, m.start(2), m.end(2), new_raw))

        return results

    def fix_one_file(
        self, file_path: Path, root: Path, dry_run: bool, verbose: bool
    ) -> int:
        links = self._extract_links(file_path)
        if not links:
            return 0

        try:
            text = file_path.read_text(encoding="utf-8")
        except Exception:
            return 0

        fixes: List[Tuple[int, int, str]] = []
        for url, start, end, new_raw in links:
            if new_raw == text[start:end]:
                continue  # no effective change
            fixes.append((start, end, new_raw))

        if not fixes:
            return 0

        fixes.sort(key=lambda x: x[0], reverse=True)
        new_text = text
        for start, end, new_val in fixes:
            new_text = new_text[:start] + new_val + new_text[end:]

        rel_display = file_path.relative_to(root)
        if dry_run:
            print(f"\n[{rel_display}]")
            for start, end, new_val in sorted(fixes, key=lambda x: x[0]):
                print(f"  - {text[start:end]}")
                print(f"  + {new_val}")
        else:
            try:
                file_path.write_text(new_text, encoding="utf-8")
            except Exception as e:
                print(
                    f"  ERROR writing {rel_display}: {e}", file=sys.stderr
                )
                return 0
            for start, end, new_val in sorted(fixes, key=lambda x: x[0]):
                print(f"  {rel_display}: {text[start:end]} -> {new_val}")

        return len(fixes)

    def resolve_all(
        self,
        root: Path,
        scan_root: Path,
        dry_run: bool,
        verbose: bool,
    ) -> Tuple[int, int]:
        return self._run_fix_all(
            root,
            scan_root,
            dry_run,
            verbose,
            "Fixing .qmd/.md links to .html",
        )


def main():
    parser = argparse.ArgumentParser(
        description="Resolve broken ../ relative asset paths and markdown links in QMD/MD files"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would change without writing files")
    parser.add_argument("--check", action="store_true",
                        help="Check-only: report broken paths without modifying;"
                             " exits 1 if any found")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show every file checked")
    parser.add_argument("--target", type=str, default=None,
                        help="Only process this target directory (relative to docs/)")
    parser.add_argument("--file", type=str, default=None,
                        help="Only process this specific file")
    args = parser.parse_args()

    root = Path(__file__).parent.resolve()
    resolvers: List = [LinkResolver(), IncludeResolver(), DocExtResolver(), PathResolver()]
    headers = ["Markdown links", "Missing title-meta-items include", "Doc ext .qmd/.md -> .html", "Asset paths"]

    if args.check:
        scan_root = (root / args.target) if args.target else root
        if args.file:
            scan_root = (root / args.file).parent
        sys.exit(
            _run_check_only(headers, resolvers, root, scan_root, args)
        )

    if args.dry_run or args.verbose:
        mode = "DRY-RUN" if args.dry_run else ""

    if args.file:
        file_path = (root / args.file).resolve()
        if not file_path.exists():
            print(f"ERROR: {file_path} does not exist", file=sys.stderr)
            sys.exit(1)
        exclude_patterns = PathResolver._load_exclude_patterns(root)
        if PathResolver()._is_ignored(file_path, root, exclude_patterns):
            print(f"ERROR: {file_path.relative_to(root)} is excluded by build.yml",
                  file=sys.stderr)
            sys.exit(1)

        total_fixes = 0
        for name, resolver in zip(headers, resolvers):
            mode = "DRY-RUN" if args.dry_run else "FIXING"
            print(f"{name} ({mode}) -- {args.file}\n")
            n = resolver.fix_one_file(file_path, root, args.dry_run, args.verbose)
            total_fixes += n
        print(f"\n{'='*60}")
        print(f"Total: {total_fixes} broken path(s)")
        if args.dry_run and total_fixes:
            print("(dry-run -- no files were modified)")
    else:
        scan_root = (root / args.target) if args.target else root
        total_proc = 0
        total_fixes = 0
        for name, resolver in zip(headers, resolvers):
            p, f = resolver.resolve_all(root, scan_root, args.dry_run, args.verbose)
            total_proc += p
            total_fixes += f
        print(f"{'='*60}")
        print(f"Combined: processed {total_proc} file(s), fixed {total_fixes} broken path(s)")


if __name__ == "__main__":
    main()
