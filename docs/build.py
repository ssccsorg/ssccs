#!/usr/bin/env python3
"""
SSCCS Documentation Builder

Behavior:
  - Single target: runs normally
  - Multiple targets: runs in PARALLEL by default
  - Use --sequence/-s to force sequential execution
  - Use --website to enable website mode (adds --profile website to quarto render)

Project Structure:
  The build system orchestrates the Quarto documents in the `docs/` directory:
      docs/
      ├── build.py              # Build orchestrator (Python 3)
      ├── build.yml             # External configuration (targets, exclusions)
      ├── _quarto.yml           # Quarto project configuration
      ├── _quarto-website.yml   # Website profile configuration
      ├── *.qmd                 # Source documents
      ├── _include/             # Shared fragments (headers, formats, references)
      ├── _utils/               # Build utilities (C2PA signing, path helpers)
      └── _site/                # Generated output (git-ignored)

Caching:
  - Outputs of non‑deterministic formats (pdf, beamer, html, gfm) are cached based on
    a combined SHA‑256 hash that includes the QMD source file and all its dependencies
    (included QMD files and Python files referenced by %run directives). This prevents
    unnecessary re‑renders when the source or any dependency is unchanged, even if the
    generated file would be slightly different (e.g. due to timestamps). The rendered
    output hash is still stored for the `snapshot` command, but it is not used to decide
    whether to render.
  - Cache entries are stored in a `{document_stem}_locked/` directory adjacent to
    each QMD file, with each format saved as `rendered_{format}.txt`. If the combined
    hash matches the cached one, the Quarto render step is skipped.
  - Because the hash includes all dependencies, modifying a single included fragment
    triggers rebuilds only for documents that actually include it—not the entire site.

Snapshot:
  - Use `./build.py snapshot` to refresh cache hashes for all targets.
  - Specify individual targets: `./build.py snapshot whitepaper proposal`
  - **Important:** Snapshot updates the cache only when the combined source hash has not changed
    (i.e., the source and its dependencies are identical to when the cache was created). If the
    combined hash changed, the cache is removed, forcing a rebuild on the next build.
  - This avoids recording stale outputs and eliminates reliance on file timestamps.

External Configuration:
  - Build parameters are externalised to `docs/build.yml`, separating policy from mechanism.
  - The configuration supports target‑specific overrides (e.g., enabling C2PA signing)
    and exclusion patterns (gitignore‑style) to omit certain files from processing.
  - Example:
        target_config:
          whitepaper:
            c2pa: true          # Enable C2PA signing
          proposal:
            c2pa: true
        exclude:
          - "**/README.md"
          - "**/_include/"
  - C2PA signing is performed by `docs/_utils/sign_c2pa.py` when enabled.

Website Mode (--website):
  - Adds `--profile website` to all quarto render commands.
  - Because `quarto render` only supports single‑threaded execution, the `--website` mode
    implements a parallel rendering strategy. Each target is rendered in a fully isolated
    temporary directory that contains a complete copy of the source tree.
  - Architecture:
      base_temp/
      ├── whitepaper/          ← full docs copy
      │   └── _site/           ← quarto render output
      ├── proposal/            ← full docs copy
      │   └── _site/           ← quarto render output
      └── research/            ← full docs copy
          └── _site/           ← quarto render output
  - After all targets complete, their `_site` directories are merged into the final
    `docs/_site` using `merge_dirs()`.
  - Temp directories are automatically cleaned up after the build.
  - **Note:** Website mode requires more disk space (N x docs size for N parallel jobs).
    Use `-j` to limit parallelism if disk space is constrained.

Parallel Execution:
  - Default `--jobs` (-j) is set to **estimated physical CPU cores** (`os.cpu_count() // 2`).
    This accounts for hyperthreading on Intel/AMD CPUs, where logical cores = 2x physical.
    Quarto rendering (LuaLaTeX) is CPU-intensive, so physical core count gives better
    performance per watt and avoids memory pressure from excessive parallelism.
  - Override with `-j N` for manual control.
  - Formats within a target can also be rendered in parallel (separate quarto calls)
    or in a single command (`--single-command` with `--to format1,format2`).

Important:
  - Formats can be rendered either in parallel (each in a separate `quarto render` call)
    or in a single command (with `--to format1,format2`) depending on the `--single-command` flag.
    Concurrency is limited to the number of formats per target when parallel mode is used.
  - A per‑QMD lock ensures that concurrent Quarto renders on the same source file do not interfere
    with each other (avoiding temporary‑directory collisions). This lock is transparent to the user.
  - The script **never** guesses output filenames. It uses `quarto inspect` to obtain
    the exact output path for each format. If that information is unavailable, the
    build fails for that target.
  - Destination filenames in post‑processing (e.g., index.html`, `README.md`) are
    hardcoded only as part of the target‑specific behavior defined in `SPECIAL_CONFIG`.

Usage:
  ./build.py whitepaper                     # Single target
  ./build.py whitepaper readme              # Multiple -> parallel by default
  ./build.py whitepaper,readme,legal        # Multiple -> parallel by default
  ./build.py -s whitepaper proposal readme  # Force sequential execution
  ./build.py -j 2 whitepaper,proposal       # Parallel with 2 jobs
  ./build.py -o ./dist whitepaper proposal  # With output directory
  ./build.py --website                      # Website mode (parallel with isolated docs)
  ./build.py --website -j 3                 # Website mode with 3 parallel jobs
  ./build.py snapshot                       # Refresh cache for all targets
  ./build.py snapshot whitepaper proposal   # Refresh cache for specific targets
  ./build.py --single-command whitepaper     # Use single Quarto command for all formats
  ./build.py clean                          # Remove Quarto artifacts
"""

import argparse
import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Optional, Dict, Callable, Tuple, Any
from functools import lru_cache

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

# Formats that are considered non‑deterministic (cached based on QMD hash only)
NON_DETERMINISTIC_FORMATS = {"pdf", "beamer", "html", "gfm"}

# Patterns that match Quarto‑generated artifacts (used by clean_quarto_artifacts and copy ignore)
IGNORING_ARTIFACT_PATTERNS = [
    "**/__pycache__",
    "**/*.pyc",
    "**/*.pyd",
    "**/*.log",
    "**/*_files",
    "**/*_output",
    "**/*_extensions",
    "**/*_locked",
    "**/*_libs",
    "**/_site",
    # quarto: final artifacts
    "**/*.tex",
    "**/*.pdf",
    "**/*.html",
    # quarto: global
    "**/*.quarto_ipynb",
    "**/*.quarto",
    # c2pa
    "**/*.c2pa",
    "**/*.c2pa_identifier.svg",
]

def ignore_quarto_artifacts() -> Callable[[str, List[str]], List[str]]:
    """
    Return an ignore function suitable for shutil.copytree that excludes
    Quarto-generated artifacts.
    """
    # Convert glob patterns to basename patterns (strip leading '**/')
    basename_patterns = []
    for pat in IGNORING_ARTIFACT_PATTERNS:
        if pat.startswith('**/'):
            pat = pat[3:]
        basename_patterns.append(pat)
    return shutil.ignore_patterns(*basename_patterns)

# Per‑QMD locks to prevent concurrent Quarto renders on the same source file
_QUARTO_FILE_LOCKS = {}
_QUARTO_FILE_LOCKS_LOCK = threading.Lock()

def _lock_for_quarto_file(qmd_path: Path) -> threading.Lock:
    """Return a dedicated lock for the given QMD path."""
    with _QUARTO_FILE_LOCKS_LOCK:
        lock = _QUARTO_FILE_LOCKS.get(qmd_path)
        if lock is None:
            lock = threading.Lock()
            _QUARTO_FILE_LOCKS[qmd_path] = lock
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
def compute_quarto_file_hash_with_deps(file_path: Path) -> str:
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
        data = inspect_quarto_file(path)
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
    collect(file_path.resolve())

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
def inspect_quarto_file(file_path: Path) -> Optional[Dict[str, Any]]:
    """
    Run `quarto inspect` on the QMD file and return the parsed JSON.
    Returns None on failure.
    """
    try:
        result = subprocess.run(
            ["quarto", "inspect", str(file_path)],
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(result.stdout)
    except Exception as e:
        logger.warning(f"Failed to inspect {file_path}: {e}")
        return None


def get_formats_from_quarto_file(file_path: Path) -> List[str]:
    """
    Inspect the QMD file and return a list of output formats defined in its YAML.
    Returns empty list on failure.
    """
    data = inspect_quarto_file(file_path)
    if data is None:
        return []
    formats = data.get("formats", {})
    return list(formats.keys())


def get_format_output_path(file_path: Path, fmt: str) -> Optional[Path]:
    """
    Determine the output file path for a given format using quarto inspect.
    Returns None if format not found or path cannot be determined.
    """
    data = inspect_quarto_file(file_path)
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
        return file_path.parent / output_file
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
    """
    Return the _locked directory for a QMD file.
    Uses the QMD file stem for the cache directory name.
    """
    return qmd_path.parent / f"{qmd_path.stem}_locked"


def get_cache_dir_for_target(qmd_path: Path, target_name: str) -> Path:
    """
    Return the _locked directory considering target naming rules.
    For index.qmd files, the cache dir uses the parent folder name.
    For other files, uses the file stem.
    
    This ensures backward compatibility when target names change.
    """
    if qmd_path.stem.lower() == "index":
        # For index.qmd, use parent folder name for cache dir
        parent_name = qmd_path.parent.name
        if parent_name and parent_name != ".":
            return qmd_path.parent / f"{parent_name}_locked"
    # Default: use file stem
    return qmd_path.parent / f"{qmd_path.stem}_locked"


def get_cache_base() -> Path:
    """
    Return the base directory for the new cache system (_locked).
    """
    return Path(__file__).parent.parent / "_locked"


def format_to_extension(fmt: str) -> str:
    """
    Map a Quarto format to a file extension.
    """
    mapping = {
        "pdf": "pdf",
        "beamer": "pdf",
        "html": "html",
        "gfm": "md",
        "markdown": "md",
    }
    return mapping.get(fmt, fmt)


def get_cached_artifact_path(target_name: str, hash_str: str, fmt: str) -> Path:
    """
    Return the path to a cached artifact file for the given target, hash, and format.
    """
    ext = format_to_extension(fmt)
    return get_cache_base() / target_name / hash_str / f"{target_name}.{ext}"


def find_cached_artifact(target_name: str, hash_str: str, fmt: str) -> Optional[Path]:
    """
    Return the cached artifact path if it exists, otherwise None.
    """
    path = get_cached_artifact_path(target_name, hash_str, fmt)
    if path.exists():
        return path
    return None


def cache_site_directory(target_name: str, hash_str: str, site_dir: Path) -> bool:
    """
    Cache the entire _site directory for a target (including site_libs).
    The directory is copied to _locked/{target}/{hash}/site/.
    Returns True on success, False on error.
    """
    if not site_dir.exists():
        logger.warning(f"Site directory {site_dir} does not exist, nothing to cache.")
        return False
    cache_base = get_cache_base() / target_name / hash_str / "site"
    if cache_base.exists():
        # Remove existing cache to ensure clean copy
        shutil.rmtree(cache_base, ignore_errors=True)
    try:
        shutil.copytree(site_dir, cache_base)
        logger.info(f"Cached site directory for {target_name} at {cache_base}")
        return True
    except Exception as e:
        logger.error(f"Failed to cache site directory for {target_name}: {e}")
        return False


def restore_site_directory(target_name: str, hash_str: str, dest_dir: Path) -> bool:
    """
    Restore a cached site directory to dest_dir (should be the _site directory).
    Returns True on success, False if cache missing or error.
    """
    cache_dir = get_cache_base() / target_name / hash_str / "site"
    if not cache_dir.exists():
        logger.debug(f"No cached site directory for {target_name} ({hash_str})")
        return False
    # Ensure destination parent exists
    dest_dir.parent.mkdir(parents=True, exist_ok=True)
    if dest_dir.exists():
        # Remove existing destination to avoid conflicts
        shutil.rmtree(dest_dir, ignore_errors=True)
    try:
        shutil.copytree(cache_dir, dest_dir)
        logger.info(f"Restored cached site directory for {target_name} to {dest_dir}")
        return True
    except Exception as e:
        logger.error(f"Failed to restore cached site directory for {target_name}: {e}")
        return False


def get_cache_file(qmd_path: Path, fmt: str) -> Path:
    """
    Return the cache file path for a given format.
    For index.qmd files, uses the parent folder name for cache directory.
    """
    if qmd_path.stem.lower() == "index":
        parent_name = qmd_path.parent.name
        if parent_name and parent_name != ".":
            return qmd_path.parent / f"{parent_name}_locked" / f"rendered_{fmt}.txt"
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
    file_path: Path,
    fmt: str,
    target_name: str,
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

    qmd_hash = compute_quarto_file_hash_with_deps(file_path)
    logger.info(f"Checking cache for {target_name} ({fmt}): QMD hash {qmd_hash[:16]}...")
    
    # Check if cached artifact exists
    cached = find_cached_artifact(target_name, qmd_hash, fmt)
    if cached is not None:
        # Cache hit: copy the artifact to the output location
        output_path = get_format_output_path(file_path, fmt)
        if output_path is None:
            logger.warning(f"Cannot determine output path for {target_name} ({fmt}), proceeding with render.")
            return True
        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(cached, output_path)
            logger.info(f"Cache hit for {target_name} ({fmt}), copied cached artifact to {output_path}")
        except Exception as e:
            logger.warning(f"Failed to copy cached artifact for {target_name} ({fmt}): {e}, proceeding with render.")
            return True
        # Also update the old-style cache file for compatibility (optional)
        # For now, we skip updating the old cache.
        return False
    
    # Cache miss: need render
    logger.info(f"Cache miss for {target_name} ({fmt}) – QMD hash {qmd_hash[:16]}...")
    return True




def update_format_cache(file_path: Path, fmt: str, output_path: Path, target_name: Optional[str] = None) -> None:
    """Update cache after successful render of a specific format."""
    qmd_hash = compute_quarto_file_hash_with_deps(file_path)
    output_hash = compute_file_hash(output_path)
    logger.info(f"Updating {fmt} cache for {file_path.name}: output hash {output_hash[:16]}...")
    
    # New cache system: store artifact file in _locked/{target_name}/{hash}/{target_name}.{ext}
    if target_name is not None:
        cache_dir = get_cache_base() / target_name / qmd_hash
        cache_dir.mkdir(parents=True, exist_ok=True)
        ext = format_to_extension(fmt)
        artifact_name = f"{target_name}.{ext}"
        artifact_path = cache_dir / artifact_name
        try:
            shutil.copy2(output_path, artifact_path)
            logger.info(f"Cached artifact for {target_name} ({fmt}) at {artifact_path}")
        except Exception as e:
            logger.warning(f"Failed to cache artifact for {target_name} ({fmt}): {e}")
    
    # Legacy cache system: keep hash pair file for compatibility
    cache_file = get_cache_file(file_path, fmt)
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
    formats = get_formats_from_quarto_file(qmd_path)
    if not formats:
        logger.info(f"Target {target} has no defined output formats, skipping cache refresh.")
        return True

    current_qmd_hash = compute_quarto_file_hash_with_deps(qmd_path)

    for fmt in formats:
        cache_file = get_cache_file(qmd_path, fmt)
        existing_cache = read_hash_pair(cache_file)

        output_path = find_existing_output(qmd_path, fmt, config, output_dir)

        if output_path and output_path.exists():
            # Output exists
            if existing_cache is not None and existing_cache[0] == current_qmd_hash:
                # QMD unchanged – update cache (output may have changed due to non‑determinism)
                update_format_cache(qmd_path, fmt, output_path, target_name=target)
                logger.info(f"Updated {fmt} cache for {target}")
            else:
                # QMD changed or cache missing – we cannot trust the output; remove cache to force rebuild
                if cache_file.exists():
                    cache_file.unlink()
                    logger.info(f"Removed cache file for {target} ({fmt}) – QMD changed or cache missing")
                else:
                    logger.info(f"No cache file for {target} ({fmt}) – will rebuild on next run")
                # Also remove new cache system directory if exists
                if existing_cache is not None:
                    old_hash = existing_cache[0]
                    old_cache_dir = get_cache_base() / target / old_hash
                    if old_cache_dir.exists():
                        shutil.rmtree(old_cache_dir)
                        logger.info(f"Removed new cache directory for {target} ({fmt}) – QMD changed")
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
    patterns = IGNORING_ARTIFACT_PATTERNS
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


# Default special target configurations (can be overridden by external config)
DEFAULT_TARGET_CONFIG: Dict[str, Dict[str, Any]] = {
    "whitepaper": {
        "c2pa": True,
    },
    "proposal": {
        "c2pa": True,
    },
}

# Default exclude patterns (gitignore-style)
DEFAULT_EXCLUDE_PATTERNS: List[str] = []


def load_external_config(config_path: Optional[Path]) -> Dict[str, Any]:
    """
    Load external configuration from YAML file.
    Returns empty dict if file doesn't exist or YAML is not available.
    """
    if config_path is None or not config_path.exists():
        return {}
    
    if not YAML_AVAILABLE:
        logger.warning(f"YAML support not available (install PyYAML). Using default config.")
        return {}
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        logger.info(f"Loaded external config from {config_path}")
        return config or {}
    except Exception as e:
        logger.warning(f"Failed to load config from {config_path}: {e}. Using default config.")
        return {}


def get_exclude_patterns(external_config: Dict[str, Any]) -> List[str]:
    """Get exclude patterns from external config or use defaults."""
    return external_config.get('exclude', DEFAULT_EXCLUDE_PATTERNS)


def get_target_config_from_external(external_config: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Get target configurations from external config or use defaults."""
    # Note: YAML uses 'target_config' key (not 'target')
    target_config = external_config.get('target_config', {})
    # Merge with defaults (external config takes precedence)
    merged = DEFAULT_TARGET_CONFIG.copy()
    for target, config in target_config.items():
        if target in merged:
            merged[target].update(config)
        else:
            merged[target] = config
    return merged


def matches_gitignore_pattern(rel_path: Path, patterns: List[str]) -> bool:
    """
    Check if a relative path matches any of the gitignore-style patterns.
    
    Supports:
    - Glob patterns: **/*.md, **/README.md
    - Directory patterns: **/_include/, **/*_libs/ (trailing slash for directories)
    - Simple patterns: README.md, contributing.md
    
    Pattern matching rules (gitignore-style):
    - "**/" at start matches any directory depth
    - "*" matches any characters except "/"
    - "?" matches single character except "/"
    - Trailing "/" indicates directory-only match
    - Pattern without "/" matches filename at any level
    """
    import fnmatch
    
    path_str = str(rel_path)
    path_str_forward = path_str.replace('\\', '/')  # Normalize to forward slashes
    name = rel_path.name
    
    for pattern in patterns:
        # Normalize pattern
        pattern = pattern.strip()
        if not pattern:
            continue
            
        # Check if pattern is for directories only (trailing slash)
        is_dir_only = pattern.endswith('/')
        if is_dir_only:
            pattern = pattern[:-1]
            # For directory patterns, check if path is under a matching directory
            # Match against each directory component
            parts = path_str_forward.split('/')
            for i, part in enumerate(parts[:-1]):  # Exclude filename
                if fnmatch.fnmatch(part, pattern) or fnmatch.fnmatch(parts[i], pattern.split('/')[-1] if '/' in pattern else pattern):
                    return True
            continue
        
        # Check full path match
        if fnmatch.fnmatch(path_str_forward, pattern):
            return True
        if fnmatch.fnmatch(path_str, pattern):
            return True
            
        # Check filename-only match (for patterns without directory separators)
        if '/' not in pattern and '\\' not in pattern:
            if fnmatch.fnmatch(name, pattern):
                return True
        
        # Check if pattern starts with **/ (matches any depth)
        if pattern.startswith('**/'):
            subpattern = pattern[3:]
            # Match against filename
            if fnmatch.fnmatch(name, subpattern):
                return True
            # Match against any suffix of the path
            parts = path_str_forward.split('/')
            for i in range(len(parts)):
                suffix = '/'.join(parts[i:])
                if fnmatch.fnmatch(suffix, subpattern):
                    return True
        
        # Check if pattern ends with /** (matches anything under directory)
        if pattern.endswith('/**'):
            dirpattern = pattern[:-3]
            if path_str_forward.startswith(dirpattern + '/') or path_str.startswith(dirpattern + '/'):
                return True
    
    return False


def discover_quarto_targets(docs_root: Path, exclude_patterns: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
    """
    Scan docs_root for .qmd and .md files and return target configurations.
    Excludes files/directories matching gitignore-style patterns.
    
    Target naming rules:
      - folder/index.qmd or folder/index.qmd -> target name is 'folder'
      - folder/name.qmd or folder/name.md -> target name is 'name' (or 'folder_name' if conflict)
    
    Args:
        docs_root: Root directory to scan
        exclude_patterns: List of gitignore-style patterns for files/dirs to exclude
    """
    if exclude_patterns is None:
        exclude_patterns = DEFAULT_EXCLUDE_PATTERNS

    targets = {}
    # Process .qmd files first, then .md files
    for ext in ("*.qmd", "*.md"):
        for file_path in docs_root.rglob(ext):
            file_resolved = file_path.resolve()
            
            rel_path = file_path.relative_to(docs_root)
            
            # Check exclude patterns (gitignore-style)
            if matches_gitignore_pattern(rel_path, exclude_patterns):
                logger.info(f"Ignoring {rel_path} (matches exclude pattern)")
                continue
            
            # Determine target name based on file name
            if rel_path.stem.lower() == "index":
                # index.qmd / index.qmd -> use parent folder name as target
                parent = rel_path.parent.name
                if parent and parent != ".":
                    target_name = parent.lower()
                else:
                    # Root level index -> use 'index'
                    target_name = "index"
            else:
                # Regular file -> use stem as target name
                # Sanitize: replace spaces and special chars with underscores
                target_name = rel_path.stem.lower()
                # Replace spaces and multiple spaces with single underscore
                target_name = re.sub(r'\s+', '_', target_name)
                # Replace other special chars that might cause issues
                target_name = re.sub(r'[^a-z0-9_]', '', target_name)

            # Handle name conflicts
            if target_name in targets:
                parent = rel_path.parent.name
                if parent and parent != ".":
                    target_name = f"{parent}_{target_name}"
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


def get_target_config(docs_root: Path, external_config: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
    """
    Return merged configuration: target_config updates discovered defaults.
    
    Note: target_config in YAML is optional - targets not listed still get built with defaults.
    
    Args:
        docs_root: Root directory of documentation
        external_config: Optional external configuration dictionary
    """
    if external_config is None:
        external_config = {}
    
    exclude_patterns = get_exclude_patterns(external_config)
    target_config = get_target_config_from_external(external_config)
    
    discovered = discover_quarto_targets(docs_root, exclude_patterns)
    # Merge target config (updates discovered entries)
    # Note: Unlike before, missing targets in config are NOT errors - they just use defaults
    for target, config in target_config.items():
        if target not in discovered:
            logger.warning(f"Target '{target}' from config not found in discovered files (may be excluded by pattern)")
            continue
        # Update discovered config with target config, preserving missing keys
        discovered[target].update(config)
    
    # Validate target names for configured targets only
    for target, config in target_config.items():
        if target not in discovered:
            continue
        qmd_path = Path(discovered[target]["qmd"])
        if qmd_path.stem.lower() == "index":
            expected = qmd_path.parent.name.lower()
        else:
            expected = qmd_path.stem.lower()
        
        if target.lower() != expected:
            logger.error(
                f"Target name '{target}' does not match source file path '{qmd_path}' "
                f"(expected target name '{expected}')"
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
    docs_root: Path,
    website: bool = False,
    target_name: Optional[str] = None
) -> bool:
    """Render each format in its own Quarto command, running in parallel threads."""
    def render_single_format(fmt: str) -> bool:
        lock = _lock_for_quarto_file(qmd_path)
        with lock:
            quarto_cmd = ["quarto", "render", str(qmd_path), "--to", fmt]
            if website:
                quarto_cmd.append("--profile")
                quarto_cmd.append("website")
            if not run_command(quarto_cmd, cwd=docs_root):
                logger.error(f"Quarto render failed for {qmd_path.name} (format {fmt}).")
                return False
            if fmt in NON_DETERMINISTIC_FORMATS:
                output_path = format_output_paths[fmt]
                if output_path.exists():
                    update_format_cache(qmd_path, fmt, output_path, target_name=target_name)
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
    docs_root: Path,
    website: bool = False,
    target_name: Optional[str] = None
) -> bool:
    """Render all formats using a single Quarto command (--to fmt1,fmt2)."""
    lock = _lock_for_quarto_file(qmd_path)
    with lock:
        formats_str = ",".join(formats)
        quarto_cmd = ["quarto", "render", str(qmd_path), "--to", formats_str]
        if website:
            quarto_cmd.append("--profile")
            quarto_cmd.append("website")
        if not run_command(quarto_cmd, cwd=docs_root):
            logger.error(f"Quarto render failed for {qmd_path.name} (formats {formats_str}).")
            return False
        # Update cache for each rendered format
        for fmt in formats:
            if fmt in NON_DETERMINISTIC_FORMATS:
                output_path = format_output_paths[fmt]
                if output_path.exists():
                    update_format_cache(qmd_path, fmt, output_path, target_name=target_name)
                else:
                    logger.warning(f"Expected output {output_path} not found after render for {fmt}")
        return True


def _render_formats(
    qmd_path: Path,
    formats: List[str],
    format_output_paths: Dict[str, Path],
    docs_root: Path,
    single_command: bool,
    website: bool = False,
    target_name: Optional[str] = None
) -> bool:
    """Dispatch to the appropriate rendering strategy."""
    if single_command:
        return _render_formats_single(qmd_path, formats, format_output_paths, docs_root, website, target_name)
    else:
        return _render_formats_parallel(qmd_path, formats, format_output_paths, docs_root, website, target_name)


def build_generic(target: str, config: Dict[str, Any], output_dir: Optional[Path] = None, single_command: bool = False, website: bool = False, docs_root: Optional[Path] = None) -> bool:
    """
    Generic build function that renders a .qmd or .md file and performs optional post‑processing.
    Formats are rendered either in parallel (separate commands) or in a single command
    depending on the `single_command` flag.
    If `website` is True, adds `--profile website` to Quarto render commands.
    
    Important: In website mode, formats are NOT rendered individually. Instead, quarto render
    is called without --to to let Quarto handle all formats defined in the document's YAML.
    This is required because website mode uses a shared project configuration.
    
    For .md files without explicit format configuration, quarto render is called without --to
    to let Quarto handle the file natively.
    
    If `docs_root` is provided, use it as the docs directory (for isolated mode).
    """
    logger.info(f"Building {target}...")
    if docs_root is None:
        docs_root = Path(__file__).parent.absolute()

    source_path = docs_root / config["qmd"]
    if not source_path.exists():
        logger.error(f"Source file not found: {source_path}")
        return False

    # Check if this is a .md file (not .qmd)
    is_md_file = source_path.suffix.lower() == ".md"
    
    # For .md files without explicit 'to' config, render directly without format inspection
    if is_md_file and config.get("to") is None:
        # In website mode, we keep the simple render (no caching) because output location differs
        if website:
            fmt = "html"
            qmd_hash = compute_quarto_file_hash_with_deps(source_path)
            if not should_render_format(source_path, fmt, target, config, output_dir):
                logger.info(f"Cache hit for {target} ({fmt}), skipping website render.")
                # Copy cached artifact to _site subdirectory if different
                output_path = get_format_output_path(source_path, fmt)
                if docs_root and output_path:
                    try:
                        rel = source_path.relative_to(docs_root)
                        site_path = docs_root / "_site" / rel.with_suffix('.html')
                        if site_path != output_path and not site_path.exists():
                            cached = find_cached_artifact(target, qmd_hash, fmt)
                            if cached:
                                site_path.parent.mkdir(parents=True, exist_ok=True)
                                shutil.copy2(cached, site_path)
                    except ValueError:
                        pass
                # Restore cached site directory (including site_libs)
                site_dir = docs_root / "_site"
                restore_site_directory(target, qmd_hash, site_dir)
                logger.info(f"{target} build completed successfully (native Markdown, website).")
                return True
            logger.info(f"Rendering {source_path.name} as native Markdown (website mode)")
            quarto_cmd = ["quarto", "render", str(source_path), "--profile", "website"]
            if not run_command(quarto_cmd, cwd=docs_root):
                logger.error(f"Quarto render failed for {source_path.name}.")
                return False
            # Cache the rendered HTML artifact
            output_path = get_format_output_path(source_path, fmt)
            if output_path and output_path.exists():
                update_format_cache(source_path, fmt, output_path, target_name=target)
            else:
                # Try under _site subdirectory
                if docs_root:
                    try:
                        rel = source_path.relative_to(docs_root)
                        site_path = docs_root / "_site" / rel.with_suffix('.html')
                        if site_path.exists():
                            update_format_cache(source_path, fmt, site_path, target_name=target)
                    except ValueError:
                        pass
            # Cache the entire _site directory for future reuse
            site_dir = docs_root / "_site"
            cache_site_directory(target, qmd_hash, site_dir)
            logger.info(f"{target} build completed successfully (native Markdown, website).")
            return True
        
        # Non‑website mode: apply _locked cache policy
        # Determine formats via inspect_quarto_file (may be empty)
        formats = get_formats_from_quarto_file(source_path)
        if not formats:
            # No YAML formats, assume default HTML
            formats = ["html"]
        
        # Determine which formats need rendering
        formats_to_render = []
        for fmt in formats:
            if should_render_format(source_path, fmt, target, config, output_dir):
                formats_to_render.append(fmt)
        
        if not formats_to_render:
            logger.info(f"All formats for {target} are up‑to‑date, skipping render.")
            return True
        
        # Render all formats with a single quarto render (no --to)
        logger.info(f"Rendering {source_path.name} as native Markdown (formats: {', '.join(formats)})")
        quarto_cmd = ["quarto", "render", str(source_path)]
        if not run_command(quarto_cmd, cwd=docs_root):
            logger.error(f"Quarto render failed for {source_path.name}.")
            return False
        
        # Update cache for each format that was rendered
        for fmt in formats:
            output_path = get_format_output_path(source_path, fmt)
            if output_path and output_path.exists():
                update_format_cache(source_path, fmt, output_path, target_name=target)
        
        logger.info(f"{target} build completed successfully (native Markdown).")
        return True

    # For .qmd files or .md with explicit 'to' config, use full format handling
    qmd_path = source_path
    
    # Determine generated files early for caching
    # For index.qmd files, use parent folder name for output files (e.g., whitepaper.pdf)
    # For other files, use the file stem
    if qmd_path.stem.lower() == "index":
        parent_name = qmd_path.parent.name
        stem = parent_name if parent_name and parent_name != "." else qmd_path.stem
    else:
        stem = qmd_path.stem
    parent = qmd_path.parent

    # Determine formats to render
    target_format = config.get("to")
    if target_format is None:
        # inspect the QMD to get all formats
        formats = get_formats_from_quarto_file(qmd_path)
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

    # Determine which formats need rendering (only for non‑website mode)
    formats_to_render = []
    if not website:
        for fmt in formats:
            if should_render_format(qmd_path, fmt, target, config, output_dir):
                formats_to_render.append(fmt)

    # In website mode, render without --to to let Quarto handle all formats from YAML
    # This is required because website mode uses shared project configuration
    if website:
        qmd_hash = compute_quarto_file_hash_with_deps(qmd_path)
        all_cached = True
        for fmt in formats:
            if find_cached_artifact(target, qmd_hash, fmt) is None:
                all_cached = False
                break
        if all_cached:
            logger.info(f"All formats for {target} are cached, skipping website render.")
            # Copy cached artifacts to output locations
            for fmt in formats:
                cached = find_cached_artifact(target, qmd_hash, fmt)
                if cached:
                    output_path = format_output_paths.get(fmt)
                    if output_path:
                        output_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(cached, output_path)
                    # Also copy to _site subdirectory if different
                    if docs_root and output_path:
                        try:
                            rel = output_path.relative_to(docs_root)
                            site_path = docs_root / "_site" / rel
                            if site_path != output_path and not site_path.exists():
                                site_path.parent.mkdir(parents=True, exist_ok=True)
                                shutil.copy2(cached, site_path)
                        except ValueError:
                            pass
            # Skip the actual Quarto render but continue with post‑processing
            # Restore cached site directory (including site_libs)
            site_dir = docs_root / "_site"
            restore_site_directory(target, qmd_hash, site_dir)
            pass
        else:
            # Not all formats cached, proceed with render
            logger.info(f"Rendering {source_path.name} in website mode (no --to, all formats from YAML)")
            quarto_cmd = ["quarto", "render", str(source_path), "--profile", "website"]
            if not run_command(quarto_cmd, cwd=docs_root):
                logger.error(f"Quarto render failed for {source_path.name} (website mode).")
                return False
            # Cache artifacts for each format
            for fmt in formats:
                output_path = format_output_paths.get(fmt)
                if output_path and output_path.exists():
                    update_format_cache(qmd_path, fmt, output_path, target_name=target)
                else:
                    # Try under _site subdirectory
                    if docs_root:
                        try:
                            rel = output_path.relative_to(docs_root)
                            site_path = docs_root / "_site" / rel
                            if site_path.exists():
                                update_format_cache(qmd_path, fmt, site_path, target_name=target)
                        except (ValueError, AttributeError):
                            pass
            # Cache the entire _site directory for future reuse
            site_dir = docs_root / "_site"
            cache_site_directory(target, qmd_hash, site_dir)
    else:
        if formats_to_render:
            logger.info(f"Rendering {len(formats_to_render)} format(s) for {target}")
            if not _render_formats(qmd_path, formats_to_render, format_output_paths, docs_root, single_command, website, target_name=target):
                return False
        else:
            logger.info(f"All formats for {target} are up‑to‑date, skipping render.")

    # Step 2: C2PA signing (if enabled) – assumes PDF exists at format_output_paths['pdf'] or similar
    logger.info(f"format_output_paths keys: {list(format_output_paths.keys())}")
    if config.get("c2pa"):
        # Determine possible PDF paths
        candidates = []
        primary = format_output_paths.get('pdf') or format_output_paths.get('beamer')
        if primary:
            candidates.append(primary)
            if website:
                # Website output goes to _site subdirectory
                try:
                    rel = primary.relative_to(docs_root)
                    candidates.append(docs_root / "_site" / rel)
                except ValueError:
                    pass
        # Also consider moved location via copy_pdf (if config has copy_pdf)
        if config.get("copy_pdf") and output_dir:
            dest_dir = Path(output_dir).absolute() if output_dir else docs_root
            candidates.append(dest_dir / f"{stem}.pdf")
        # Try each candidate
        pdf_path = None
        for cand in candidates:
            if cand and cand.exists():
                pdf_path = cand
                break
        logger.info(f"pdf_path candidates: {candidates}, selected: {pdf_path}, exists: {pdf_path.exists() if pdf_path else False}")
        if pdf_path and pdf_path.exists():
            # For index.qmd files, use the QMD file stem (index) for C2PA files
            # since the manifest is named after the QMD file, not the target
            c2pa_stem = qmd_path.stem
            manifest_path = parent / f"{c2pa_stem}.c2pa_manifest.json"
            # Place .c2pa file next to the PDF (so it appears in the same output directory)
            output_c2pa = pdf_path.parent / f"{c2pa_stem}.c2pa"
            # Ensure parent directory exists
            output_c2pa.parent.mkdir(parents=True, exist_ok=True)
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
        # Determine possible PDF paths (same logic as signing)
        candidates = []
        primary = format_output_paths.get('pdf') or format_output_paths.get('beamer')
        if primary:
            candidates.append(primary)
            if website:
                # Website output goes to _site subdirectory
                try:
                    rel = primary.relative_to(docs_root)
                    candidates.append(docs_root / "_site" / rel)
                except ValueError:
                    pass
        # Try each candidate
        pdf_path = None
        for cand in candidates:
            if cand and cand.exists():
                pdf_path = cand
                break
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
EXTERNAL_CONFIG: Dict[str, Any] = {}
TARGET_CONFIG: Dict[str, Dict[str, Any]] = {}
BUILD_FUNCTIONS: Dict[str, Callable[..., bool]] = {}
OUTPUT_DIR_TARGETS: set = set()

def initialize_config(config_path: Optional[Path]) -> None:
    """Initialize global configuration from external file."""
    global EXTERNAL_CONFIG, TARGET_CONFIG, BUILD_FUNCTIONS, OUTPUT_DIR_TARGETS
    EXTERNAL_CONFIG = load_external_config(config_path)
    TARGET_CONFIG = get_target_config(DOCS_ROOT, EXTERNAL_CONFIG)
    
    # Build function mapping per target (auto-generated from TARGET_CONFIG)
    BUILD_FUNCTIONS = {}
    for target, config in TARGET_CONFIG.items():
        # Create a closure that captures target and config
        def make_builder(tgt, cfg):
            def builder(output_dir: Optional[Path] = None, single_command: bool = False, website: bool = False, docs_root: Optional[Path] = None) -> bool:
                return build_generic(tgt, cfg, output_dir, single_command, website, docs_root)
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


def build_single_target(target: str, output_dir: Optional[Path], single_command: bool, website: bool = False) -> Tuple[str, bool]:
    """Wrapper to run a single build function and return (target_name, success)."""
    logger.info(f"Starting build: {target}")
    func = BUILD_FUNCTIONS[target]
    try:
        if target in OUTPUT_DIR_TARGETS:
            success = func(output_dir=output_dir, single_command=single_command, website=website)
        else:
            success = func(single_command=single_command, website=website)
        logger.info(f"Finished build: {target} -> {'✓' if success else '✗'}")
        return target, success
    except Exception as e:
        logger.error(f"Exception while building {target}: {e}")
        return target, False


def merge_dirs(src: Path, dst: Path) -> bool:
    """
    Merge contents of src directory into dst directory.
    Overwrites existing files, creates missing directories.
    Does NOT delete files in dst that don't exist in src
    (because we're merging multiple sources, not mirroring one).
    """
    try:
        dst.mkdir(parents=True, exist_ok=True)
        for item in src.iterdir():
            src_item = item
            dst_item = dst / item.name
            if item.is_dir():
                if dst_item.exists():
                    merge_dirs(src_item, dst_item)
                else:
                    shutil.copytree(src_item, dst_item)
            else:
                shutil.copy2(src_item, dst_item)
        return True
    except Exception as e:
        logger.error(f"Failed to merge {src} into {dst}: {e}")
        return False


def _render_target_isolated(target: str, output_dir: Optional[Path], single_command: bool, website: bool, temp_docs: Path) -> bool:
    """
    Render a single target in isolation using a complete copy of the docs folder.
    This prevents resource conflicts when running multiple quarto renders in parallel.
    """
    logger.info(f"Rendering {target} in isolated docs directory {temp_docs}")
    
    try:
        # Build in the isolated docs directory
        func = BUILD_FUNCTIONS.get(target)
        if func is None:
            logger.error(f"Unknown target: {target}")
            return False
        
        # For isolated mode, we run the build in the temp_docs directory
        # The output will go to temp_docs/_site
        success = func(output_dir=temp_docs / "_site", single_command=single_command, website=website, docs_root=temp_docs)
        return success
    except Exception as e:
        logger.error(f"Exception while rendering {target}: {e}")
        return False


def build_targets(
    targets: List[str],
    output_dir: Optional[Path],
    sequence_mode: bool,
    max_jobs: int,
    single_command: bool,
    website: bool = False
) -> bool:
    """
    Build multiple targets.

    Behavior:
      - If sequence_mode=True: run sequentially regardless of target count
      - If sequence_mode=False and len(targets) > 1: run in parallel (default)
      - If sequence_mode=False and len(targets) == 1: run normally (no threading overhead)
      - If website=True and parallel: use isolated temp directories for each target, then merge
    
    In website mode with parallel execution, each target renders to its own temp directory
    to avoid site_libs conflicts, then results are merged into the final _site directory.
    
    Important: The _site output directory is cleaned before building to ensure no stale files remain.
    """
    if not targets:
        logger.info("No targets specified. Nothing to build.")
        return True

    results: Dict[str, bool] = {}
    
    # Clean _site directory before building to ensure no stale files remain
    final_site = output_dir if output_dir else (DOCS_ROOT / "_site")
    if final_site.exists():
        logger.info(f"Cleaning existing _site directory: {final_site}")
        try:
            shutil.rmtree(final_site)
            logger.info(f"Removed existing _site directory")
        except Exception as e:
            logger.error(f"Failed to remove existing _site directory: {e}")
            return False

    # In website mode with parallel execution:
    # Each target gets a complete copy of the docs folder in a temp directory
    # This ensures complete isolation of Quarto's project resources
    if website and (not sequence_mode) and (len(targets) > 1):
        logger.info("Website mode: using isolated docs copies for parallel rendering...")
        
        # Create base temp directory
        base_temp = Path(tempfile.mkdtemp(prefix="quarto_website_"))
        target_temp_dirs: Dict[str, Path] = {}
        
        try:
            # Copy entire docs folder for each target in parallel
            def copy_for_target(t: str) -> Tuple[str, Path]:
                temp_docs = base_temp / t
                logger.info(f"Copying docs to {temp_docs} for {t}...")
                shutil.copytree(DOCS_ROOT, temp_docs, ignore=ignore_quarto_artifacts())
                return t, temp_docs

            target_temp_dirs = {}
            with ThreadPoolExecutor(max_workers=max_jobs) as executor:
                future_to_target = {executor.submit(copy_for_target, t): t for t in targets}
                for future in as_completed(future_to_target):
                    target = future_to_target[future]
                    try:
                        t, temp_docs = future.result()
                        target_temp_dirs[t] = temp_docs
                    except Exception as e:
                        logger.error(f"Failed to copy docs for {target}: {e}")
                        # Clean up any already copied directories
                        for td in target_temp_dirs.values():
                            if td.exists():
                                shutil.rmtree(td, ignore_errors=True)
                        shutil.rmtree(base_temp, ignore_errors=True)
                        return False
            
            # Render all targets in parallel, each in its own isolated docs copy
            with ThreadPoolExecutor(max_workers=max_jobs) as executor:
                futures = {
                    executor.submit(
                        _render_target_isolated, t, output_dir, single_command, website, target_temp_dirs[t]
                    ): t
                    for t in targets
                }
                for future in as_completed(futures):
                    target = futures[future]
                    try:
                        success = future.result()
                        results[target] = success
                    except Exception as e:
                        logger.error(f"Exception while rendering {target}: {e}")
                        results[target] = False
            
            # Merge all successful _site directories into final output
            final_output = output_dir if output_dir else (DOCS_ROOT / "_site")
            
            # Determine which targets succeeded before merging
            succeeded = [t for t, s in results.items() if s]
            failed = [t for t, s in results.items() if not s]
            
            # Clean the output directory once before merging (ensures freshness)
            if final_output.exists():
                logger.info(f"Cleaning existing output directory {final_output}")
                shutil.rmtree(final_output)
            
            final_output.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Merging {len(succeeded)} successful targets into {final_output}...")
            # Sort succeeded so that 'index' target is merged last (its index.html should prevail)
            sorted_succeeded = sorted(succeeded, key=lambda x: (x == 'index', x))
            # Iterate over a copy because we may modify results
            for target in sorted_succeeded:
                temp_docs = target_temp_dirs[target]
                temp_site = temp_docs / "_site"
                if temp_site.exists():
                    if not merge_dirs(temp_site, final_output):
                        logger.warning(f"Failed to merge {target} output into {final_output}")
                        results[target] = False
            
            
            # Summary
            succeeded = [t for t, s in results.items() if s]
            failed = [t for t, s in results.items() if not s]
            if failed:
                if succeeded:
                    logger.info(f"Successful targets: {succeeded}")
                logger.error(f"Failed targets: {failed}")
                # Clean up partial merge results
                if final_output.exists():
                    logger.info(f"Cleaning partial output directory {final_output} due to failures")
                    shutil.rmtree(final_output)
                return False
            
            logger.info(f"All targets completed successfully: {list(results.keys())}")
            return True
            
        finally:
            # Clean up temp directory
            logger.info(f"Cleaning up temp directory {base_temp}")
            try:
                shutil.rmtree(base_temp)
            except Exception as e:
                logger.warning(f"Failed to clean up temp dir {base_temp}: {e}")

    # Non-website or sequential mode: use standard execution
    use_parallel = (not sequence_mode) and (len(targets) > 1)

    if use_parallel:
        logger.info(f"Running {len(targets)} targets in parallel (max_jobs={max_jobs})")
        with ThreadPoolExecutor(max_workers=max_jobs) as executor:
            futures = {
                executor.submit(build_single_target, t, output_dir, single_command, website): t
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
            _, success = build_single_target(target, output_dir, single_command, website)
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
  - Use --website to enable website mode (--profile website) with isolated parallel docs.

Website Mode:
  - Each target gets a complete isolated copy of the docs folder in a temp directory.
  - After rendering, all _site directories are merged into the final output.
  - Prevents resource conflicts (site_libs, .quarto cache) in parallel website builds.
  - Requires more disk space (N x docs size for N parallel jobs).

Snapshot:
  - Use `%(prog)s snapshot` to refresh cache hashes for all targets.
  - Specify individual targets: `%(prog)s snapshot whitepaper proposal`
  - Updates cache entries with current file hashes; missing PDFs cause cache removal.
  - **Only updates if the QMD hash has not changed** – otherwise removes cache.

Clean:
  - Use `%(prog)s clean` to remove Quarto‑generated directories:
      **/*_files, **/*_output, **/*_extensions, **/*_locked, **/_site
  - Deletes all matching directories and files recursively.

Examples:
  %(prog)s whitepaper                     # Single target
  %(prog)s whitepaper readme              # Multiple -> parallel by default
  %(prog)s whitepaper,readme,legal        # Multiple -> parallel by default
  %(prog)s -s whitepaper proposal readme  # Force sequential execution
  %(prog)s -j 2 whitepaper,proposal       # Parallel with 2 jobs
  %(prog)s -o ./dist whitepaper proposal  # Specify output directory
  %(prog)s --website                      # Website mode (parallel with isolated docs)
  %(prog)s --website -j 3                 # Website mode with 3 parallel jobs
  %(prog)s snapshot                       # Refresh cache for all targets
  %(prog)s snapshot whitepaper proposal   # Refresh cache for specific targets
  %(prog)s clean                          # Remove Quarto artifacts
  %(prog)s --single-command whitepaper     # Use single Quarto command for all formats
  %(prog)s --config build.yml whitepaper   # Use external configuration file
  %(prog)s -c ./custom-config.yml whitepaper  # Specify custom config path
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
    # Default max_jobs to physical core count for optimal parallel performance.
    # Uses multiprocessing to get logical cores, then estimates physical cores
    # by dividing by 2 (accounts for hyperthreading on Intel/AMD CPUs).
    # Falls back to os.cpu_count() if multiprocessing is unavailable.
    _logical_cores = os.cpu_count() or 4
    _default_jobs = max(1, _logical_cores // 2)
    parser.add_argument(
        "--jobs", "-j",
        type=int,
        default=_default_jobs,
        help=f"Max number of parallel jobs (default: {_default_jobs} = estimated physical cores, only used in parallel mode)",
    )
    parser.add_argument(
        "--single-command",
        action="store_true",
        help="Render all formats in a single Quarto command (--to fmt1,fmt2) instead of separate commands",
    )
    parser.add_argument(
        "--website",
        action="store_true",
        help="Use Quarto website profile (adds --profile website to render commands)",
    )
    parser.add_argument(
        "--config", "-c",
        type=Path,
        default=None,
        help="Path to external YAML configuration file (default: build.yml in docs root)",
    )
    parser.add_argument(
        "targets",
        nargs="*",
        default=["all"],
        help="Build targets: any discovered .qmd file (e.g., whitepaper, proposal, readme, legal, guide, manifesto, pt, ...), 'all' (default: all), 'snapshot' to refresh cache hashes, or 'clean' to remove Quarto artifacts",
    )

    args = parser.parse_args()

    # Initialize configuration from external file
    config_path = args.config
    if config_path is None:
        # Default: look for build.yml in docs root
        default_config = DOCS_ROOT / "build.yml"
        if default_config.exists():
            config_path = default_config
    
    initialize_config(config_path)

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
        website=args.website,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()