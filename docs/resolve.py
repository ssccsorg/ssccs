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
# PathResolver — fix broken ../ relative asset paths
# ======================================================================
class PathResolver:
    """Detect and correct ``../`` relative asset paths that broke after a
    ``.qmd`` file was moved.

    Covers:
    * YAML frontmatter: ``metadata-files``, ``bibliography``, ``csl``
    * Jupyter ``%run`` directives inside code cells
    """

    # Filesystem-level ignores (VCS, tooling — not configurable in build.yml)
    SYSTEM_IGNORED_DIRS: Set[str] = {
        ".venv", ".git", ".quarto", "node_modules", "__pycache__", ".*",
    }
    SOURCE_EXTENSIONS: Set[str] = {".qmd"}
    PATH_KEYS: Set[str] = {"metadata-files", "bibliography", "csl"}
    RE_RUN = re.compile(r"^\s*%run\s+([^\s#]+)", re.MULTILINE)

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
        cfg = PathResolver._load_build_yml(root)
        patterns = cfg.get("exclude", [])
        return patterns if isinstance(patterns, list) else []

    @staticmethod
    def _matches_gitignore_pattern(rel_path: Path, patterns: List[str]) -> bool:
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
                        parts[i], pattern.split("/")[-1] if "/" in pattern else pattern
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
    # File discovery
    # ------------------------------------------------------------------
    def _is_ignored(self, file_path: Path, root: Path, exclude_patterns: List[str]) -> bool:
        parts = file_path.relative_to(root).parts
        for part in parts:
            for pattern in self.SYSTEM_IGNORED_DIRS:
                if fnmatch.fnmatch(part, pattern):
                    return True
        if exclude_patterns:
            return self._matches_gitignore_pattern(
                file_path.relative_to(root), exclude_patterns
            )
        return False

    def discover_files(
        self, root: Path, scan_root: Path, exclude_patterns: List[str]
    ) -> List[Path]:
        return sorted(
            p for p in scan_root.rglob("*")
            if p.suffix in self.SOURCE_EXTENSIONS
            and not self._is_ignored(p, root, exclude_patterns)
        )

    # ------------------------------------------------------------------
    # Path extraction helpers
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
    def _search_upward(start_dir: Path, rel: str, root: Path) -> Optional[Path]:
        cur = start_dir
        while cur >= root:
            candidate = (cur / rel).resolve()
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
# CLI
# ======================================================================
def main():
    parser = argparse.ArgumentParser(
        description="Resolve broken ../ relative asset paths in QMD files"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would change without writing files")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show every file checked")
    parser.add_argument("--target", type=str, default=None,
                        help="Only process this target directory (relative to docs/)")
    parser.add_argument("--file", type=str, default=None,
                        help="Only process this specific file")
    args = parser.parse_args()

    root = Path(__file__).parent.resolve()
    resolver = PathResolver()

    if args.file:
        file_path = (root / args.file).resolve()
        if not file_path.exists():
            print(f"ERROR: {file_path} does not exist", file=sys.stderr)
            sys.exit(1)
        files = [file_path]
        exclude_patterns = resolver._load_exclude_patterns(root)
        if resolver._is_ignored(file_path, root, exclude_patterns):
            print(f"ERROR: {file_path.relative_to(root)} is excluded by build.yml",
                  file=sys.stderr)
            sys.exit(1)

        mode = "DRY-RUN" if args.dry_run else "FIXING"
        print(f"Resolving ({mode}) — {args.file}\n")
        total_fixes = 0
        for fp in files:
            total_fixes += resolver.fix_one_file(fp, root, args.dry_run, args.verbose)
        print(f"\n{'='*60}")
        print(f"Fixed {total_fixes} broken path(s)")
        if args.dry_run and total_fixes:
            print("(dry-run – no files were modified)")
    else:
        scan_root = (root / args.target) if args.target else root
        resolver.resolve_all(root, scan_root, args.dry_run, args.verbose)


if __name__ == "__main__":
    main()
