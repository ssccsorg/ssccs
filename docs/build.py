#!/usr/bin/env python3
"""
Top-level build manager for SSCCS documentation.

Behavior:
  - Single target: runs normally
  - Multiple targets: runs in PARALLEL by default
  - Use --sequence/-s to force sequential execution

Caching:
  - Outputs of non‑deterministic formats (pdf, beamer, html, gfm) are cached based on
    a combined SHA‑256 hash that includes the QMD source file and all its dependencies
    (included QMD files and Python files referenced by %run directives). This prevents
    unnecessary re‑renders when the source or any dependency is unchanged, even if the
    generated file would be slightly different (e.g. due to timestamps). The rendered
    output hash is still stored for the `snapshot` command, but it is not used to decide
    whether to render.
  - Cache entries are stored in a `{qmd_stem}_locked/` directory adjacent to
    each QMD file. If the combined hash matches the cached one, the Quarto render
    step is skipped.

Snapshot:
  - Use `./build.py snapshot` to refresh cache hashes for all targets.
  - Specify individual targets: `./build.py snapshot whitepaper proposal`
  - **Important:** Snapshot updates the cache only when the combined source hash has not changed
    (i.e., the source and its dependencies are identical to when the cache was created). If the
    combined hash changed, the cache is removed, forcing a rebuild on the next build.
  - This avoids recording stale outputs and eliminates reliance on file timestamps.

Important:
  - Formats can be rendered either in parallel (each in a separate `quarto render` call)
    or in a single command (with `--to format1,format2`) depending on the `--single-command` flag.
    Concurrency is limited to the number of formats per target when parallel mode is used.
  - A per‑QMD lock ensures that concurrent Quarto renders on the same source file do not interfere
    with each other (avoiding temporary‑directory collisions). This lock is transparent to the user.
  - The script **never** guesses output filenames. It uses `quarto inspect` to obtain
    the exact output path for each format. If that information is unavailable, the
    build fails for that target.
  - Destination filenames in post‑processing (e.g., `index.html`, `README.md`) are
    hardcoded only as part of the target‑specific behavior defined in `SPECIAL_CONFIG`.

Usage:
  ./build.py whitepaper                     # Single target
  ./build.py whitepaper readme              # Multiple -> parallel by default
  ./build.py whitepaper,readme,legal        # Multiple -> parallel by default
  ./build.py -s whitepaper proposal readme  # Force sequential execution
  ./build.py -j 2 whitepaper,proposal       # Parallel with 2 jobs
  ./build.py -o ./dist whitepaper proposal  # With output directory
  ./build.py snapshot                       # Refresh cache for all targets
  ./build.py snapshot whitepaper proposal   # Refresh cache for specific targets
  ./build.py --single-command whitepaper     # Use single Quarto command for all formats
"""

import argparse
import hashlib
import json
import logging
import re
import shutil
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Optional, Dict, Callable, Tuple, Any
from functools import lru_cache

# Formats that are considered non‑deterministic (cached based on QMD hash only)
NON_DETERMINISTIC_FORMATS = {"pdf", "beamer", "html", "gfm"}

# Per‑QMD locks to prevent concurrent Quarto renders on the same source file
_QMD_LOCKS = {}
_QMD_LOCKS_LOCK = threading.Lock()

def _lock_for_qmd(qmd_path: Path) -> threading.Lock:
    """Return a dedicated lock for the given QMD path."""
    with _QMD_LOCKS_LOCK:
        lock = _QMD_LOCKS.get(qmd_path)
        if lock is None:
            lock = threading.Lock()
            _QMD_LOCKS[qmd_path] = lock
        return lock

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@lru_cache(maxsize=128)
def compute_file_hash(path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    try:
        with open(path, 'rb') as f:
            return hashlib.file_digest(f, 'sha256').hexdigest()
    except FileNotFoundError:
        raise


@lru_cache(maxsize=32)
def compute_qmd_hash_with_deps(qmd_path: Path) -> str:
    """
    Compute a combined SHA‑256 hash that includes the QMD file itself and all
    files it directly or indirectly includes (via `includeMap`) as well as
    Python files referenced by `%run` directives in code cells.
    """
    visited = set()
    # Helper to resolve relative paths relative to a base file
    def resolve(base: Path, rel: str) -> Path:
        # rel may be relative with '..' or '.'
        return (base.parent / rel).resolve()

    def collect(path: Path) -> None:
        if path in visited:
            return
        visited.add(path)
        data = inspect_qmd(path)
        if data is None:
            # If inspect fails, we still have the file itself; no further dependencies
            return
        fi = data.get("fileInformation", {})
        # fi is a dict keyed by file path (absolute). Use the key that matches path
        # (might be relative). We'll find the entry whose key ends with path.name
        entry = None
        for key, val in fi.items():
            if Path(key).resolve() == path.resolve():
                entry = val
                break
        if entry is None:
            # No file information, treat as leaf
            return
        # Process includeMap
        for inc in entry.get("includeMap", []):
            target_rel = inc.get("target")
            if target_rel:
                target = resolve(path, target_rel)
                # Only recurse into QMD files; other files are added as dependencies
                if target.suffix.lower() == ".qmd":
                    collect(target)
                else:
                    visited.add(target)
        # Process codeCells for %run directives
        for cell in entry.get("codeCells", []):
            source = cell.get("source", "")
            # Look for lines starting with %run
            for line in source.splitlines():
                line = line.strip()
                if line.startswith("%run"):
                    # Extract the first non‑whitespace token after %run
                    parts = line.split()
                    if len(parts) >= 2:
                        run_path = parts[1]
                        # Remove any trailing arguments (e.g., --output)
                        run_path = run_path.split("--")[0].strip()
                        if run_path:
                            # Resolve relative to the cell's file (if given) else path
                            cell_file = cell.get("file")
                            base = Path(cell_file).parent if cell_file else path.parent
                            try:
                                dep = (base / run_path).resolve()
                                if dep.exists():
                                    visited.add(dep)
                            except Exception:
                                pass
                    break  # only first %run per line? we'll continue scanning lines

        # Add config files
        for config_path in data.get("config", []):
            visited.add(Path(config_path).resolve())
        for resource_path in data.get("configResources", []):
            visited.add(Path(resource_path).resolve())

    # Start collection
    collect(qmd_path.resolve())

    # Compute combined hash
    hasher = hashlib.sha256()
    for dep in sorted(visited, key=lambda p: str(p)):
        # Include each file's hash
        try:
            dep_hash = compute_file_hash(dep)
            hasher.update(dep_hash.encode("utf-8"))
        except FileNotFoundError:
            # If a dependency disappears, we treat it as changed, causing a rebuild
            # by including a placeholder.
            hasher.update(b"<missing>")
    return hasher.hexdigest()


def target_produces_pdf(config: Dict[str, Any]) -> bool:
    """
    Return True if the target is expected to produce PDF/beamer output.
    """
    target_format = config.get("to")
    if target_format in ("pdf", "beamer"):
        return True
    if target_format is None and config.get("copy_pdf"):
        # No explicit format but copy_pdf suggests PDF will be generated
        return True
    return False


@lru_cache(maxsize=128)
def inspect_qmd(qmd_path: Path) -> Optional[Dict[str, Any]]:
    """
    Run `quarto inspect` on the QMD file and return the parsed JSON.
    Returns None on failure.
    """
    try:
        result = subprocess.run(
            ["quarto", "inspect", str(qmd_path)],
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(result.stdout)
    except Exception as e:
        logger.warning(f"Failed to inspect {qmd_path}: {e}")
        return None


def get_formats_from_qmd(qmd_path: Path) -> List[str]:
    """
    Inspect the QMD file and return a list of output formats defined in its YAML.
    Returns empty list on failure.
    """
    data = inspect_qmd(qmd_path)
    if data is None:
        return []
    formats = data.get("formats", {})
    return list(formats.keys())


def get_format_output_path(qmd_path: Path, fmt: str) -> Optional[Path]:
    """
    Determine the output file path for a given format using quarto inspect.
    Returns None if format not found or path cannot be determined.
    """
    data = inspect_qmd(qmd_path)
    if data is None:
        return None
    formats = data.get("formats", {})
    if fmt not in formats:
        return None
    # Look for output-file in pandoc section
    pandoc = formats[fmt].get("pandoc", {})
    output_file = pandoc.get("output-file")
    if output_file:
        # Path is relative to the QMD's parent directory
        return qmd_path.parent / output_file
    # If no explicit output-file, Quarto uses a default based on format.
    # We do NOT guess; we return None because we cannot be certain.
    # The caller must handle this as an error.
    return None


def get_moved_path_for_format(
    qmd_path: Path,
    fmt: str,
    config: Dict[str, Any],
    output_dir: Optional[Path],
    docs_root: Path,
    source_path: Path,  # the primary output path (must be known)
) -> Optional[Path]:
    """
    Return the path where the output file for the given format is moved
    after post‑processing, if any. Returns None if no move applies or if
    the source path is unknown.
    """
    stem = qmd_path.stem
    # PDF moves
    if fmt in ("pdf", "beamer") and config.get("copy_pdf"):
        dest_dir = output_dir.absolute() if output_dir else docs_root
        return dest_dir / f"{stem}.pdf"
    # HTML moves (manifesto) – note: the moved file is always 'index.html' in the dest dir
    if fmt == "html" and config.get("copy_html"):
        dest_dir = output_dir.absolute() if output_dir else docs_root
        return dest_dir / "index.html"
    # Markdown moves (manifesto) – moved file keeps stem name
    if fmt in ("gfm", "markdown") and config.get("copy_md"):
        dest_dir = output_dir.absolute() if output_dir else docs_root
        return dest_dir / f"{stem}.md"
    # README copy to project root (special case for 'readme' target)
    if fmt == "gfm" and config.get("copy_to_root"):
        return docs_root.parent / "README.md"
    return None


def find_existing_output(
    qmd_path: Path,
    fmt: str,
    config: Optional[Dict[str, Any]],
    output_dir: Optional[Path],
) -> Optional[Path]:
    """
    Find an existing output file for the given format, considering possible
    moved locations (copy_pdf, copy_html, copy_md, copy_to_root).
    Returns the path if found, otherwise None.
    """
    # Primary output path (must be known)
    primary = get_format_output_path(qmd_path, fmt)
    if primary is None:
        # Cannot determine output path – treat as missing.
        return None

    candidates = [primary]

    # Add moved location if applicable
    if config:
        docs_root = Path(__file__).parent.absolute()
        moved = get_moved_path_for_format(qmd_path, fmt, config, output_dir, docs_root, primary)
        if moved and moved != primary:
            candidates.append(moved)

    # Return first existing candidate
    for cand in candidates:
        if cand.exists():
            return cand
    return None


def get_cache_dir(qmd_path: Path) -> Path:
    """Return the _locked directory for a QMD file."""
    return qmd_path.parent / f"{qmd_path.stem}_locked"


def get_cache_file(qmd_path: Path, fmt: str) -> Path:
    """Return the cache file path for a given format."""
    return get_cache_dir(qmd_path) / f"rendered_{fmt}.txt"


def read_hash_pair(cache_file: Path) -> Optional[Tuple[str, str]]:
    """
    Read hash pair from cache file.
    Returns (qmd_hash, output_hash) or None if missing/malformed.
    """
    if not cache_file.exists():
        return None
    try:
        with open(cache_file, 'r') as f:
            line = f.read().strip()
        if '_' in line:
            a, b = line.split('_', 1)
            if len(a) == 64 and len(b) == 64:  # SHA-256 hex length
                return (a, b)
    except Exception:
        pass
    return None


def write_hash_pair(cache_file: Path, qmd_hash: str, output_hash: str) -> None:
    """Write hash pair to cache file."""
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_file, 'w') as f:
        f.write(f"{qmd_hash}_{output_hash}")


def should_render_format(
    qmd_path: Path,
    fmt: str,
    config: Optional[Dict[str, Any]] = None,
    output_dir: Optional[Path] = None,
) -> bool:
    """
    Determine whether a given format needs to be rendered based on cached QMD hash.
    For non‑deterministic formats, we only compare the QMD hash; the output hash
    is ignored to avoid unnecessary re‑renders when the generated file would be
    slightly different (e.g. due to timestamps). Deterministic formats are always
    rendered.
    Returns True if render is needed, False if up‑to‑date.
    """
    # Only cache non‑deterministic formats; others always render
    if fmt not in NON_DETERMINISTIC_FORMATS:
        logger.info(f"{fmt} is considered deterministic, always render.")
        return True

    existing_output = find_existing_output(qmd_path, fmt, config, output_dir)

    if existing_output is None:
        logger.info(f"No {fmt} output found for {qmd_path.name}, need render.")
        return True

    qmd_hash = compute_qmd_hash_with_deps(qmd_path)
    logger.info(f"Checking cache for {qmd_path.name} ({fmt}): QMD hash {qmd_hash[:16]}...")
    cache_file = get_cache_file(qmd_path, fmt)
    pair = read_hash_pair(cache_file)
    if pair is None:
        logger.info(f"No cache file found for {qmd_path.name} ({fmt}), need render.")
        return True
    cached_qmd, _ = pair
    if cached_qmd == qmd_hash:
        logger.info(f"Cache matches for {qmd_path.name} (QMD unchanged), skipping {fmt} render.")
        return False
    logger.info(f"Cache mismatch for {qmd_path.name} ({fmt}) – QMD changed, need render.")
    return True


def should_render_pdf(
    qmd_path: Path,
    pdf_path: Path,
    config: Optional[Dict[str, Any]] = None,
    output_dir: Optional[Path] = None,
) -> bool:
    """
    Determine whether PDF needs to be rendered based on cached hashes.
    Returns True if render is needed, False if up‑to‑date.
    """
    # delegate to generic function with format='pdf'
    return should_render_format(qmd_path, 'pdf', config, output_dir)


def update_format_cache(qmd_path: Path, fmt: str, output_path: Path) -> None:
    """Update cache after successful render of a specific format."""
    qmd_hash = compute_qmd_hash_with_deps(qmd_path)
    output_hash = compute_file_hash(output_path)
    logger.info(f"Updating {fmt} cache for {qmd_path.name}: output hash {output_hash[:16]}...")
    cache_file = get_cache_file(qmd_path, fmt)
    write_hash_pair(cache_file, qmd_hash, output_hash)


def refresh_cache_for_target(target: str, output_dir: Optional[Path] = None) -> bool:
    """
    Refresh the cache entries for a given target.
    Updates the cache only when the QMD hash has not changed (i.e., the source is
    identical to when the cache was created). If the QMD hash changed, the cache
    is removed to force a rebuild on the next build. This avoids recording stale
    outputs and eliminates reliance on file timestamps.
    Returns True on success, False on failure.
    """
    if target not in TARGET_CONFIG:
        logger.error(f"Unknown target '{target}'")
        return False
    config = TARGET_CONFIG[target]
    docs_root = Path(__file__).parent.absolute()
    qmd_path = docs_root / config["qmd"]
    if not qmd_path.exists():
        logger.error(f"Qmd file not found: {qmd_path}")
        return False

    # Determine all formats defined in the QMD
    formats = get_formats_from_qmd(qmd_path)
    if not formats:
        logger.info(f"Target {target} has no defined output formats, skipping cache refresh.")
        return True

    current_qmd_hash = compute_qmd_hash_with_deps(qmd_path)

    for fmt in formats:
        cache_file = get_cache_file(qmd_path, fmt)
        existing_cache = read_hash_pair(cache_file)

        output_path = find_existing_output(qmd_path, fmt, config, output_dir)

        if output_path and output_path.exists():
            # Output exists
            if existing_cache is not None and existing_cache[0] == current_qmd_hash:
                # QMD unchanged – update cache (output may have changed due to non‑determinism)
                update_format_cache(qmd_path, fmt, output_path)
                logger.info(f"Updated {fmt} cache for {target}")
            else:
                # QMD changed or cache missing – we cannot trust the output; remove cache to force rebuild
                if cache_file.exists():
                    cache_file.unlink()
                    logger.info(f"Removed cache file for {target} ({fmt}) – QMD changed or cache missing")
                else:
                    logger.info(f"No cache file for {target} ({fmt}) – will rebuild on next run")
        else:
            # No output file (or output path unknown), remove cache file for this format
            if cache_file.exists():
                cache_file.unlink()
                logger.info(f"Removed cache file for {target} ({fmt} output missing)")
            else:
                logger.info(f"No cache file for {target} ({fmt} output missing)")
    return True


def clean_quarto_artifacts(docs_root: Path) -> bool:
    """
    Remove Quarto-generated directories matching the patterns
    """
    patterns = [
        "**/*_files",
        "**/*_output",
        "**/*_extensions",
        "**/*_locked",

        # quarto: final artifects
        "**/*.tex",
        "**/*.pdf",
        "**/*.html",
        "**/*.c2pa_identifier.svg",

        # quarto: global
        "**/*.quarto_ipynb",
        "**/*.quarto",

        # c2pa
        "**/*.c2pa",
    ]
    deleted = []
    errors = []
    for pattern in patterns:
        for item in docs_root.glob(pattern):
            if item.is_dir():
                try:
                    shutil.rmtree(item)
                    deleted.append(str(item))
                    logger.info(f"Deleted directory: {item}")
                except Exception as e:
                    errors.append(f"Failed to delete {item}: {e}")
            elif item.is_file():
                try:
                    item.unlink()
                    deleted.append(str(item))
                    logger.info(f"Deleted file: {item}")
                except Exception as e:
                    errors.append(f"Failed to delete {item}: {e}")
    if deleted:
        logger.info(f"Cleaned {len(deleted)} items.")
    if errors:
        for err in errors:
            logger.error(err)
        return False
    return True


# Special target configurations
SPECIAL_CONFIG: Dict[str, Dict[str, Any]] = {
    "whitepaper": {
        "output_dir": True,
        "c2pa": True,
        "copy_pdf": True,
    },
    "proposal": {
        "output_dir": True,
        "c2pa": True,
        "copy_pdf": True,
        "copy_html": True,
    },
}

def discover_qmd_targets(docs_root: Path) -> Dict[str, Dict[str, Any]]:
    """
    Scan docs_root for .qmd files and return target configurations.
    Excludes directories matching the patterns:
      **/*_include, **/*_extensions, **/*_utils, **/*_output, **/*_files, **/*_locked
    (i.e., any directory whose name ends with one of these suffixes, at any depth)
    """
    exclude_suffixes = ["_include", "_extensions", "_utils", "_output", "_files", "_locked"]
    exclude_dirs = set()
    for suffix in exclude_suffixes:
        pattern = f"**/*{suffix}"
        for item in docs_root.glob(pattern):
            if item.is_dir():
                exclude_dirs.add(item.resolve())

    targets = {}
    for qmd_path in docs_root.rglob("*.qmd"):
        qmd_resolved = qmd_path.resolve()
        if any(qmd_resolved.is_relative_to(ex_dir) for ex_dir in exclude_dirs):
            continue

        rel_path = qmd_path.relative_to(docs_root)
        target_name = rel_path.stem.lower()

        if target_name in targets:
            parent = rel_path.parent.name
            if parent:
                target_name = f"{target_name}_{parent}"
            else:
                suffix = 2
                while f"{target_name}_{suffix}" in targets:
                    suffix += 1
                target_name = f"{target_name}_{suffix}"

        config = {
            "qmd": str(rel_path),
            "output_dir": False,
            "c2pa": False,
            "copy_pdf": False,
            "copy_to_root": False,
            "to": None,
            "copy_html": False,
            "copy_md": False,
        }
        targets[target_name] = config
    return targets


def get_target_config(docs_root: Path) -> Dict[str, Dict[str, Any]]:
    """
    Return merged configuration: special config updates discovered defaults.
    """
    discovered = discover_qmd_targets(docs_root)
    # Merge special config (updates discovered entries)
    for target, config in SPECIAL_CONFIG.items():
        if target not in discovered:
            logger.error(f"Target '{target}' not found in discovered .qmd files")
            sys.exit(1)
        # Update discovered config with special config, preserving missing keys
        discovered[target].update(config)
        # Validate that qmd stem matches target name (case-insensitive)
        qmd_path = Path(discovered[target]["qmd"])
        if qmd_path.stem.lower() != target.lower():
            logger.error(
                f"Target name '{target}' does not match QMD file stem '{qmd_path.stem}' "
                f"(expected '{target}.qmd' or similar)"
            )
            sys.exit(1)
    return discovered


def run_command(cmd: List[str], cwd: Optional[Path] = None) -> bool:
    """
    Run a shell command and log its output.

    Args:
        cmd: List of command and arguments.
        cwd: Working directory (optional).

    Returns:
        True if the command succeeded (exit code 0), False otherwise.
    """
    logger.info(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.stdout:
            logger.debug(result.stdout.strip())
        if result.stderr:
            logger.warning(result.stderr.strip())
        if result.returncode != 0:
            logger.error(f"Command failed with exit code {result.returncode}")
            return False
        logger.info("Command succeeded")
        return True
    except FileNotFoundError as e:
        logger.error(f"Command not found: {cmd[0]}. Is it installed? {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error while running command: {e}")
        return False


def _render_formats_parallel(
    qmd_path: Path,
    formats: List[str],
    format_output_paths: Dict[str, Path],
    docs_root: Path
) -> bool:
    """Render each format in its own Quarto command, running in parallel threads."""
    def render_single_format(fmt: str) -> bool:
        lock = _lock_for_qmd(qmd_path)
        with lock:
            quarto_cmd = ["quarto", "render", str(qmd_path), "--to", fmt]
            if not run_command(quarto_cmd, cwd=docs_root):
                logger.error(f"Quarto render failed for {qmd_path.name} (format {fmt}).")
                return False
            if fmt in NON_DETERMINISTIC_FORMATS:
                output_path = format_output_paths[fmt]
                if output_path.exists():
                    update_format_cache(qmd_path, fmt, output_path)
                else:
                    logger.warning(f"Expected output {output_path} not found after render for {fmt}")
            return True

    with ThreadPoolExecutor(max_workers=len(formats)) as executor:
        futures = {executor.submit(render_single_format, fmt): fmt for fmt in formats}
        success_count = 0
        for future in as_completed(futures):
            fmt = futures[future]
            try:
                success = future.result()
            except Exception as e:
                logger.error(f"Unexpected error while rendering {fmt}: {e}")
                success = False
            if success:
                success_count += 1
            else:
                logger.error(f"Format {fmt} failed.")
        return success_count == len(formats)


def _render_formats_single(
    qmd_path: Path,
    formats: List[str],
    format_output_paths: Dict[str, Path],
    docs_root: Path
) -> bool:
    """Render all formats using a single Quarto command (--to fmt1,fmt2)."""
    lock = _lock_for_qmd(qmd_path)
    with lock:
        formats_str = ",".join(formats)
        quarto_cmd = ["quarto", "render", str(qmd_path), "--to", formats_str]
        if not run_command(quarto_cmd, cwd=docs_root):
            logger.error(f"Quarto render failed for {qmd_path.name} (formats {formats_str}).")
            return False
        # Update cache for each rendered format
        for fmt in formats:
            if fmt in NON_DETERMINISTIC_FORMATS:
                output_path = format_output_paths[fmt]
                if output_path.exists():
                    update_format_cache(qmd_path, fmt, output_path)
                else:
                    logger.warning(f"Expected output {output_path} not found after render for {fmt}")
        return True


def _render_formats(
    qmd_path: Path,
    formats: List[str],
    format_output_paths: Dict[str, Path],
    docs_root: Path,
    single_command: bool
) -> bool:
    """Dispatch to the appropriate rendering strategy."""
    if single_command:
        return _render_formats_single(qmd_path, formats, format_output_paths, docs_root)
    else:
        return _render_formats_parallel(qmd_path, formats, format_output_paths, docs_root)


def build_generic(target: str, config: Dict[str, Any], output_dir: Optional[Path] = None, single_command: bool = False) -> bool:
    """
    Generic build function that renders a .qmd file and performs optional post‑processing.
    Formats are rendered either in parallel (separate commands) or in a single command
    depending on the `single_command` flag.
    """
    logger.info(f"Building {target}...")
    docs_root = Path(__file__).parent.absolute()

    qmd_path = docs_root / config["qmd"]
    if not qmd_path.exists():
        logger.error(f"Qmd file not found: {qmd_path}")
        return False

    # Determine generated files early for caching
    stem = qmd_path.stem
    parent = qmd_path.parent

    # Determine formats to render
    target_format = config.get("to")
    if target_format is None:
        # inspect the QMD to get all formats
        formats = get_formats_from_qmd(qmd_path)
        if not formats:
            logger.error(f"Could not determine output formats for {qmd_path}. "
                         f"Please specify a format in the target config or ensure 'quarto inspect' works.")
            return False
    else:
        formats = [target_format]

    # Validate that we can determine output paths for all formats
    format_output_paths = {}  # fmt -> Path (expected output before moves)
    for fmt in formats:
        output_path = get_format_output_path(qmd_path, fmt)
        if output_path is None:
            logger.error(f"Cannot determine output path for format '{fmt}' of {qmd_path}. "
                         f"Please ensure 'quarto inspect' provides an 'output-file' or that the format is properly defined.")
            return False
        format_output_paths[fmt] = output_path

    # Determine which formats need rendering
    formats_to_render = []
    for fmt in formats:
        if should_render_format(qmd_path, fmt, config, output_dir):
            formats_to_render.append(fmt)

    # Render
    if formats_to_render:
        logger.info(f"Rendering {len(formats_to_render)} format(s) for {target}")
        if not _render_formats(qmd_path, formats_to_render, format_output_paths, docs_root, single_command):
            return False
    else:
        logger.info(f"All formats for {target} are up‑to‑date, skipping render.")

    # Step 2: C2PA signing (if enabled) – assumes PDF exists at format_output_paths['pdf'] or similar
    if config.get("c2pa"):
        pdf_path = format_output_paths.get('pdf') or format_output_paths.get('beamer')
        if pdf_path and pdf_path.exists():
            manifest_path = parent / f"{stem}.c2pa_manifest.json"
            output_c2pa = parent / f"{stem}.c2pa"
            sign_cmd = [
                "python3", "_utils/sign_c2pa.py",
                "--pdf", str(pdf_path),
                "--manifest", str(manifest_path),
                "--output", str(output_c2pa),
            ]
            if not run_command(sign_cmd, cwd=docs_root):
                logger.warning(f"C2PA signing failed for {target}. Proceeding without signature.")
        else:
            logger.warning(f"C2PA signing requested but PDF output not found for {target}")

    # Step 3: Copy PDF to output_dir (if enabled)
    if config.get("copy_pdf"):
        pdf_path = format_output_paths.get('pdf') or format_output_paths.get('beamer')
        if pdf_path and pdf_path.exists():
            dest_dir = Path(output_dir).absolute() if output_dir else docs_root
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_pdf = dest_dir / f"{stem}.pdf"
            # Avoid moving if source and destination are the same
            if dest_pdf.resolve() != pdf_path.resolve():
                try:
                    shutil.move(str(pdf_path), str(dest_pdf))
                    logger.info(f"Moved PDF to {dest_pdf}")
                except Exception as e:
                    logger.error(f"Failed to move PDF: {e}")
                    return False
            else:
                logger.info("PDF already at destination, skipping move.")

    # Step 5: Copy HTML/Markdown to output_dir (if enabled)
    if output_dir:
        if config.get("copy_html"):
            html_path = format_output_paths.get('html')
            if html_path and html_path.exists():
                dest_dir = Path(output_dir).absolute()
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest_html = dest_dir / "index.html"
                try:
                    shutil.copy2(str(html_path), str(dest_html))
                    logger.info(f"Copied index.html to {dest_html}")
                except Exception as e:
                    logger.error(f"Failed to copy index.html: {e}")
                    return False
            else:
                logger.warning(f"copy_html enabled but HTML output not found for {target}")
        if config.get("copy_md"):
            # Note: assumes Markdown format is either 'gfm' or 'markdown'
            md_path = format_output_paths.get('gfm') or format_output_paths.get('markdown')
            if md_path and md_path.exists():
                dest_dir = Path(output_dir).absolute()
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest_md = dest_dir / f"{stem}.md"
                try:
                    shutil.copy2(str(md_path), str(dest_md))
                    logger.info(f"Copied {stem}.md to {dest_md}")
                except Exception as e:
                    logger.error(f"Failed to copy {stem}.md: {e}")
                    return False
            else:
                logger.warning(f"copy_md enabled but Markdown output not found for {target}")

    logger.info(f"{target} build completed successfully.")
    return True


DOCS_ROOT = Path(__file__).parent.absolute()
TARGET_CONFIG = get_target_config(DOCS_ROOT)


# Build function mapping per target (auto‑generated from TARGET_CONFIG)
BUILD_FUNCTIONS: Dict[str, Callable[..., bool]] = {}
for target, config in TARGET_CONFIG.items():
    # Create a closure that captures target and config
    def make_builder(tgt, cfg):
        def builder(output_dir: Optional[Path] = None, single_command: bool = False) -> bool:
            return build_generic(tgt, cfg, output_dir, single_command)
        return builder
    BUILD_FUNCTIONS[target] = make_builder(target, config)

# list of targets that receive output_dir argument (those with output_dir=True in config)
OUTPUT_DIR_TARGETS = {t for t, cfg in TARGET_CONFIG.items() if cfg.get("output_dir")}


def parse_targets(targets_arg: List[str]) -> List[str]:
    """
    Parse target arguments: supports both space-separated and comma-separated.
    Example: ["whitepaper,readme"] -> ["whitepaper", "readme"]
             ["whitepaper", "readme"] -> ["whitepaper", "readme"]
    """
    parsed = []
    for t in targets_arg:
        if "," in t:
            parsed.extend([x.strip() for x in t.split(",") if x.strip()])
        elif t.strip():
            parsed.append(t.strip())
    return parsed


def validate_targets(targets: List[str]) -> List[str]:
    """Validate target names against available functions."""
    invalid = [t for t in targets if t not in BUILD_FUNCTIONS]
    if invalid:
        logger.error(f"Unknown target(s): {invalid}. Available: {list(BUILD_FUNCTIONS.keys())}")
        sys.exit(1)
    return targets


def build_single_target(target: str, output_dir: Optional[Path], single_command: bool) -> Tuple[str, bool]:
    """Wrapper to run a single build function and return (target_name, success)."""
    logger.info(f"Starting build: {target}")
    func = BUILD_FUNCTIONS[target]
    try:
        if target in OUTPUT_DIR_TARGETS:
            success = func(output_dir=output_dir, single_command=single_command)
        else:
            success = func(single_command=single_command)
        logger.info(f"Finished build: {target} -> {'✓' if success else '✗'}")
        return target, success
    except Exception as e:
        logger.error(f"Exception while building {target}: {e}")
        return target, False


def build_targets(
    targets: List[str],
    output_dir: Optional[Path],
    sequence_mode: bool,
    max_jobs: int,
    single_command: bool
) -> bool:
    """
    Build multiple targets.

    Behavior:
      - If sequence_mode=True: run sequentially regardless of target count
      - If sequence_mode=False and len(targets) > 1: run in parallel (default)
      - If sequence_mode=False and len(targets) == 1: run normally (no threading overhead)
    """
    if not targets:
        logger.info("No targets specified. Nothing to build.")
        return True

    results: Dict[str, bool] = {}

    # Decide execution mode: parallel only if NOT sequence_mode AND multiple targets
    use_parallel = (not sequence_mode) and (len(targets) > 1)

    if use_parallel:
        logger.info(f"Running {len(targets)} targets in parallel (max_jobs={max_jobs})")
        with ThreadPoolExecutor(max_workers=max_jobs) as executor:
            futures = {
                executor.submit(build_single_target, t, output_dir, single_command): t
                for t in targets
            }
            for future in as_completed(futures):
                target, success = future.result()
                results[target] = success
    else:
        # Sequential execution (either forced by --sequence, or single target)
        if len(targets) > 1:
            logger.info(f"Running {len(targets)} targets sequentially (--sequence mode)")
        for target in targets:
            _, success = build_single_target(target, output_dir, single_command)
            results[target] = success

    # Summary of results
    succeeded = [t for t, s in results.items() if s]
    failed = [t for t, s in results.items() if not s]

    if failed:
        if succeeded:
            logger.info(f"Successful targets: {succeeded}")
        logger.error(f"Failed targets: {failed}")
        return False

    logger.info(f"All targets completed successfully: {list(results.keys())}")
    return True


def main() -> None:
    """Parse command line arguments and dispatch to build functions."""
    parser = argparse.ArgumentParser(
        description="SSCCS Documentation Build Manager",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Behavior:
  - Single target: formats are rendered either in parallel or in a single Quarto command.
  - Multiple targets: runs in PARALLEL by default (targets parallel, formats parallel per target)
    unless --single-command is used.
  - Use --sequence/-s to force sequential execution across targets.
  - Use --single-command to render all formats of a target in one Quarto command.

Snapshot:
  - Use `%(prog)s snapshot` to refresh cache hashes for all targets.
  - Specify individual targets: `%(prog)s snapshot whitepaper proposal`
  - Updates cache entries with current file hashes; missing PDFs cause cache removal.
  - **Only updates if the QMD hash has not changed** – otherwise removes cache.

Clean:
  - Use `%(prog)s clean` to remove Quarto‑generated directories:
      **/*_files, **/*_output, **/*_extensions, **/*_locked
  - Deletes all matching directories and files recursively.

Examples:
  %(prog)s whitepaper                     # Single target
  %(prog)s whitepaper readme              # Multiple -> parallel by default
  %(prog)s whitepaper,readme,legal        # Multiple -> parallel by default
  %(prog)s -s whitepaper proposal readme  # Force sequential execution
  %(prog)s -j 2 whitepaper,proposal       # Parallel with 2 jobs
  %(prog)s -o ./dist whitepaper proposal  # Specify output directory
  %(prog)s snapshot                       # Refresh cache for all targets
  %(prog)s snapshot whitepaper proposal   # Refresh cache for specific targets
  %(prog)s clean                          # Remove Quarto artifacts
  %(prog)s --single-command whitepaper     # Use single Quarto command for all formats
        """
    )

    parser.add_argument(
        "--output-dir", "-o",
        type=Path,
        default=None,
        help="Directory to place the final PDF (default: docs root)",
    )
    parser.add_argument(
        "--sequence", "-s",
        action="store_true",
        help="Force sequential execution even with multiple targets",
    )
    parser.add_argument(
        "--jobs", "-j",
        type=int,
        default=5,
        help="Max number of parallel jobs (default: 4, only used in parallel mode)",
    )
    parser.add_argument(
        "--single-command",
        action="store_true",
        help="Render all formats in a single Quarto command (--to fmt1,fmt2) instead of separate commands",
    )
    parser.add_argument(
        "targets",
        nargs="*",
        default=["all"],
        help="Build targets: any discovered .qmd file (e.g., whitepaper, proposal, readme, legal, guide, manifesto, pt, ...), 'all' (default: all), 'snapshot' to refresh cache hashes, or 'clean' to remove Quarto artifacts",
    )

    args = parser.parse_args()

    # Clean special handling
    if "clean" in args.targets:
        docs_root = Path(__file__).parent.absolute()
        success = clean_quarto_artifacts(docs_root)
        sys.exit(0 if success else 1)

    # Snapshot special handling
    if "snapshot" in args.targets:
        # Remove 'snapshot' from the list
        snapshot_targets = [t for t in args.targets if t != "snapshot"]
        # If no other targets, default to all targets
        if not snapshot_targets:
            snapshot_targets = list(BUILD_FUNCTIONS.keys())
        else:
            # Parse comma-separated and validate
            snapshot_targets = parse_targets(snapshot_targets)
            # Handle 'all' keyword
            if "all" in snapshot_targets:
                snapshot_targets = list(BUILD_FUNCTIONS.keys())
            else:
                snapshot_targets = validate_targets(snapshot_targets)
        # Refresh cache for each target
        success = True
        for target in snapshot_targets:
            if not refresh_cache_for_target(target, output_dir=args.output_dir):
                success = False
        sys.exit(0 if success else 1)

    # 'all' special handling
    if "all" in args.targets:
        targets = list(BUILD_FUNCTIONS.keys())
    else:
        targets = parse_targets(args.targets)
        targets = validate_targets(targets)

    # Run build
    success = build_targets(
        targets=targets,
        output_dir=args.output_dir,
        sequence_mode=args.sequence,
        max_jobs=args.jobs,
        single_command=args.single_command,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()