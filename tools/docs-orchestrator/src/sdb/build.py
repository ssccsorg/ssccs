"""
SDBS build -- Quarto build orchestration.

This is the main orchestration module. It builds on top of the extracted
sub-modules (config, hash, quarto, render, artifact, merge) to implement
the full build pipeline: discovery, caching, rendering, artifact generation,
merge, and cleanup.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from .artifact import (
    get_cached_artifact_path as _get_cached_artifact_path,
    get_enabled_handlers,
    get_linked_artifact_extensions,
    find_cached_artifact as _find_cached_artifact,
)
from .config import (
    BUILD_TEMP_DIR,
    JUPYTER_CACHE_DIR,
    ConfigManager,
    CleanupManager,
)
from .hash import HashManager
from .merge import merge_dirs
from .quarto import QuartoInspector
from .render import (
    NON_DETERMINISTIC_FORMATS,
    CommandRunner,
    _render_formats,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Module-level global mutable state
# ---------------------------------------------------------------------------

EXTERNAL_CONFIG: Dict[str, Any] = {}
TARGET_CONFIG: Dict[str, Dict[str, Any]] = {}
BUILD_FUNCTIONS: Dict[str, Callable[..., bool]] = {}
OUTPUT_DIR_TARGETS: set = set()
_INITIAL_CACHED_TARGETS: Optional[set] = None
PROJECT_ROOT: Optional[Path] = None  # Set by initialize_config


# ---------------------------------------------------------------------------
# Standalone function aliases that delegate to extracted module classes
# ---------------------------------------------------------------------------


def ignore_quarto_artifacts() -> Callable[[str, list[str]], set[str]]:
    return CleanupManager().ignore_quarto_artifacts()


def compute_file_hash(path: Path) -> str:
    return HashManager.compute_file_hash(path)


def compute_quarto_file_hash_with_deps(file_path: Path, docs_root: Path) -> str:
    return HashManager.compute_quarto_file_hash_with_deps(file_path, docs_root)


def target_produces_pdf(config: Dict[str, Any]) -> bool:
    return QuartoInspector.target_produces_pdf(config)


def inspect_quarto_file(file_path: Path) -> Optional[Dict[str, Any]]:
    return QuartoInspector.inspect(file_path)


def get_formats_from_quarto_file(file_path: Path) -> List[str]:
    return QuartoInspector.get_formats(file_path)


def get_format_output_path(file_path: Path, fmt: str) -> Optional[Path]:
    return QuartoInspector.get_output_path(file_path, fmt)


def get_moved_path_for_format(
    qmd_path: Path,
    fmt: str,
    config: Optional[Dict[str, Any]],
    output_dir: Optional[Path],
    docs_root: Path,
    source_path: Path,
) -> Optional[Path]:
    return QuartoInspector.get_moved_path(
        qmd_path, fmt, config, output_dir, docs_root, source_path
    )


def find_existing_output(
    qmd_path: Path,
    fmt: str,
    config: Optional[Dict[str, Any]],
    output_dir: Optional[Path],
    docs_root: Path,
) -> Optional[Path]:
    return QuartoInspector.find_existing_output(
        qmd_path, fmt, config, output_dir, docs_root
    )


def get_cache_dir(qmd_path: Path) -> Path:
    return QuartoInspector.get_cache_dir(qmd_path)


def get_cache_dir_for_target(qmd_path: Path, target_name: str) -> Path:
    return QuartoInspector.get_cache_dir_for_target(qmd_path, target_name)


def get_cache_base(docs_root: Optional[Path] = None) -> Path:
    """Return the system-wide cache base directory.

    Uses the module-level ``PROJECT_ROOT`` (set by ``initialize_config``)
    when available, falling back to ``docs_root.parent``.
    """
    if PROJECT_ROOT is not None:
        return PROJECT_ROOT / "_cached"
    if docs_root is not None:
        return docs_root.parent / "_cached"
    return Path.cwd().parent / "_cached"


def format_to_extension(fmt: str) -> str:
    return QuartoInspector.format_to_extension(fmt)


def clean_quarto_artifacts(docs_root: Path) -> bool:
    return CleanupManager().clean(docs_root)


def load_external_config(config_path: Optional[Path]) -> Dict[str, Any]:
    return ConfigManager.load_external_config(config_path)


def get_exclude_patterns(external_config: Dict[str, Any]) -> List[str]:
    return ConfigManager.get_exclude_patterns(external_config)


def get_target_config_from_external(
    external_config: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    return ConfigManager.get_target_config_from_external(external_config)


def matches_gitignore_pattern(rel_path: Path, patterns: List[str]) -> bool:
    return ConfigManager.matches_gitignore_pattern(rel_path, patterns)


def discover_quarto_targets(
    docs_root: Path, exclude_patterns: Optional[List[str]] = None
) -> Dict[str, Dict[str, Any]]:
    return ConfigManager.discover_quarto_targets(docs_root, exclude_patterns)


def get_target_config(
    docs_root: Path, external_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Dict[str, Any]]:
    return ConfigManager.get_target_config(docs_root, external_config)


def run_command(cmd: List[str], cwd: Optional[Path] = None) -> bool:
    return CommandRunner.run(cmd, cwd)


def get_cached_artifact_path(
    target_name: str,
    hash_str: str,
    fmt: str,
    docs_root: Path,
    linked_ext: Optional[str] = None,
) -> Path:
    # Use PROJECT_ROOT for cache paths (consistent across website mode)
    project_root = PROJECT_ROOT if PROJECT_ROOT else docs_root.parent
    return _get_cached_artifact_path(
        target_name, hash_str, fmt, project_root, linked_ext=linked_ext
    )


def find_cached_artifact(
    target_name: str,
    hash_str: str,
    fmt: str,
    docs_root: Path,
    linked_ext: Optional[str] = None,
) -> Optional[Path]:
    project_root = PROJECT_ROOT if PROJECT_ROOT else docs_root.parent
    return _find_cached_artifact(
        target_name, hash_str, fmt, project_root, linked_ext=linked_ext
    )


# ---------------------------------------------------------------------------
# Caching helpers
# ---------------------------------------------------------------------------


def capture_initial_cached_targets(docs_root: Path) -> None:
    """
    Capture the set of cached target names before build starts.
    This is used to detect if the document set has changed during the build.
    """
    global _INITIAL_CACHED_TARGETS
    cache_base = get_cache_base(docs_root)
    if not cache_base.exists():
        _INITIAL_CACHED_TARGETS = set()
    else:
        _INITIAL_CACHED_TARGETS = {d.name for d in cache_base.iterdir() if d.is_dir()}


def get_initial_cached_targets() -> set:
    """Return the snapshot of cached target names captured before build starts."""
    if _INITIAL_CACHED_TARGETS is None:
        return set()
    return _INITIAL_CACHED_TARGETS


def should_rerender_for_sidebar(build_targets: set, docs_root: Path) -> bool:
    """
    Check if HTML must be re-rendered to update sidebar.
    Returns True if:
      - Any target in the build set is not yet cached (new files added), OR
      - Any cached target is not in the build set (files deleted/changed)

    This ensures the sidebar is updated whenever the document set changes,
    whether by addition, deletion, or modification of source files.
    """
    cached_targets = get_initial_cached_targets()
    has_new_files = not build_targets.issubset(cached_targets)
    has_deleted_files = not cached_targets.issubset(build_targets)
    return has_new_files or has_deleted_files


def cache_site_directory(target_name: str, hash_str: str, site_dir: Path, docs_root: Path) -> bool:
    """
    Cache the entire _site directory for a target (including site_libs).
    The directory is copied to _cached/{target}/{hash}/site/.
    Returns True on success, False on error.
    """
    if not site_dir.exists():
        logger.warning(f"Site directory {site_dir} does not exist, nothing to cache.")
        return False
    cache_base = get_cache_base(docs_root) / target_name / hash_str / "site"
    if cache_base.exists():
        shutil.rmtree(cache_base, ignore_errors=True)
    try:
        shutil.copytree(site_dir, cache_base)
        logger.info(f"Cached site directory for {target_name} at {cache_base}")
        return True
    except Exception as e:
        logger.error(f"Failed to cache site directory for {target_name}: {e}")
        return False


def restore_site_directory(target_name: str, hash_str: str, dest_dir: Path, docs_root: Path) -> bool:
    """
    Restore a cached site directory to dest_dir (should be the _site directory).
    Returns True on success, False if cache missing or error.
    """
    cache_dir = get_cache_base(docs_root) / target_name / hash_str / "site"
    if not cache_dir.exists():
        logger.debug(f"No cached site directory for {target_name} ({hash_str})")
        return False
    dest_dir.parent.mkdir(parents=True, exist_ok=True)
    if dest_dir.exists():
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
            return qmd_path.parent / f"{parent_name}_cached" / f"rendered_{fmt}.txt"
    return get_cache_dir(qmd_path) / f"rendered_{fmt}.txt"


def read_hash_pair(cache_file: Path) -> Optional[Tuple[str, str]]:
    """
    Read hash pair from cache file.
    Returns (qmd_hash, output_hash) or None if missing/malformed.
    """
    if not cache_file.exists():
        return None
    try:
        with open(cache_file, "r") as f:
            line = f.read().strip()
        if "_" in line:
            a, b = line.split("_", 1)
            if len(a) == 64 and len(b) == 64:
                return (a, b)
    except Exception:
        pass
    return None


def write_hash_pair(cache_file: Path, qmd_hash: str, output_hash: str) -> None:
    """Write hash pair to cache file."""
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_file, "w") as f:
        f.write(f"{qmd_hash}_{output_hash}")


# ---------------------------------------------------------------------------
# Render decision helpers
# ---------------------------------------------------------------------------


def should_render_format(
    file_path: Path,
    fmt: str,
    target_name: str,
    docs_root: Path,
    config: Optional[Dict[str, Any]] = None,
    output_dir: Optional[Path] = None,
) -> bool:
    """
    Determine whether a given format needs to be rendered based on cached QMD hash.
    For non-deterministic formats, we only compare the QMD hash; the output hash
    is ignored to avoid unnecessary re-renders when the generated file would be
    slightly different (e.g. due to timestamps). Deterministic formats are always
    rendered.
    Returns True if render is needed, False if up-to-date.
    """
    if fmt not in NON_DETERMINISTIC_FORMATS:
        logger.info(f"{fmt} is considered deterministic, always render.")
        return True

    qmd_hash = compute_quarto_file_hash_with_deps(file_path, docs_root)
    logger.info(
        f"Checking cache for {target_name} ({fmt}): QMD hash {qmd_hash[:16]}..."
    )

    cached = find_cached_artifact(target_name, qmd_hash, fmt, docs_root)
    if cached is not None:
        output_path = get_format_output_path(file_path, fmt)
        if output_path is None:
            logger.warning(
                f"Cannot determine output path for {target_name} ({fmt}), proceeding with render."
            )
            return True
        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(cached, output_path)
            logger.info(
                f"Cache hit for {target_name} ({fmt}), copied cached artifact to {output_path}"
            )
        except Exception as e:
            logger.warning(
                f"Failed to copy cached artifact for {target_name} ({fmt}): {e}, proceeding with render."
            )
            return True
        cfg = config or {}
        for linked_ext in get_linked_artifact_extensions(fmt, cfg):
            cached_linked = find_cached_artifact(
                target_name, qmd_hash, fmt, docs_root, linked_ext=linked_ext
            )
            if cached_linked is not None:
                linked_stem = file_path.stem
                linked_output_path = output_path.parent / f"{linked_stem}.{linked_ext}"
                try:
                    shutil.copy2(cached_linked, linked_output_path)
                    logger.info(
                        f"Restored cached linked artifact ({linked_ext}) to {linked_output_path}"
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to copy cached linked artifact for {target_name} ({fmt}): {e}"
                    )
        return False

    logger.info(f"Cache miss for {target_name} ({fmt}) - QMD hash {qmd_hash[:16]}...")
    return True


def update_format_cache(
    file_path: Path,
    fmt: str,
    output_path: Path,
    docs_root: Path,
    target_name: Optional[str] = None,
    linked_artifacts: Optional[Dict[str, Path]] = None,
) -> None:
    """Update cache after successful render of a specific format.

    Args:
        file_path: Path to the source QMD file
        fmt: Output format (pdf, html, etc.)
        output_path: Path to the rendered output file
        docs_root: Root directory of documentation
        target_name: Name of the build target
        linked_artifacts: Dict mapping linked file extension -> path to the linked artifact file
    """
    qmd_hash = compute_quarto_file_hash_with_deps(file_path, docs_root)
    output_hash = compute_file_hash(output_path)
    logger.info(
        f"Updating {fmt} cache for {file_path.name}: output hash {output_hash[:16]}..."
    )

    if target_name is not None:
        target_cache_dir = get_cache_base(docs_root) / target_name
        if target_cache_dir.exists():
            try:
                for existing_hash_dir in target_cache_dir.iterdir():
                    if (
                        existing_hash_dir.is_dir()
                        and existing_hash_dir.name != qmd_hash
                    ):
                        shutil.rmtree(existing_hash_dir)
                        logger.info(
                            f"Deleted old cache directory for target '{target_name}' "
                            f"(hash: {existing_hash_dir.name[:16]}...) to prevent accumulation"
                        )
            except Exception as e:
                logger.warning(
                    f"Failed to delete old cache for target '{target_name}': {e}"
                )

        cache_dir = get_cache_base(docs_root) / target_name / qmd_hash
        cache_dir.mkdir(parents=True, exist_ok=True)
        ext = format_to_extension(fmt)
        artifact_name = f"{target_name}.{ext}"
        artifact_path = cache_dir / artifact_name
        try:
            shutil.copy2(output_path, artifact_path)
            logger.info(f"Cached artifact for {target_name} ({fmt}) at {artifact_path}")
        except Exception as e:
            logger.warning(f"Failed to cache artifact for {target_name} ({fmt}): {e}")

        if linked_artifacts:
            for linked_ext, linked_path in linked_artifacts.items():
                if linked_path is not None and linked_path.exists():
                    linked_cache_name = f"{target_name}.{linked_ext}"
                    linked_cache_path = cache_dir / linked_cache_name
                    try:
                        shutil.copy2(linked_path, linked_cache_path)
                        logger.info(
                            f"Cached linked artifact ({linked_ext}) for {target_name} ({fmt}) at {linked_cache_path}"
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to cache linked artifact ({linked_ext}) for {target_name} ({fmt}): {e}"
                        )

    cache_file = get_cache_file(file_path, fmt)
    write_hash_pair(cache_file, qmd_hash, output_hash)


def refresh_cache_for_target(
    target: str,
    output_dir: Optional[Path] = None,
    docs_root: Optional[Path] = None,
    target_config: Optional[Dict] = None,
) -> bool:
    """
    Refresh the cache entries for a given target.
    Updates the cache only when the QMD hash has not changed (i.e., the source is
    identical to when the cache was created). If the QMD hash changed, the cache
    is removed to force a rebuild on the next build. This avoids recording stale
    outputs and eliminates reliance on file timestamps.
    Returns True on success, False on failure.
    """
    if docs_root is None:
        docs_root = Path.cwd()
    if target_config is None:
        target_config = TARGET_CONFIG

    if target not in target_config:
        logger.error(f"Unknown target '{target}'")
        return False
    config = target_config[target]
    qmd_path = docs_root / config["qmd"]
    if not qmd_path.exists():
        logger.error(f"Qmd file not found: {qmd_path}")
        return False

    formats = get_formats_from_quarto_file(qmd_path)
    if not formats:
        logger.info(
            f"Target {target} has no defined output formats, skipping cache refresh."
        )
        return True

    current_qmd_hash = compute_quarto_file_hash_with_deps(qmd_path, docs_root)

    for fmt in formats:
        cache_file = get_cache_file(qmd_path, fmt)
        existing_cache = read_hash_pair(cache_file)

        output_path = find_existing_output(qmd_path, fmt, config, output_dir, docs_root)

        if output_path and output_path.exists():
            if existing_cache is not None and existing_cache[0] == current_qmd_hash:
                update_format_cache(qmd_path, fmt, output_path, docs_root, target_name=target)
                logger.info(f"Updated {fmt} cache for {target}")
            else:
                if cache_file.exists():
                    cache_file.unlink()
                    logger.info(
                        f"Removed cache file for {target} ({fmt}) - QMD changed or cache missing"
                    )
                else:
                    logger.info(
                        f"No cache file for {target} ({fmt}) - will rebuild on next run"
                    )
                if existing_cache is not None:
                    old_hash = existing_cache[0]
                    old_cache_dir = get_cache_base(docs_root) / target / old_hash
                    if old_cache_dir.exists():
                        shutil.rmtree(old_cache_dir)
                        logger.info(
                            f"Removed new cache directory for {target} ({fmt}) - QMD changed"
                        )
        else:
            if cache_file.exists():
                cache_file.unlink()
                logger.info(f"Removed cache file for {target} ({fmt} output missing)")
            else:
                logger.info(f"No cache file for {target} ({fmt} output missing)")
    return True


# ---------------------------------------------------------------------------
# Pre-build / post-render command runners
# ---------------------------------------------------------------------------


# Mapping of known command patterns to (module_path, function_name) tuples.
# When a command list matches one of these keys (as a tuple), the
# corresponding function is called directly instead of via subprocess.
_INLINE_COMMAND_MAP: Dict[Tuple[str, ...], Tuple[str, str]] = {
    ("python3", "_utils/generate_latest_docs.py"): (
        "sdb.utils.latest",
        "generate_latest_docs",
    ),
    ("python3", "resolve.py"): (
        "sdb.resolve",
        "resolve_all",
    ),
    ("python3", "_utils/generate_llms_txt.py"): (
        "sdb.utils.llms",
        "generate_llms_txt",
    ),
}


def _try_dispatch_inline(
    cmd: List[str],
    docs_root: Path,
    log: logging.Logger,
    phase: str,
) -> bool:
    """Try to dispatch *cmd* to an in-process function instead of subprocess.

    Returns ``True`` if the command was handled (success or failure logged),
    ``False`` if the caller should fall through to subprocess.
    """
    key = tuple(cmd)
    if key not in _INLINE_COMMAND_MAP:
        logger.debug(f"{phase}: no inline handler for {' '.join(cmd)}, fallback to subprocess")
        return False

    module_name, func_name = _INLINE_COMMAND_MAP[key]
    log.info(f"{phase}: calling {module_name}.{func_name}(docs_root={docs_root})")
    try:
        import importlib

        module = importlib.import_module(module_name)
        func = getattr(module, func_name)
        func(docs_root)
        log.info(f"{phase}: inline function '{func_name}' completed.")
    except Exception as e:
        log.warning(
            f"{phase}: inline function '{func_name}' raised: {e}, "
            f"continuing..."
        )
    return True


def _run_config_commands(
    section: Any,
    docs_root: Path,
    phase: str,
    target_name: Optional[str] = None,
) -> None:
    """Execute commands from a named config section (pre_build / post_render).

    Handles both global commands (``_global``) and target-specific entries.
    Known Python commands are dispatched inline via ``_try_dispatch_inline``;
    others are run as subprocesses.
    """
    if not section:
        return

    if isinstance(section, list):
        global_commands = section
        target_commands: Dict[str, Any] = {}
    elif isinstance(section, dict):
        global_commands = section.get("_global", [])
        target_commands = {
            k: v for k, v in section.items() if k != "_global"
        }
    else:
        logger.warning(
            f"Invalid {phase.lower()} format: expected list or dict, "
            f"got {type(section).__name__}"
        )
        return

    commands_to_run: List[List[str]] = []
    if target_name is None:
        commands_to_run.extend(global_commands)
    elif target_name in target_commands:
        target_cmds = target_commands[target_name]
        if isinstance(target_cmds, list):
            if target_cmds and isinstance(target_cmds[0], list):
                commands_to_run.extend(target_cmds)
            else:
                commands_to_run.append(target_cmds)
        elif isinstance(target_cmds, str):
            commands_to_run.append(target_cmds.split())
        else:
            logger.warning(
                f"Invalid {phase.lower()} entry for target "
                f"'{target_name}': {target_cmds}, skipping."
            )

    if not commands_to_run:
        return

    prefix = phase.lower()
    if target_name:
        logger.info(
            f"Running {len(commands_to_run)} {prefix} command(s) "
            f"for target '{target_name}'..."
        )
    else:
        logger.info(
            f"Running {len(commands_to_run)} global {prefix} command(s)..."
        )

    for cmd in commands_to_run:
        if not cmd or not isinstance(cmd, list):
            logger.warning(f"Invalid {prefix} entry: {cmd}, skipping.")
            continue
        executable = cmd[0]

        if _try_dispatch_inline(cmd, docs_root, logger, phase):
            continue

        if not shutil.which(executable):
            logger.info(f"{phase}: '{executable}' not found in PATH, skipping.")
            continue
        logger.info(f"{phase}: running {' '.join(cmd)}")
        try:
            result = subprocess.run(
                cmd, cwd=docs_root, capture_output=True, text=True
            )
            if result.stdout:
                logger.debug(result.stdout.strip())
            if result.stderr:
                logger.warning(result.stderr.strip())
            if result.returncode != 0:
                logger.warning(
                    f"{phase} command '{executable}' failed with exit code "
                    f"{result.returncode}, continuing..."
                )
            else:
                logger.info(
                    f"{phase} command '{' '.join(cmd)}' succeeded."
                )
        except Exception as e:
            logger.warning(
                f"{phase} command '{executable}' raised an exception: "
                f"{e}, continuing..."
            )


def run_pre_build_commands(
    external_config: Dict[str, Any],
    docs_root: Path,
    target_name: Optional[str] = None,
) -> None:
    """Execute pre-build commands from configuration."""
    _run_config_commands(
        external_config.get("pre_build", []),
        docs_root,
        "Pre-build",
        target_name=target_name,
    )


def run_post_render_commands(
    external_config: Dict[str, Any],
    docs_root: Path,
    target_name: Optional[str] = None,
) -> None:
    """Execute post-render commands from configuration."""
    _run_config_commands(
        external_config.get("post_render", []),
        docs_root,
        "Post-render",
        target_name=target_name,
    )


# ---------------------------------------------------------------------------
# Core build function
# ---------------------------------------------------------------------------


def build_generic(
    target: str,
    config: Dict[str, Any],
    output_dir: Optional[Path] = None,
    single_command: bool = True,
    website: bool = False,
    docs_root: Optional[Path] = None,
    build_targets_set: Optional[set] = None,
) -> bool:
    """
    Generic build function that renders a .qmd or .md file and performs
    optional post-processing.

    Formats are rendered in a single command by default.  Set
    ``single_command=False`` to render each format in separate commands
    (parallel per format).

    If ``website`` is True, adds ``--profile website`` to Quarto render
    commands.  In website mode, formats are NOT rendered individually;
    instead ``quarto render`` is called without ``--to`` to let Quarto
    handle all formats defined in the document YAML.

    For .md files without explicit format configuration, ``quarto render``
    is called without ``--to`` to let Quarto handle the file natively.

    If ``docs_root`` is provided, use it as the docs directory (for isolated
    mode).
    """
    logger.info(f"Building {target}...")
    if docs_root is None:
        docs_root = Path.cwd()

    source_path = docs_root / config["qmd"]
    if not source_path.exists():
        logger.error(f"Source file not found: {source_path}")
        return False

    is_md_file = source_path.suffix.lower() == ".md"

    # For .md files without explicit 'to' config, render directly without
    # format inspection
    if is_md_file and config.get("to") is None:
        if website:
            fmt = "html"
            qmd_hash = compute_quarto_file_hash_with_deps(source_path, docs_root)
            if not should_render_format(
                source_path, fmt, target, docs_root, config, output_dir
            ):
                if not should_rerender_for_sidebar(
                    build_targets_set or set(), docs_root
                ):
                    logger.info(
                        f"Cache hit for {target} ({fmt}), document set unchanged, "
                        "using cached version."
                    )
                    site_dir = docs_root / "_site"
                    restore_site_directory(target, qmd_hash, site_dir, docs_root)
                    logger.info(
                        f"{target} build completed successfully "
                        "(native Markdown, website)."
                    )
                    return True
                logger.info(
                    f"Cache hit for {target} ({fmt}), document set changed, "
                    "re-rendering HTML to update sidebar."
                )
            logger.info(
                f"Rendering {source_path.name} as native Markdown "
                "(website mode, HTML only)"
            )
            quarto_cmd = [
                "quarto",
                "render",
                str(source_path),
                "--to",
                "html",
                "--profile",
                "website",
            ]
            if not run_command(quarto_cmd, cwd=docs_root):
                logger.error(f"Quarto render failed for {source_path.name}.")
                return False
            output_path = get_format_output_path(source_path, fmt)
            if output_path and output_path.exists():
                update_format_cache(
                    source_path, fmt, output_path, docs_root, target_name=target
                )
            else:
                if docs_root:
                    try:
                        rel = source_path.relative_to(docs_root)
                        site_path = docs_root / "_site" / rel.with_suffix(".html")
                        if site_path.exists():
                            update_format_cache(
                                source_path, fmt, site_path, docs_root, target_name=target
                            )
                    except ValueError:
                        pass
            site_dir = docs_root / "_site"
            cache_site_directory(target, qmd_hash, site_dir, docs_root)
            logger.info(
                f"{target} build completed successfully (native Markdown, website)."
            )
            return True

        formats = get_formats_from_quarto_file(source_path)
        if not formats:
            formats = ["html"]

        formats_to_render = []
        for fmt in formats:
            if should_render_format(
                source_path, fmt, target, docs_root, config, output_dir
            ):
                formats_to_render.append(fmt)

        if not formats_to_render:
            logger.info(
                f"All formats for {target} are up-to-date, skipping render."
            )
            return True

        logger.info(
            f"Rendering {source_path.name} as native Markdown "
            f"(formats: {', '.join(formats)})"
        )
        quarto_cmd = ["quarto", "render", str(source_path)]
        if not run_command(quarto_cmd, cwd=docs_root):
            logger.error(f"Quarto render failed for {source_path.name}.")
            return False

        for fmt in formats:
            output_path = get_format_output_path(source_path, fmt)
            if output_path and output_path.exists():
                update_format_cache(
                    source_path, fmt, output_path, docs_root, target_name=target
                )

        logger.info(f"{target} build completed successfully (native Markdown).")
        return True

    qmd_path = source_path

    if qmd_path.stem.lower() == "index":
        parent_name = qmd_path.parent.name
        stem = parent_name if parent_name and parent_name != "." else qmd_path.stem
    else:
        stem = qmd_path.stem

    target_format = config.get("to")
    if target_format is None:
        formats = get_formats_from_quarto_file(qmd_path)
        if not formats:
            logger.error(
                f"Could not determine output formats for {qmd_path}. "
                "Please specify a format in the target config or ensure "
                "'quarto inspect' works."
            )
            return False
    else:
        formats = [target_format]

    format_output_paths = {}
    for fmt in formats:
        output_path = get_format_output_path(qmd_path, fmt)
        if output_path is None:
            logger.error(
                f"Cannot determine output path for format '{fmt}' of {qmd_path}. "
                "Please ensure 'quarto inspect' provides an 'output-file' or "
                "that the format is properly defined."
            )
            return False
        format_output_paths[fmt] = output_path

    formats_to_render = []
    if not website:
        for fmt in formats:
            if should_render_format(
                qmd_path, fmt, target, docs_root, config, output_dir
            ):
                formats_to_render.append(fmt)

    qmd_hash = ""

    if website:
        qmd_hash = compute_quarto_file_hash_with_deps(qmd_path, docs_root)
        all_cached = True
        for fmt in formats:
            if find_cached_artifact(target, qmd_hash, fmt, docs_root) is None:
                all_cached = False
                break
        if all_cached:
            if "html" in formats:
                if not should_rerender_for_sidebar(
                    build_targets_set or set(), docs_root
                ):
                    logger.info(
                        f"All formats for {target} are cached, document set unchanged, "
                        "using cached version."
                    )
                    for fmt in formats:
                        cached = find_cached_artifact(
                            target, qmd_hash, fmt, docs_root
                        )
                        output_path = format_output_paths.get(fmt)
                        if cached:
                            if output_path:
                                output_path.parent.mkdir(parents=True, exist_ok=True)
                                shutil.copy2(cached, output_path)
                        for linked_ext in get_linked_artifact_extensions(fmt, config):
                            cached_linked = find_cached_artifact(
                                target, qmd_hash, fmt, docs_root, linked_ext=linked_ext
                            )
                            if cached_linked is not None:
                                linked_stem = qmd_path.stem
                                linked_output_path = (
                                    output_path.parent / f"{linked_stem}.{linked_ext}"
                                    if output_path
                                    else None
                                )
                                if linked_output_path:
                                    try:
                                        shutil.copy2(cached_linked, linked_output_path)
                                        logger.info(
                                            f"Restored cached linked artifact ({linked_ext}) "
                                            f"to {linked_output_path}"
                                        )
                                    except Exception as e:
                                        logger.warning(
                                            f"Failed to copy cached linked artifact "
                                            f"for {target} ({fmt}): {e}"
                                        )
                    site_dir = docs_root / "_site"
                    restore_site_directory(target, qmd_hash, site_dir, docs_root)
                    return True
                logger.info(
                    f"All formats for {target} are cached, document set changed, "
                    "re-rendering HTML to update sidebar."
                )
                for fmt in formats:
                    if fmt == "html":
                        continue
                    cached = find_cached_artifact(
                        target, qmd_hash, fmt, docs_root
                    )
                    if cached:
                        output_path = format_output_paths.get(fmt)
                        if output_path:
                            output_path.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(cached, output_path)
                        if docs_root and output_path:
                            try:
                                rel = output_path.relative_to(docs_root)
                                site_path = docs_root / "_site" / rel
                                if site_path != output_path and not site_path.exists():
                                    site_path.parent.mkdir(parents=True, exist_ok=True)
                                    shutil.copy2(cached, site_path)
                            except ValueError:
                                pass
                logger.info(
                    f"Re-rendering {source_path.name} in website mode "
                    "(HTML only, to update sidebar)"
                )
                quarto_cmd = [
                    "quarto",
                    "render",
                    str(source_path),
                    "--to",
                    "html",
                    "--profile",
                    "website",
                ]
                if not run_command(quarto_cmd, cwd=docs_root):
                    logger.error(
                        f"Quarto render failed for {source_path.name} "
                        "(website mode, HTML refresh)."
                    )
                    return False
                output_path = format_output_paths.get("html")
                if output_path and output_path.exists():
                    update_format_cache(
                        qmd_path, "html", output_path, docs_root, target_name=target
                    )
                else:
                    if docs_root:
                        try:
                            if output_path:
                                rel = output_path.relative_to(docs_root)
                                site_path = docs_root / "_site" / rel
                                if site_path.exists():
                                    update_format_cache(
                                        qmd_path,
                                        "html",
                                        site_path,
                                        docs_root,
                                        target_name=target,
                                    )
                        except (ValueError, AttributeError):
                            pass
                site_dir = docs_root / "_site"
                cache_site_directory(target, qmd_hash, site_dir, docs_root)
            else:
                logger.info(
                    f"All formats for {target} are cached (no HTML), "
                    "restoring from cache."
                )
                for fmt in formats:
                    cached = find_cached_artifact(
                        target, qmd_hash, fmt, docs_root
                    )
                    if cached:
                        output_path = format_output_paths.get(fmt)
                        if output_path:
                            output_path.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(cached, output_path)
                        for linked_ext in get_linked_artifact_extensions(fmt, config):
                            cached_linked = find_cached_artifact(
                                target,
                                qmd_hash,
                                fmt,
                                docs_root,
                                linked_ext=linked_ext,
                            )
                            if cached_linked is not None:
                                linked_stem = qmd_path.stem
                                linked_output_path = (
                                    output_path.parent / f"{linked_stem}.{linked_ext}"
                                    if output_path
                                    else None
                                )
                                if linked_output_path:
                                    try:
                                        shutil.copy2(cached_linked, linked_output_path)
                                        logger.info(
                                            f"Restored cached linked artifact ({linked_ext}) "
                                            f"to {linked_output_path}"
                                        )
                                    except Exception as e:
                                        logger.warning(
                                            f"Failed to copy cached linked artifact "
                                            f"for {target} ({fmt}): {e}"
                                        )
                site_dir = docs_root / "_site"
                restore_site_directory(target, qmd_hash, site_dir, docs_root)
        else:
            logger.info(
                f"Rendering {source_path.name} in website mode "
                "(no --to, all formats from YAML)"
            )
            quarto_cmd = [
                "quarto",
                "render",
                str(source_path),
                "--profile",
                "website",
            ]
            if not run_command(quarto_cmd, cwd=docs_root):
                logger.error(
                    f"Quarto render failed for {source_path.name} (website mode)."
                )
                return False
            for fmt in formats:
                output_path = format_output_paths.get(fmt)
                if output_path and output_path.exists():
                    update_format_cache(
                        qmd_path, fmt, output_path, docs_root, target_name=target
                    )
                else:
                    if docs_root:
                        try:
                            if output_path is not None:
                                try:
                                    rel = output_path.relative_to(docs_root)
                                except ValueError:
                                    continue
                            else:
                                continue
                            site_path = docs_root / "_site" / rel
                            if site_path.exists():
                                update_format_cache(
                                    qmd_path,
                                    fmt,
                                    site_path,
                                    docs_root,
                                    target_name=target,
                                )
                        except (ValueError, AttributeError):
                            pass
    else:
        if formats_to_render:
            logger.info(
                f"Rendering {len(formats_to_render)} format(s) for {target}"
            )
            if not _render_formats(
                qmd_path,
                formats_to_render,
                format_output_paths,
                docs_root,
                single_command,
                website,
                target_name=target,
            ):
                return False
        else:
            logger.info(
                f"All formats for {target} are up-to-date, skipping render."
            )

    # Step 2: Generate linked artifacts (e.g. C2PA signing)
    logger.info(f"format_output_paths keys: {list(format_output_paths.keys())}")
    enabled_handlers = get_enabled_handlers(config)
    if enabled_handlers:
        primary_paths: Dict[str, Path] = {}
        for fmt in formats:
            path = format_output_paths.get(fmt)
            if path:
                if website:
                    try:
                        rel = path.relative_to(docs_root)
                        primary_paths[fmt] = docs_root / "_site" / rel
                    except ValueError:
                        primary_paths[fmt] = path
                else:
                    primary_paths[fmt] = path
            if config.get("copy_pdf") and output_dir and fmt in ("pdf", "beamer"):
                dest_dir = (
                    Path(output_dir).absolute() if output_dir else docs_root
                )
                primary_paths[fmt] = (
                    dest_dir / f"{stem}.{format_to_extension(fmt)}"
                )

        linked_artifacts: Dict[str, Dict[str, Path]] = {}
        for fmt, primary_path in primary_paths.items():
            if not primary_path.exists():
                continue
            linked_artifacts[fmt] = {}
            for handler in enabled_handlers:
                ext = handler.get_extension(fmt)
                if ext is None:
                    continue
                linked_stem = qmd_path.stem
                existing_linked = primary_path.parent / f"{linked_stem}.{ext}"
                if existing_linked.exists():
                    linked_artifacts[fmt][ext] = existing_linked
                    logger.info(
                        f"Linked artifact ({ext}) already exists at "
                        f"{existing_linked}, skipping generation."
                    )
                    continue
                generated_path = handler.generate(
                    qmd_path,
                    fmt,
                    primary_path,
                    docs_root,
                    config,
                    target_name=target,
                )
                if generated_path:
                    linked_artifacts[fmt][ext] = generated_path
                    logger.info(
                        f"Generated linked artifact ({ext}) for {fmt} "
                        f"at {generated_path}"
                    )
                else:
                    logger.warning(
                        f"Failed to generate linked artifact ({ext}) for {fmt}"
                    )

        for fmt, artifacts in linked_artifacts.items():
            if artifacts:
                primary_path = primary_paths.get(fmt)
                if primary_path and primary_path.exists():
                    update_format_cache(
                        qmd_path,
                        fmt,
                        primary_path,
                        docs_root,
                        target_name=target,
                        linked_artifacts=artifacts,
                    )

    if website:
        site_dir = docs_root / "_site"
        cache_site_directory(target, qmd_hash, site_dir, docs_root)

    # Step 3: Move primary output and linked artifacts to output_dir
    if config.get("copy_pdf"):
        candidates = []
        primary = format_output_paths.get("pdf") or format_output_paths.get("beamer")
        if primary:
            candidates.append(primary)
            if website:
                try:
                    rel = primary.relative_to(docs_root)
                    candidates.append(docs_root / "_site" / rel)
                except ValueError:
                    pass
        primary_path = None
        for cand in candidates:
            if cand and cand.exists():
                primary_path = cand
                break
        if primary_path and primary_path.exists():
            dest_dir = (
                Path(output_dir).absolute() if output_dir else docs_root
            )
            dest_dir.mkdir(parents=True, exist_ok=True)
            primary_ext = format_to_extension(
                "pdf" if "pdf" in format_output_paths else "beamer"
            )
            dest_primary = dest_dir / f"{stem}.{primary_ext}"
            linked_stem = qmd_path.stem
            source_linked = {}
            dest_linked = {}
            for linked_ext in get_linked_artifact_extensions(
                "pdf" if "pdf" in format_output_paths else "beamer",
                config,
            ):
                source_linked[linked_ext] = (
                    primary_path.parent / f"{linked_stem}.{linked_ext}"
                )
                dest_linked[linked_ext] = (
                    dest_dir / f"{linked_stem}.{linked_ext}"
                )
            if dest_primary.resolve() != primary_path.resolve():
                try:
                    shutil.move(str(primary_path), str(dest_primary))
                    logger.info(
                        f"Moved primary output ({primary_ext}) to {dest_primary}"
                    )
                    for linked_ext, src_path in source_linked.items():
                        if src_path.exists():
                            shutil.move(
                                str(src_path), str(dest_linked[linked_ext])
                            )
                            logger.info(
                                f"Moved linked artifact ({linked_ext}) "
                                f"to {dest_linked[linked_ext]}"
                            )
                except Exception as e:
                    logger.error(f"Failed to move primary output: {e}")
                    return False
            else:
                logger.info(
                    "Primary output already at destination, skipping move."
                )

    # Step 4: Copy HTML/Markdown to output_dir
    if output_dir:
        if config.get("copy_html"):
            html_path = format_output_paths.get("html")
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
                logger.warning(
                    f"copy_html enabled but HTML output not found for {target}"
                )
        if config.get("copy_md"):
            md_path = format_output_paths.get("gfm") or format_output_paths.get(
                "markdown"
            )
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
                logger.warning(
                    f"copy_md enabled but Markdown output not found "
                    f"for {target}"
                )

    logger.info(f"{target} build completed successfully.")
    return True


# ---------------------------------------------------------------------------
# Initialization and builder factory
# ---------------------------------------------------------------------------


def initialize_config(docs_root: Path, config_path: Optional[Path] = None) -> None:
    """Initialize global configuration for the given docs root.

    Loads external config, discovers targets, populates module-level
    ``TARGET_CONFIG`` and ``BUILD_FUNCTIONS``, and ensures the Jupyter
    cache directory exists.
    """
    global EXTERNAL_CONFIG, TARGET_CONFIG, BUILD_FUNCTIONS, OUTPUT_DIR_TARGETS
    global JUPYTER_CACHE_PATH, PROJECT_ROOT

    PROJECT_ROOT = docs_root.parent

    jupyter_cache_path = PROJECT_ROOT / JUPYTER_CACHE_DIR
    jupyter_cache_path.mkdir(parents=True, exist_ok=True)
    JUPYTER_CACHE_PATH = jupyter_cache_path
    os.environ["JUPYTERCACHE"] = str(jupyter_cache_path)

    EXTERNAL_CONFIG = load_external_config(config_path)
    TARGET_CONFIG = get_target_config(docs_root, EXTERNAL_CONFIG)

    BUILD_FUNCTIONS = {}
    for target, config in TARGET_CONFIG.items():

        def make_builder(tgt, cfg):
            def builder(
                output_dir: Optional[Path] = None,
                single_command: bool = True,
                website: bool = False,
                docs_root: Optional[Path] = None,
                build_targets_set: Optional[set] = None,
            ) -> bool:
                return build_generic(
                    tgt,
                    cfg,
                    output_dir,
                    single_command,
                    website,
                    docs_root,
                    build_targets_set,
                )

            return builder

        BUILD_FUNCTIONS[target] = make_builder(target, config)

    OUTPUT_DIR_TARGETS = {
        t for t, cfg in TARGET_CONFIG.items() if cfg.get("output_dir")
    }


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
        logger.error(
            f"Unknown target(s): {invalid}. "
            f"Available: {list(BUILD_FUNCTIONS.keys())}"
        )
        sys.exit(1)
    return targets


def build_single_target(
    target: str,
    output_dir: Optional[Path],
    single_command: bool,
    website: bool = False,
    docs_root: Optional[Path] = None,
    build_targets_set: Optional[set] = None,
) -> Tuple[str, bool]:
    """Wrapper to run a single build function and return (target_name, success)."""
    logger.info(f"Starting build: {target}")
    func = BUILD_FUNCTIONS[target]
    try:
        if target in OUTPUT_DIR_TARGETS:
            success = func(
                output_dir=output_dir,
                single_command=single_command,
                website=website,
                docs_root=docs_root,
                build_targets_set=build_targets_set,
            )
        else:
            success = func(
                single_command=single_command,
                website=website,
                docs_root=docs_root,
                build_targets_set=build_targets_set,
            )
        logger.info(f"Finished build: {target} -> {'✓' if success else '✗'}")
        return target, success
    except Exception as e:
        logger.error(f"Exception while building {target}: {e}")
        return target, False


# ---------------------------------------------------------------------------
# Isolated target rendering (website parallel mode)
# ---------------------------------------------------------------------------


def _render_target_isolated(
    target: str,
    output_dir: Optional[Path],
    single_command: bool,
    website: bool,
    temp_docs: Path,
    build_targets_set: Optional[set] = None,
) -> bool:
    """
    Render a single target in isolation using a complete copy of the docs folder.
    This prevents resource conflicts when running multiple quarto renders in parallel.
    """
    logger.info(
        f"Rendering {target} in isolated docs directory {temp_docs}"
    )

    try:
        func = BUILD_FUNCTIONS.get(target)
        if func is None:
            logger.error(f"Unknown target: {target}")
            return False

        success = func(
            output_dir=temp_docs / "_site",
            single_command=single_command,
            website=website,
            docs_root=temp_docs,
            build_targets_set=build_targets_set,
        )
        return success
    except Exception as e:
        logger.error(f"Exception while rendering {target}: {e}")
        return False


# ---------------------------------------------------------------------------
# LLMS file sync
# ---------------------------------------------------------------------------


def _sync_llms_files(source_dir: Path, docs_root: Path) -> None:
    """
    Sync LLMS files (llms.txt and *.llms.md) from source_dir to a sibling
    _llms directory.

    Only operates if the website config has llms-txt enabled.
    """
    config = ConfigManager.get_website_config(docs_root)
    llms_txt_enabled = config.get("website", {}).get("llms-txt", False)
    if not llms_txt_enabled:
        return
    if not source_dir.exists():
        logger.warning(
            f"Source directory {source_dir} does not exist, skipping rsync."
        )
        return
    dest_dir = source_dir.parent / "_llms"
    logger.info(
        f"Running rsync to copy LLMS files from {source_dir} to {dest_dir}"
    )
    rsync_cmd = [
        "rsync",
        "-av",
        "--delete",
        "--delete-excluded",
        "--include=*/",
        "--include=*.llms.md",
        "--include=llms.txt",
        "--exclude=*",
        f"{source_dir}/",
        f"{dest_dir}/",
    ]
    try:
        subprocess.run(rsync_cmd, check=True)
        subprocess.run(
            ["find", str(dest_dir), "-type", "d", "-empty", "-delete"],
            check=False,
        )
        logger.info("rsync completed successfully.")
    except subprocess.CalledProcessError as e:
        logger.error(f"rsync failed with exit code {e.returncode}")
    except Exception as e:
        logger.error(f"Failed to run rsync: {e}")


# ---------------------------------------------------------------------------
# Orphaned cache cleanup
# ---------------------------------------------------------------------------


def _cleanup_orphaned_caches(
    successful_targets: set,
    docs_root: Path,
    cache_base: Optional[Path] = None,
) -> int:
    """
    Remove cache entries for targets that are no longer in the successful
    build set.  Prevents accumulation of stale cache data when source files
    are deleted or target names change.

    Args:
        successful_targets: Set of target names that were successfully built
        docs_root: Root directory of documentation
        cache_base: Base cache directory (defaults to ``_cached`` in parent
            of docs root)

    Returns:
        Number of orphaned cache directories removed
    """
    if cache_base is None:
        cache_base = get_cache_base(docs_root)

    if not cache_base.exists():
        return 0

    cached_targets = {d.name for d in cache_base.iterdir() if d.is_dir()}
    orphaned = cached_targets - successful_targets

    if not orphaned:
        logger.debug("No orphaned cache entries found.")
        return 0

    removed_count = 0
    for target_name in orphaned:
        cache_dir = cache_base / target_name
        try:
            shutil.rmtree(cache_dir)
            logger.info(
                f"Removed orphaned cache for target '{target_name}' "
                f"at {cache_dir}"
            )
            removed_count += 1
        except Exception as e:
            logger.warning(
                f"Failed to remove orphaned cache for '{target_name}': {e}"
            )

    logger.info(
        f"Cleaned up {removed_count} orphaned cache directorie(s)."
    )
    return removed_count


# ---------------------------------------------------------------------------
# Multi-target orchestrator
# ---------------------------------------------------------------------------


def build_targets(
    targets: List[str],
    output_dir: Optional[Path],
    sequence_mode: bool,
    max_jobs: int,
    single_command: bool,
    website: bool = False,
    docs_root: Optional[Path] = None,
) -> bool:
    """
    Build multiple targets.

    Behavior:
      - If sequence_mode=True: run sequentially regardless of target count
      - If sequence_mode=False and len(targets) > 1: run in parallel (default)
      - If sequence_mode=False and len(targets) == 1: run normally
        (no threading overhead)
      - If website=True and parallel: use isolated temp directories for each
        target, then merge

    In website mode with parallel execution, each target renders to its own
    temp directory to avoid site_libs conflicts, then results are merged into
    the final _site directory.

    Important: The _site output directory is cleaned before building to
    ensure no stale files remain.
    """
    if docs_root is None:
        docs_root = Path.cwd()

    if not targets:
        logger.info("No targets specified. Nothing to build.")
        return True

    build_temp_path = docs_root.parent / BUILD_TEMP_DIR

    run_pre_build_commands(EXTERNAL_CONFIG, docs_root)

    for t in targets:
        run_pre_build_commands(EXTERNAL_CONFIG, docs_root, target_name=t)

    capture_initial_cached_targets(docs_root)

    results: Dict[str, bool] = {}

    final_site = output_dir if output_dir else (docs_root / "_site")
    if final_site.exists():
        logger.info(f"Cleaning existing _site directory: {final_site}")
        try:
            shutil.rmtree(final_site)
            logger.info("Removed existing _site directory")
        except Exception as e:
            logger.error(
                f"Failed to remove existing _site directory: {e}"
            )
            return False

    if website and (not sequence_mode) and (len(targets) > 1):
        logger.info(
            "Website mode: using isolated docs copies for parallel rendering..."
        )

        base_temp = build_temp_path

        if base_temp.exists():
            logger.info(f"Cleaning fixed temp dir: {base_temp}")
            shutil.rmtree(base_temp, ignore_errors=True)

        base_temp.mkdir(parents=True, exist_ok=True)
        logger.info(f"Using fixed temp directory: {base_temp}")

        def copy_for_target(t: str) -> Tuple[str, Path]:
            temp_docs = base_temp / t
            if temp_docs.exists():
                shutil.rmtree(temp_docs, ignore_errors=True)

            logger.info(f"Copying docs to {temp_docs} for {t}...")

            def _strict_ignore(src, names):
                ignored = set(ignore_quarto_artifacts()(src, names))
                if base_temp.name in names:
                    ignored.add(base_temp.name)
                for name in list(names):
                    p = Path(src) / name
                    if p.is_symlink() and p.resolve() == base_temp.resolve():
                        ignored.add(name)
                return ignored

            shutil.copytree(docs_root, temp_docs, ignore=_strict_ignore)
            return t, temp_docs

        target_temp_dirs: Dict[str, Path] = {}

        try:
            with ThreadPoolExecutor(max_workers=max_jobs) as executor:
                future_to_target = {
                    executor.submit(copy_for_target, t): t for t in targets
                }
                for future in as_completed(future_to_target):
                    target = future_to_target[future]
                    try:
                        t, temp_docs = future.result()
                        target_temp_dirs[t] = temp_docs
                    except Exception as e:
                        logger.error(
                            f"Failed to copy docs for {target}: {e}"
                        )
                        for td in target_temp_dirs.values():
                            if td.exists():
                                shutil.rmtree(td, ignore_errors=True)
                        shutil.rmtree(base_temp, ignore_errors=True)
                        return False

            build_targets_set = set(targets)
            with ThreadPoolExecutor(max_workers=max_jobs) as executor:
                futures = {
                    executor.submit(
                        _render_target_isolated,
                        t,
                        output_dir,
                        single_command,
                        website,
                        target_temp_dirs[t],
                        build_targets_set,
                    ): t
                    for t in targets
                }
                for future in as_completed(futures):
                    target = futures[future]
                    try:
                        success = future.result()
                        results[target] = success
                    except Exception as e:
                        logger.error(
                            f"Exception while rendering {target}: {e}"
                        )
                        results[target] = False

            final_output = output_dir if output_dir else (docs_root / "_site")

            succeeded = [t for t, s in results.items() if s]
            failed = [t for t, s in results.items() if not s]

            if final_output.exists():
                logger.info(
                    f"Cleaning existing output directory {final_output}"
                )
                shutil.rmtree(final_output)

            final_output.mkdir(parents=True, exist_ok=True)

            logger.info(
                f"Merging {len(succeeded)} successful targets "
                f"into {final_output}..."
            )
            sorted_succeeded = sorted(
                succeeded, key=lambda x: (x == "index", x)
            )
            for target in sorted_succeeded:
                temp_docs = target_temp_dirs[target]
                temp_site = temp_docs / "_site"
                if not temp_site.exists():
                    cache_dir = get_cache_base(docs_root) / target
                    if cache_dir.exists():
                        hash_dirs = list(cache_dir.iterdir())
                        if hash_dirs:
                            hash_dir = hash_dirs[0]
                            qmd_path = Path(TARGET_CONFIG[target]["qmd"])
                            src_parent = qmd_path.parent
                            src_stem = qmd_path.stem
                            for src_file in hash_dir.iterdir():
                                if src_file.name == "site":
                                    continue
                                if src_file.is_file():
                                    if src_parent == Path("."):
                                        dest_parent = final_output
                                    else:
                                        dest_parent = final_output / src_parent
                                    dest_name = src_stem + src_file.suffix
                                    dest = dest_parent / dest_name
                                    dest.parent.mkdir(parents=True, exist_ok=True)
                                    shutil.copy2(src_file, dest)
                                    logger.debug(
                                        f"Copied cached artifact "
                                        f"{src_file} -> {dest}"
                                    )
                if temp_site.exists():
                    if not merge_dirs(
                        temp_site, final_output, target_name=target
                    ):
                        logger.warning(
                            f"Failed to merge {target} output "
                            f"into {final_output}"
                        )
                        results[target] = False

            succeeded = [t for t, s in results.items() if s]
            failed = [t for t, s in results.items() if not s]
            if failed:
                if succeeded:
                    logger.info(f"Successful targets: {succeeded}")
                logger.error(f"Failed targets: {failed}")
                if final_output.exists():
                    logger.info(
                        f"Cleaning partial output directory {final_output} "
                        "due to failures"
                    )
                    shutil.rmtree(final_output)
                return False

            if succeeded:
                successful_set = set(succeeded)
                _cleanup_orphaned_caches(successful_set, docs_root)

            logger.info(
                f"All targets completed successfully: "
                f"{list(results.keys())}"
            )

            _sync_llms_files(final_output, docs_root)
            run_post_render_commands(EXTERNAL_CONFIG, docs_root)

            return True

        finally:
            logger.info(f"Cleaning up temp directory {base_temp}")
            try:
                shutil.rmtree(base_temp)
            except Exception as e:
                logger.warning(
                    f"Failed to clean up temp dir {base_temp}: {e}"
                )

    # Non-website or sequential mode
    use_parallel = (not sequence_mode) and (len(targets) > 1)
    build_targets_set = set(targets)

    if use_parallel:
        logger.info(
            f"Running {len(targets)} targets in parallel "
            f"(max_jobs={max_jobs})"
        )
        with ThreadPoolExecutor(max_workers=max_jobs) as executor:
            futures = {
                executor.submit(
                    build_single_target,
                    t,
                    output_dir,
                    single_command,
                    website,
                    docs_root,
                    build_targets_set,
                ): t
                for t in targets
            }
            for future in as_completed(futures):
                target, success = future.result()
                results[target] = success
    else:
        if len(targets) > 1:
            logger.info(
                f"Running {len(targets)} targets sequentially "
                "(--sequence mode)"
            )
        for target in targets:
            _, success = build_single_target(
                target,
                output_dir,
                single_command,
                website,
                docs_root,
                build_targets_set,
            )
            results[target] = success

    succeeded = [t for t, s in results.items() if s]
    failed = [t for t, s in results.items() if not s]

    if failed:
        if succeeded:
            logger.info(f"Successful targets: {succeeded}")
        logger.error(f"Failed targets: {failed}")
        return False

    logger.info(
        f"All targets completed successfully: {list(results.keys())}"
    )

    if website:
        _sync_llms_files(
            source_dir=final_site if output_dir is None else output_dir,
            docs_root=docs_root,
        )

    run_post_render_commands(EXTERNAL_CONFIG, docs_root)

    return True


# ---------------------------------------------------------------------------
# Patterns that match Quarto-generated artifacts (used by clean_quarto_artifacts
# and copy ignore)
# ---------------------------------------------------------------------------

JUPYTER_CACHE_PATH: Optional[Path] = None  # Set by initialize_config

IGNORING_ARTIFACT_PATTERNS = [
    "**/__pycache__",
    "**/*.pyc",
    "**/*.pyd",
    "**/*.log",
    "**/*_output",
    "**/*_extensions",
    "**/*_cached",
    "**/*_files",
    "**/*_libs",
    "**/_llms",
    "**/_site",
    "**/_docsbuild",
    "**/.jupyter_cache",
    "**/*.tex",
    "**/*.pdf",
    "**/*.html",
    "**/*.quarto_ipynb*",
    "**/*.quarto",
    "**/*.c2pa",
    "**/*.c2pa_identifier.svg",
]
