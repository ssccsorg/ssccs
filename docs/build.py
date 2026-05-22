#!/usr/bin/env python3
"""
SSCCS Documentation Builder

Behavior:
  - Single target: formats are rendered in a single Quarto command by default.
  - Multiple targets: runs in PARALLEL by default (targets parallel, formats per target in single command)
  - Use --sequence/-s to force sequential execution across targets.
  - Use --parallel-formats to render each format in a separate Quarto command (parallel per format).
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

Target Naming:
  - Target names are derived from the relative path of each .qmd/.md file
    with path separators replaced by hyphens.
  - Examples:
      docs/index.qmd → index
      docs/legal/index.qmd → legal-index
      docs/research/file.qmd → research-file
      docs/whitepaper/whitepaper.qmd → whitepaper-whitepaper
  - This ensures unique target names even for same‑filename documents in different directories.
  - `target_name.qmd` and `target_name.md` CANNOT be located at the same path.
  - Target names are defined externally in build.yml; build.py does not know about them.

Caching:
  - Outputs of non‑deterministic formats (pdf, beamer, html, gfm) are cached based on
    a combined SHA‑256 hash that includes the QMD source file and all its dependencies
    (included QMD files and Python files referenced by %run directives). This prevents
    unnecessary re‑renders when the source or any dependency is unchanged, even if the
    generated file would be slightly different (e.g. due to timestamps). The rendered
    output hash is still stored for the `snapshot` command, but it is not used to decide
    whether to render.
  - Cache entries are stored in a `{document_stem}_cached/` directory adjacent to
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
  - **Important:** When switching between `--website` mode and regular mode, run `./build.py clean` to avoid conflicts between Quarto artifacts.

Parallel Execution:
  - Default `--jobs` (-j) is set to **estimated physical CPU cores** (`os.cpu_count() // 2`).
    This accounts for hyperthreading on Intel/AMD CPUs, where logical cores = 2x physical.
    Quarto rendering (LuaLaTeX) is CPU-intensive, so physical core count gives better
    performance per watt and avoids memory pressure from excessive parallelism.
  - Override with `-j N` for manual control.
  - Formats within a target are rendered in a single Quarto command by default.
    Use `--parallel-formats` to render each format in separate commands (parallel per format).

Important:
  - Formats are rendered in a single Quarto command by default. Use `--parallel-formats`
    to render each format in separate `quarto render` calls (parallel per format).
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
  ./build.py --parallel-formats whitepaper     # Render each format in separate Quarto commands
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
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

DOCS_PARENT = Path(__file__).parent.parent.resolve()
DOCS_ROOT = Path(__file__).parent.absolute()

BUILD_TEMP_DIR = "_docsbuild"
BUILD_CACHE_DIR = "_cached"
JUPYTER_CACHE_DIR = "_jupyter_cache"
QUARTO_CONFIG_FILES = ["_quarto.yml", "_quarto-website.yml"]



# ---------------------------------------------------------------------------
# BuildContext — immutable runtime state (replaces global mutable variables)
# ---------------------------------------------------------------------------


@dataclass
class BuildContext:
    """Immutable context initialized once at startup from external config.
    Replaces EXTERNAL_CONFIG, TARGET_CONFIG, BUILD_FUNCTIONS, OUTPUT_DIR_TARGETS."""

    external_config: Dict[str, Any]
    target_config: Dict[str, Dict[str, Any]]
    build_functions: Dict[str, Callable[..., bool]]
    output_dir_targets: set
    initial_cached_targets: Optional[set] = None


# ---------------------------------------------------------------------------
# ConfigManager — configuration loading, target discovery, gitignore matching
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _get_website_config_cached(docs_root: Path) -> Dict[str, Any]:
    return ConfigManager.load_yaml_file(docs_root / "_quarto-website.yml") if hasattr(ConfigManager, 'load_yaml_file') else {}


class ConfigManager:
    """Configuration loading and target management."""

    @staticmethod
    def load_yaml_file(file_path: Path) -> Dict[str, Any]:
        if not file_path.exists():
            logger.debug(f"Config file not found: {file_path}")
            return {}
        try:
            import yaml
        except ImportError:
            logger.debug("PyYAML not available, cannot read YAML config")
            return {}
        try:
            with open(file_path, "r") as f:
                config = yaml.safe_load(f)
            return config or {}
        except Exception as e:
            logger.warning(f"Failed to load YAML config from {file_path}: {e}")
            return {}

    @staticmethod
    @lru_cache(maxsize=1)
    def get_website_config(docs_root: Path) -> Dict[str, Any]:
        return ConfigManager.load_yaml_file(docs_root / "_quarto-website.yml")

    @staticmethod
    def load_external_config(config_path: Optional[Path]) -> Dict[str, Any]:
        if config_path is None:
            return {}
        config = ConfigManager.load_yaml_file(config_path)
        if config:
            logger.info(f"Loaded external config from {config_path}")
        return config  # type: ignore[name-defined]

    @staticmethod
    def get_exclude_patterns(external_config: Dict[str, Any]) -> List[str]:
        return external_config.get("exclude", DEFAULT_EXCLUDE_PATTERNS)

    @staticmethod
    def get_target_config_from_external(external_config: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        return external_config.get("target_config", {})

    @staticmethod
    def matches_gitignore_pattern(rel_path: Path, patterns: List[str]) -> bool:
        import fnmatch
        path_str = str(rel_path)
        path_str_forward = path_str.replace("\\", "/")
        name = rel_path.name
        for pattern in patterns:
            pattern = pattern.strip()
            if not pattern:
                continue
            is_dir_only = pattern.endswith("/")
            if is_dir_only:
                pattern = pattern[:-1]
                parts = path_str_forward.split("/")
                for i, part in enumerate(parts[:-1]):
                    if fnmatch.fnmatch(part, pattern) or fnmatch.fnmatch(
                        parts[i], pattern.split("/")[-1] if "/" in pattern else pattern
                    ):
                        return True
                continue
            if fnmatch.fnmatch(path_str_forward, pattern):
                return True
            if fnmatch.fnmatch(path_str, pattern):
                return True
            if "/" not in pattern and "\\" not in pattern:
                if fnmatch.fnmatch(name, pattern):
                    return True
            if pattern.startswith("**/"):
                subpattern = pattern[3:]
                if fnmatch.fnmatch(name, subpattern):
                    return True
                parts = path_str_forward.split("/")
                for i in range(len(parts)):
                    suffix = "/".join(parts[i:])
                    if fnmatch.fnmatch(suffix, subpattern):
                        return True
            if pattern.endswith("/**"):
                dirpattern = pattern[:-3]
                if path_str_forward.startswith(dirpattern + "/") or path_str.startswith(dirpattern + "/"):
                    return True
        return False

    @staticmethod
    def discover_quarto_targets(docs_root: Path, exclude_patterns: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
        if exclude_patterns is None:
            exclude_patterns = DEFAULT_EXCLUDE_PATTERNS
        targets = {}
        for ext in ("*.qmd", "*.md"):
            for file_path in docs_root.rglob(ext):
                rel_path = file_path.relative_to(docs_root)
                if ConfigManager.matches_gitignore_pattern(rel_path, exclude_patterns):
                    logger.info(f"Ignoring {rel_path} (matches exclude pattern)")
                    continue
                parts = list(rel_path.parts)
                if parts:
                    last_part = parts[-1]
                    if last_part.endswith(".qmd"):
                        parts[-1] = last_part[:-4]
                    elif last_part.endswith(".md"):
                        parts[-1] = last_part[:-3]
                target_name = "-".join(parts).lower()
                target_name = re.sub(r"[^a-z0-9_-]", "", target_name)
                target_name = re.sub(r"-+", "-", target_name)
                target_name = target_name.strip("-")
                if target_name in targets:
                    suffix = 2
                    while f"{target_name}-{suffix}" in targets:
                        suffix += 1
                    target_name = f"{target_name}-{suffix}"
                targets[target_name] = {
                    "qmd": str(rel_path), "output_dir": False, "c2pa": False,
                    "copy_pdf": False, "copy_to_root": False, "to": None,
                    "copy_html": False, "copy_md": False,
                }
        return targets

    @staticmethod
    def get_target_config(docs_root: Path, external_config: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
        if external_config is None:
            external_config = {}
        exclude_patterns = ConfigManager.get_exclude_patterns(external_config)
        target_config = ConfigManager.get_target_config_from_external(external_config)
        discovered = ConfigManager.discover_quarto_targets(docs_root, exclude_patterns)
        for target, config in target_config.items():
            if target in discovered:
                discovered[target].update(config)
        return discovered


# ---------------------------------------------------------------------------
# CleanupManager — Quarto artifact patterns and cleanup
# ---------------------------------------------------------------------------


class CleanupManager:
    """Manages Quarto artifact patterns and cleanup operations."""

    IGNORING_ARTIFACT_PATTERNS = [
        "**/__pycache__", "**/*.pyc", "**/*.pyd", "**/*.log",
        "**/*_output", "**/*_extensions", "**/*_cached", "**/*_files",
        "**/*_libs", "**/_llms", "**/_site", "**/_docsbuild",
        "**/*.tex", "**/*.pdf", "**/*.html",
        "**/*.quarto_ipynb*", "**/*.quarto",
        "**/*.c2pa", "**/*.c2pa_identifier.svg",
    ]

    def __init__(self):
        self._cleaning_patterns: List[str] = self.IGNORING_ARTIFACT_PATTERNS + [
            os.path.join("..", BUILD_TEMP_DIR),
            os.path.join("..", BUILD_CACHE_DIR),
            os.path.join("..", JUPYTER_CACHE_DIR),
            "**/.jupyter_cache",
        ]

    def ignore_quarto_artifacts(self) -> Callable[[str, list[str]], set[str]]:
        basename_patterns = []
        for pat in self.IGNORING_ARTIFACT_PATTERNS:
            if pat.startswith("**/"):
                pat = pat[3:]
            basename_patterns.append(pat)
        return shutil.ignore_patterns(*basename_patterns)

    def clean(self, docs_root: Path) -> bool:
        deleted = []
        errors = []
        for pattern in self._cleaning_patterns:
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


# ---------------------------------------------------------------------------
# HashManager — file hashing and QMD dependency graph computation
# ---------------------------------------------------------------------------


class HashManager:
    """File hashing and QMD dependency graph computation."""

    @staticmethod
    @lru_cache(maxsize=128)
    def compute_file_hash(path: Path) -> str:
        try:
            with open(path, "rb") as f:
                return hashlib.file_digest(f, "sha256").hexdigest()
        except FileNotFoundError:
            raise

    @staticmethod
    @lru_cache(maxsize=32)
    def compute_quarto_file_hash_with_deps(file_path: Path) -> str:
        visited: set = set()

        def resolve(base: Path, rel: str) -> Path:
            return (base.parent / rel).resolve()

        def collect(path: Path) -> None:
            if path in visited:
                return
            visited.add(path)
            data = inspect_quarto_file(path)
            if data is None:
                return
            fi = data.get("fileInformation", {})
            entry = None
            for key, val in fi.items():
                if Path(key).resolve() == path.resolve():
                    entry = val
                    break
            if entry is None:
                return
            for gcfg in [DOCS_ROOT / file for file in QUARTO_CONFIG_FILES]:
                if gcfg.exists():
                    visited.add(gcfg.resolve())
            for inc in entry.get("includeMap", []):
                target_rel = inc.get("target")
                if target_rel:
                    target = resolve(path, target_rel)
                    if target.suffix.lower() == ".qmd":
                        collect(target)
                    else:
                        visited.add(target)
            for cell in entry.get("codeCells", []):
                source = cell.get("source", "")
                for line in source.splitlines():
                    line = line.strip()
                    if line.startswith("%run"):
                        import shlex
                        tokens = shlex.split(line)
                        if len(tokens) >= 2:
                            run_path = tokens[1]
                            run_path = run_path.split("--")[0].strip()
                            if run_path:
                                cell_file = cell.get("file")
                                base_f = Path(cell_file).parent if cell_file else path.parent
                                try:
                                    dep = (base_f / run_path).resolve()
                                    if dep.exists():
                                        visited.add(dep)
                                except (OSError, ValueError) as e:
                                    logger.debug(f"Skipping unresolvable %run dependency '{run_path}': {e}")
            for config_path in data.get("config", []):
                visited.add(Path(config_path).resolve())
            for resource_path in data.get("configResources", []):
                visited.add(Path(resource_path).resolve())
            for fmt_config in data.get("formats", {}).values():
                pandoc = fmt_config.get("pandoc", {})
                for mf in pandoc.get("metadata-files", []):
                    visited.add(resolve(path, mf))
                bib = pandoc.get("bibliography")
                if bib:
                    visited.add(resolve(path, bib))
                csl = pandoc.get("csl")
                if csl:
                    visited.add(resolve(path, csl))

        collect(file_path.resolve())

        hasher = hashlib.sha256()
        hasher.update(file_path.suffix.encode("utf-8"))
        for dep in sorted(visited, key=str):
            try:
                dep_hash = HashManager.compute_file_hash(dep)
                hasher.update(dep_hash.encode("utf-8"))
            except FileNotFoundError:
                hasher.update(b"<missing>")
        hasher.update(file_path.suffix.encode("utf-8"))
        return hasher.hexdigest()


# ---------------------------------------------------------------------------
# QuartoInspector — Quarto inspect, format detection, output path resolution
# ---------------------------------------------------------------------------


class QuartoInspector:
    """Quarto inspect, format detection, output path resolution."""

    @staticmethod
    def target_produces_pdf(config: Dict[str, Any]) -> bool:
        target_format = config.get("to")
        if target_format in ("pdf", "beamer"):
            return True
        if target_format is None and config.get("copy_pdf"):
            return True
        return False

    @staticmethod
    @lru_cache(maxsize=128)
    def inspect(file_path: Path) -> Optional[Dict[str, Any]]:
        try:
            result = subprocess.run(
                ["quarto", "inspect", str(file_path)],
                capture_output=True, text=True, check=True,
            )
            return json.loads(result.stdout)
        except Exception as e:
            logger.warning(f"Failed to inspect {file_path}: {e}")
            return None

    @staticmethod
    def get_formats(file_path: Path) -> List[str]:
        data = QuartoInspector.inspect(file_path)
        if data is None:
            return []
        return list(data.get("formats", {}).keys())

    @staticmethod
    def get_output_path(file_path: Path, fmt: str) -> Optional[Path]:
        data = QuartoInspector.inspect(file_path)
        if data is None:
            return None
        formats = data.get("formats", {})
        if fmt not in formats:
            return None
        pandoc = formats[fmt].get("pandoc", {})
        output_file = pandoc.get("output-file")
        if output_file:
            return file_path.parent / output_file
        return None

    @staticmethod
    def get_moved_path(qmd_path, fmt, config, output_dir, docs_root, source_path):
        stem = qmd_path.stem
        if fmt in ("pdf", "beamer") and config.get("copy_pdf"):
            dest_dir = output_dir.absolute() if output_dir else docs_root
            return dest_dir / f"{stem}.pdf"
        if fmt == "html" and config.get("copy_html"):
            dest_dir = output_dir.absolute() if output_dir else docs_root
            return dest_dir / "index.html"
        if fmt in ("gfm", "markdown") and config.get("copy_md"):
            dest_dir = output_dir.absolute() if output_dir else docs_root
            return dest_dir / f"{stem}.md"
        if fmt == "gfm" and config.get("copy_to_root"):
            return docs_root.parent / "README.md"
        return None

    @staticmethod
    def find_existing_output(qmd_path, fmt, config, output_dir):
        primary = QuartoInspector.get_output_path(qmd_path, fmt)
        if primary is None:
            return None
        candidates = [primary]
        if config:
            docs_root = Path(__file__).parent.absolute()
            moved = QuartoInspector.get_moved_path(qmd_path, fmt, config, output_dir, docs_root, primary)
            if moved and moved != primary:
                candidates.append(moved)
        for cand in candidates:
            if cand.exists():
                return cand
        return None

    @staticmethod
    def get_cache_dir(qmd_path: Path) -> Path:
        return qmd_path.parent / f"{qmd_path.stem}_cached"

    @staticmethod
    def get_cache_dir_for_target(qmd_path: Path, target_name: str) -> Path:
        return qmd_path.parent / f"{target_name}_cached"

    @staticmethod
    def get_cache_base() -> Path:
        return Path(__file__).parent.parent / "_cached"

    @staticmethod
    def format_to_extension(fmt: str) -> str:
        mapping = {"pdf": "pdf", "beamer": "pdf", "html": "html", "gfm": "md", "markdown": "md"}
        return mapping.get(fmt, fmt)


# ---------------------------------------------------------------------------
# LinkedArtifactRegistry — C2PA signing and linked artifact handlers
# ---------------------------------------------------------------------------


class LinkedArtifactRegistry:
    """Registry of linked artifact handlers (e.g. C2PA signing)."""

    @staticmethod
    def get_extensions(fmt: str, config: Dict[str, Any]) -> List[str]:
        return get_linked_artifact_extensions(fmt, config)

    @staticmethod
    def get_enabled(config: Dict[str, Any]) -> List:
        return get_enabled_handlers(config)


# ---------------------------------------------------------------------------
# CommandRunner — subprocess execution
# ---------------------------------------------------------------------------


class CommandRunner:
    """Subprocess execution with logging."""

    @staticmethod
    def run(cmd: List[str], cwd: Optional[Path] = None) -> bool:
        logger.info(f"Running: {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
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


# ---------------------------------------------------------------------------
# FormatRenderer — render formats (single command or parallel per format)
# ---------------------------------------------------------------------------


class FormatRenderer:
    """Renders formats using Quarto (single command or parallel per format)."""

    @staticmethod
    def _parallel(qmd_path, formats, format_output_paths, docs_root, website=False, target_name=None):
        def render_one(fmt):
            lock = _lock_for_quarto_file(qmd_path)
            with lock:
                cmd = ["quarto", "render", str(qmd_path), "--to", fmt]
                if website:
                    cmd.extend(["--profile", "website"])
                if not CommandRunner.run(cmd, cwd=docs_root):
                    logger.error(f"Quarto render failed for {qmd_path.name} (format {fmt}).")
                    return False
                if fmt in NON_DETERMINISTIC_FORMATS:
                    out = format_output_paths[fmt]
                    if out.exists():
                        update_format_cache(qmd_path, fmt, out, target_name=target_name)
                return True
        with ThreadPoolExecutor(max_workers=len(formats)) as executor:
            futures = {executor.submit(render_one, f): f for f in formats}
            return sum(1 for fu in as_completed(futures) if fu.result()) == len(formats)

    @staticmethod
    def _single(qmd_path, formats, format_output_paths, docs_root, website=False, target_name=None):
        lock = _lock_for_quarto_file(qmd_path)
        with lock:
            fmt_str = ",".join(formats)
            cmd = ["quarto", "render", str(qmd_path), "--to", fmt_str]
            if website:
                cmd.extend(["--profile", "website"])
            if not CommandRunner.run(cmd, cwd=docs_root):
                logger.error(f"Quarto render failed for {qmd_path.name} (formats {fmt_str}).")
                return False
            for fmt in formats:
                if fmt in NON_DETERMINISTIC_FORMATS:
                    out = format_output_paths[fmt]
                    if out.exists():
                        update_format_cache(qmd_path, fmt, out, target_name=target_name)
            return True

    @staticmethod
    def render(qmd_path, formats, format_output_paths, docs_root, single_command, website=False, target_name=None):
        if single_command:
            return FormatRenderer._single(qmd_path, formats, format_output_paths, docs_root, website, target_name)
        return FormatRenderer._parallel(qmd_path, formats, format_output_paths, docs_root, website, target_name)


# ---------------------------------------------------------------------------
# TargetBuilder — single target build (wraps build_generic)
# ---------------------------------------------------------------------------


class TargetBuilder:
    @staticmethod
    def build(target, config, output_dir=None, single_command=True, website=False, docs_root=None, build_targets_set=None):
        return build_generic(target, config, output_dir, single_command, website, docs_root, build_targets_set)


# ---------------------------------------------------------------------------
# BuildOrchestrator — multi-target builds initialization and orchestration
# ---------------------------------------------------------------------------


class BuildOrchestrator:
    @staticmethod
    def initialize_config(config_path=None):
        return initialize_config(config_path)

    @staticmethod
    def parse_targets(targets_arg):
        parsed = []
        for t in targets_arg:
            if "," in t:
                parsed.extend([x.strip() for x in t.split(",") if x.strip()])
            elif t.strip():
                parsed.append(t.strip())
        return parsed

    @staticmethod
    def validate_targets(targets):
        # Access BUILD_FUNCTIONS via closure/module-level (initialized by initialize_config)
        global BUILD_FUNCTIONS
        invalid = [t for t in targets if t not in BUILD_FUNCTIONS]
        if invalid:
            logger.error(f"Unknown target(s): {invalid}. Available: {list(BUILD_FUNCTIONS.keys())}")
            sys.exit(1)
        return targets

    @staticmethod
    def build_single_target(target, output_dir, single_command, website=False, build_targets_set=None):
        return build_single_target(target, output_dir, single_command, website, build_targets_set)

    @staticmethod
    def _render_target_isolated(target, output_dir, single_command, website, temp_docs, build_targets_set=None):
        return _render_target_isolated(target, output_dir, single_command, website, temp_docs, build_targets_set)


# ---------------------------------------------------------------------------
# PreBuildRunner — pre-build command execution
# ---------------------------------------------------------------------------


class PreBuildRunner:
    @staticmethod
    def run(external_config: Dict[str, Any], docs_root: Path, target_name: Optional[str] = None) -> None:
        pre_build_section = external_config.get("pre_build", [])
        if not pre_build_section:
            return
        if isinstance(pre_build_section, list):
            global_commands = pre_build_section
            target_commands: Dict[str, Any] = {}
        elif isinstance(pre_build_section, dict):
            global_commands = pre_build_section.get("_global", [])
            target_commands = {k: v for k, v in pre_build_section.items() if k != "_global"}
        else:
            logger.warning(f"Invalid pre_build format: expected list or dict, got {type(pre_build_section).__name__}")
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
                logger.warning(f"Invalid pre_build entry for target '{target_name}': {target_cmds}, skipping.")
        if not commands_to_run:
            return
        if target_name:
            logger.info(f"Running {len(commands_to_run)} pre-build command(s) for target '{target_name}'...")
        else:
            logger.info(f"Running {len(commands_to_run)} global pre-build command(s)...")
        for cmd in commands_to_run:
            if not cmd or not isinstance(cmd, list):
                logger.warning(f"Invalid pre_build entry: {cmd}, skipping.")
                continue
            executable = cmd[0]
            if not shutil.which(executable):
                logger.info(f"Pre-build: '{executable}' not found in PATH, skipping.")
                continue
            logger.info(f"Pre-build: running {' '.join(cmd)}")
            try:
                result = subprocess.run(cmd, cwd=docs_root, capture_output=True, text=True)
                if result.stdout:
                    logger.debug(result.stdout.strip())
                if result.stderr:
                    logger.warning(result.stderr.strip())
                if result.returncode != 0:
                    logger.warning(f"Pre-build command '{executable}' failed with exit code {result.returncode}, continuing build...")
                else:
                    logger.info(f"Pre-build command '{' '.join(cmd)}' succeeded.")
            except Exception as e:
                logger.warning(f"Pre-build command '{executable}' raised an exception: {e}, continuing build...")


# ---------------------------------------------------------------------------
# PostRenderRunner — post-render command execution
# ---------------------------------------------------------------------------


class PostRenderRunner:
    """
    Executes post-render commands from external configuration.
    Mirrors PreBuildRunner but runs after all targets have been rendered and merged.
    """

    @staticmethod
    def run(external_config: Dict[str, Any], docs_root: Path, target_name: Optional[str] = None) -> None:
        post_render_section = external_config.get("post_render", [])
        if not post_render_section:
            return
        if isinstance(post_render_section, list):
            global_commands = post_render_section
            target_commands: Dict[str, Any] = {}
        elif isinstance(post_render_section, dict):
            global_commands = post_render_section.get("_global", [])
            target_commands = {k: v for k, v in post_render_section.items() if k != "_global"}
        else:
            logger.warning(f"Invalid post_render format: expected list or dict, got {type(post_render_section).__name__}")
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
                logger.warning(f"Invalid post_render entry for target '{target_name}': {target_cmds}, skipping.")
        if not commands_to_run:
            return
        if target_name:
            logger.info(f"Running {len(commands_to_run)} post-render command(s) for target '{target_name}'...")
        else:
            logger.info(f"Running {len(commands_to_run)} global post-render command(s)...")
        for cmd in commands_to_run:
            if not cmd or not isinstance(cmd, list):
                logger.warning(f"Invalid post_render entry: {cmd}, skipping.")
                continue
            executable = cmd[0]
            if not shutil.which(executable):
                logger.info(f"Post-render: '{executable}' not found in PATH, skipping.")
                continue
            logger.info(f"Post-render: running {' '.join(cmd)}")
            try:
                result = subprocess.run(cmd, cwd=docs_root, capture_output=True, text=True)
                if result.stdout:
                    logger.debug(result.stdout.strip())
                if result.stderr:
                    logger.warning(result.stderr.strip())
                if result.returncode != 0:
                    logger.warning(f"Post-render command '{executable}' failed with exit code {result.returncode}, continuing...")
                else:
                    logger.info(f"Post-render command '{' '.join(cmd)}' succeeded.")
            except Exception as e:
                logger.warning(f"Post-render command '{executable}' raised an exception: {e}, continuing...")


# ---------------------------------------------------------------------------
# CLI — command-line interface entry point
# ---------------------------------------------------------------------------


class CLI:
    @staticmethod
    def main():
        return main()
def load_yaml_file(file_path: Path) -> Dict[str, Any]:
    return ConfigManager.load_yaml_file(file_path)


def get_website_config(docs_root: Path) -> Dict[str, Any]:
    return ConfigManager.get_website_config(docs_root)


BUILD_TEMP_PATH = DOCS_PARENT / BUILD_TEMP_DIR
BUILD_CACHE_PATH = DOCS_PARENT / BUILD_CACHE_DIR
JUPYTER_CACHE_PATH = DOCS_PARENT / JUPYTER_CACHE_DIR

os.environ["JUPYTERCACHE"] = str(JUPYTER_CACHE_PATH)

# Formats that are considered non‑deterministic (cached based on QMD hash only)
NON_DETERMINISTIC_FORMATS = {"pdf", "beamer", "html", "gfm"}

# Patterns that match Quarto‑generated artifacts (used by clean_quarto_artifacts and copy ignore)
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
    # quarto: final artifacts
    "**/*.tex",
    "**/*.pdf",
    "**/*.html",
    # quarto: global
    "**/*.quarto_ipynb*",
    "**/*.quarto",
    # c2pa
    "**/*.c2pa",
    "**/*.c2pa_identifier.svg",
]

# CLEANING_ARTIFACT_PATTERNS — now inside CleanupManager
# CLEANING_ARTIFACT_PATTERNS = IGNORING_ARTIFACT_PATTERNS + [
#    os.path.join("..", BUILD_TEMP_DIR),
#    os.path.join("..", BUILD_CACHE_DIR),
#    os.path.join("..", JUPYTER_CACHE_DIR),
#    "**/.jupyter_cache",
#]


def ignore_quarto_artifacts() -> Callable[[str, list[str]], set[str]]:
    return CleanupManager().ignore_quarto_artifacts()


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


def compute_file_hash(path: Path) -> str:
    return HashManager.compute_file_hash(path)


@lru_cache(maxsize=32)
def compute_quarto_file_hash_with_deps(file_path: Path) -> str:
    return HashManager.compute_quarto_file_hash_with_deps(file_path)


def target_produces_pdf(config: Dict[str, Any]) -> bool:
    return QuartoInspector.target_produces_pdf(config)


def inspect_quarto_file(file_path: Path) -> Optional[Dict[str, Any]]:
    return QuartoInspector.inspect(file_path)


def get_formats_from_quarto_file(file_path: Path) -> List[str]:
    return QuartoInspector.get_formats(file_path)


def get_format_output_path(file_path: Path, fmt: str) -> Optional[Path]:
    return QuartoInspector.get_output_path(file_path, fmt)


def get_moved_path_for_format(qmd_path, fmt, config, output_dir, docs_root, source_path):
    return QuartoInspector.get_moved_path(qmd_path, fmt, config, output_dir, docs_root, source_path)


def find_existing_output(qmd_path, fmt, config, output_dir):
    return QuartoInspector.find_existing_output(qmd_path, fmt, config, output_dir)


def get_cache_dir(qmd_path: Path) -> Path:
    return QuartoInspector.get_cache_dir(qmd_path)


def get_cache_dir_for_target(qmd_path: Path, target_name: str) -> Path:
    return QuartoInspector.get_cache_dir_for_target(qmd_path, target_name)


def get_cache_base() -> Path:
    return QuartoInspector.get_cache_base()


def format_to_extension(fmt: str) -> str:
    return QuartoInspector.format_to_extension(fmt)


# ---------------------------------------------------------------------------
# Linked Artifact System
# ---------------------------------------------------------------------------
# Linked artifacts are files generated alongside a primary output (e.g. PDF)
# that should be cached and restored together.  Each handler is responsible
# for:
#   1. Declaring which primary formats it applies to
#   2. Returning the linked file extension
#   3. Generating the linked file (e.g. C2PA signing)
#   4. Returning the path to the generated file


@dataclass
class LinkedArtifactHandler:
    """Base class for linked artifact handlers."""

    name: str
    # Map of primary format -> linked file extension
    extensions: Dict[str, str] = field(default_factory=dict)
    # Config key to check if this handler is enabled
    config_key: str = ""

    def is_enabled(self, config: Dict[str, Any]) -> bool:
        """Check if this handler is enabled for the given config."""
        if not self.config_key:
            return True
        return bool(config.get(self.config_key, False))

    def get_extension(self, fmt: str) -> Optional[str]:
        """Return the linked file extension for the given primary format."""
        return self.extensions.get(fmt)

    def generate(
        self,
        qmd_path: Path,
        fmt: str,
        primary_path: Path,
        docs_root: Path,
        config: Dict[str, Any],
        target_name: Optional[str] = None,
    ) -> Optional[Path]:
        """
        Generate the linked artifact file.
        Returns the path to the generated file, or None if generation failed.
        Subclasses should override this.

        Args:
            qmd_path: Path to the source QMD file
            fmt: Output format
            primary_path: Path to the primary output file
            docs_root: Root directory of documentation
            config: Target configuration
            target_name: Optional target name for artifact naming
        """
        return None


class C2PAArtifactHandler(LinkedArtifactHandler):
    """C2PA signing handler for PDF/HTML outputs."""

    def __init__(self):
        super().__init__(
            name="c2pa",
            extensions={"pdf": "c2pa", "beamer": "c2pa", "html": "c2pa"},
            config_key="c2pa",
        )

    def generate(
        self,
        qmd_path: Path,
        fmt: str,
        primary_path: Path,
        docs_root: Path,
        config: Dict[str, Any],
        target_name: Optional[str] = None,
    ) -> Optional[Path]:
        # Use original QMD stem for artifact naming (preserves original filename)
        c2pa_stem = qmd_path.stem
        manifest_path = qmd_path.parent / f"{c2pa_stem}.c2pa_manifest.json"
        output_c2pa = primary_path.parent / f"{c2pa_stem}.c2pa"
        output_c2pa.parent.mkdir(parents=True, exist_ok=True)
        sign_cmd = [
            "python3",
            str(docs_root / "_utils" / "sign_c2pa.py"),
            "--pdf",
            str(primary_path),
            "--manifest",
            str(manifest_path),
            "--output",
            str(output_c2pa),
        ]
        if run_command(sign_cmd, cwd=docs_root):
            return output_c2pa
        logger.warning(f"C2PA signing failed for {qmd_path.name}.")
        return None


# Registry of linked artifact handlers
LINKED_ARTIFACT_HANDLERS: List[LinkedArtifactHandler] = [
    C2PAArtifactHandler(),
]


def get_linked_artifact_extensions(fmt: str, config: Dict[str, Any]) -> List[str]:
    """
    Return a list of linked artifact extensions for the given primary format.
    Only returns extensions for enabled handlers.
    """
    result = []
    for handler in LINKED_ARTIFACT_HANDLERS:
        if handler.is_enabled(config):
            ext = handler.get_extension(fmt)
            if ext:
                result.append(ext)
    return result


def get_enabled_handlers(config: Dict[str, Any]) -> List[LinkedArtifactHandler]:
    """Return list of enabled handlers for the given config."""
    return [h for h in LINKED_ARTIFACT_HANDLERS if h.is_enabled(config)]


def get_cached_artifact_path(
    target_name: str, hash_str: str, fmt: str, linked_ext: Optional[str] = None
) -> Path:
    """
    Return the path to a cached artifact file for the given target, hash, and format.
    If linked_ext is provided, returns the path for the linked artifact file.
    """
    ext = linked_ext if linked_ext else format_to_extension(fmt)
    return get_cache_base() / target_name / hash_str / f"{target_name}.{ext}"


def find_cached_artifact(
    target_name: str, hash_str: str, fmt: str, linked_ext: Optional[str] = None
) -> Optional[Path]:
    """
    Return the cached artifact path if it exists, otherwise None.
    If linked_ext is provided, looks for the linked artifact file.
    """
    path = get_cached_artifact_path(target_name, hash_str, fmt, linked_ext=linked_ext)
    if path.exists():
        return path
    return None


# Global: snapshot of cached target names captured before build starts
_INITIAL_CACHED_TARGETS: Optional[set] = None


def capture_initial_cached_targets() -> None:
    """
    Capture the set of cached target names before build starts.
    This is used to detect if the document set has changed during the build.
    """
    global _INITIAL_CACHED_TARGETS
    cache_base = get_cache_base()
    if not cache_base.exists():
        _INITIAL_CACHED_TARGETS = set()
    else:
        _INITIAL_CACHED_TARGETS = {d.name for d in cache_base.iterdir() if d.is_dir()}


def get_initial_cached_targets() -> set:
    """Return the snapshot of cached target names captured before build starts."""
    if _INITIAL_CACHED_TARGETS is None:
        return set()
    return _INITIAL_CACHED_TARGETS


def should_rerender_for_sidebar(build_targets: set) -> bool:
    """
    Check if HTML must be re-rendered to update sidebar.
    Returns True if:
      - Any target in the build set is not yet cached (new files added), OR
      - Any cached target is not in the build set (files deleted/changed)

    This ensures the sidebar is updated whenever the document set changes,
    whether by addition, deletion, or modification of source files.
    """
    cached_targets = get_initial_cached_targets()
    # Check for new files (targets not in cache)
    has_new_files = not build_targets.issubset(cached_targets)
    # Check for deleted/changed files (cached targets not in build set)
    has_deleted_files = not cached_targets.issubset(build_targets)
    return has_new_files or has_deleted_files


def cache_site_directory(target_name: str, hash_str: str, site_dir: Path) -> bool:
    """
    Cache the entire _site directory for a target (including site_libs).
    The directory is copied to _cached/{target}/{hash}/site/.
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
            if len(a) == 64 and len(b) == 64:  # SHA-256 hex length
                return (a, b)
    except Exception:
        pass
    return None


def write_hash_pair(cache_file: Path, qmd_hash: str, output_hash: str) -> None:
    """Write hash pair to cache file."""
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_file, "w") as f:
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
    logger.info(
        f"Checking cache for {target_name} ({fmt}): QMD hash {qmd_hash[:16]}..."
    )

    # Check if cached artifact exists
    cached = find_cached_artifact(target_name, qmd_hash, fmt)
    if cached is not None:
        # Cache hit: copy the artifact to the output location
        output_path = get_format_output_path(file_path, fmt)
        if output_path is None:
            logger.warning(
                f"Cannot determine output path for {target_name} ({fmt}), proceeding with render."
            )
            return True
        # Ensure parent directory exists
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
        # Also restore linked artifacts if they exist
        cfg = config or {}
        for linked_ext in get_linked_artifact_extensions(fmt, cfg):
            cached_linked = find_cached_artifact(
                target_name, qmd_hash, fmt, linked_ext=linked_ext
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
        # Also update the old-style cache file for compatibility (optional)
        # For now, we skip updating the old cache.
        return False

    # Cache miss: need render
    logger.info(f"Cache miss for {target_name} ({fmt}) – QMD hash {qmd_hash[:16]}...")
    return True


def update_format_cache(
    file_path: Path,
    fmt: str,
    output_path: Path,
    target_name: Optional[str] = None,
    linked_artifacts: Optional[Dict[str, Path]] = None,
) -> None:
    """Update cache after successful render of a specific format.

    Args:
        file_path: Path to the source QMD file
        fmt: Output format (pdf, html, etc.)
        output_path: Path to the rendered output file
        target_name: Name of the build target
        linked_artifacts: Dict mapping linked file extension -> path to the linked artifact file
    """
    qmd_hash = compute_quarto_file_hash_with_deps(file_path)
    output_hash = compute_file_hash(output_path)
    logger.info(
        f"Updating {fmt} cache for {file_path.name}: output hash {output_hash[:16]}..."
    )

    # New cache system: store artifact file in _cached/{target_name}/{hash}/{target_name}.{ext}
    if target_name is not None:
        # Delete existing cache entries for this target with different hash to prevent infinite accumulation
        # This ensures only the current valid cache (with current qmd_hash) is kept
        target_cache_dir = get_cache_base() / target_name
        if target_cache_dir.exists():
            try:
                for existing_hash_dir in target_cache_dir.iterdir():
                    if (
                        existing_hash_dir.is_dir()
                        and existing_hash_dir.name != qmd_hash
                    ):
                        shutil.rmtree(existing_hash_dir)
                        logger.info(
                            f"Deleted old cache directory for target '{target_name}' (hash: {existing_hash_dir.name[:16]}...) to prevent accumulation"
                        )
            except Exception as e:
                logger.warning(
                    f"Failed to delete old cache for target '{target_name}': {e}"
                )

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

        # Cache linked artifacts if they exist
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
        logger.info(
            f"Target {target} has no defined output formats, skipping cache refresh."
        )
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
                    logger.info(
                        f"Removed cache file for {target} ({fmt}) – QMD changed or cache missing"
                    )
                else:
                    logger.info(
                        f"No cache file for {target} ({fmt}) – will rebuild on next run"
                    )
                # Also remove new cache system directory if exists
                if existing_cache is not None:
                    old_hash = existing_cache[0]
                    old_cache_dir = get_cache_base() / target / old_hash
                    if old_cache_dir.exists():
                        shutil.rmtree(old_cache_dir)
                        logger.info(
                            f"Removed new cache directory for {target} ({fmt}) – QMD changed"
                        )
        else:
            # No output file (or output path unknown), remove cache file for this format
            if cache_file.exists():
                cache_file.unlink()
                logger.info(f"Removed cache file for {target} ({fmt} output missing)")
            else:
                logger.info(f"No cache file for {target} ({fmt} output missing)")
    return True


def clean_quarto_artifacts(docs_root: Path) -> bool:
    return CleanupManager().clean(docs_root)


# Default exclude patterns (gitignore-style)
DEFAULT_EXCLUDE_PATTERNS: List[str] = []


def load_external_config(config_path: Optional[Path]) -> Dict[str, Any]:
    return ConfigManager.load_external_config(config_path)


def get_exclude_patterns(external_config: Dict[str, Any]) -> List[str]:
    return ConfigManager.get_exclude_patterns(external_config)


def get_target_config_from_external(external_config: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return ConfigManager.get_target_config_from_external(external_config)


def matches_gitignore_pattern(rel_path: Path, patterns: List[str]) -> bool:
    return ConfigManager.matches_gitignore_pattern(rel_path, patterns)


def discover_quarto_targets(docs_root: Path, exclude_patterns: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
    return ConfigManager.discover_quarto_targets(docs_root, exclude_patterns)


def get_target_config(docs_root: Path, external_config: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
    return ConfigManager.get_target_config(docs_root, external_config)


def run_command(cmd: List[str], cwd: Optional[Path] = None) -> bool:
    return CommandRunner.run(cmd, cwd)


def _render_formats_parallel(qmd_path, formats, format_output_paths, docs_root, website=False, target_name=None):
    return FormatRenderer._parallel(qmd_path, formats, format_output_paths, docs_root, website, target_name)


def _render_formats_single(qmd_path, formats, format_output_paths, docs_root, website=False, target_name=None):
    return FormatRenderer._single(qmd_path, formats, format_output_paths, docs_root, website, target_name)


def _render_formats(qmd_path, formats, format_output_paths, docs_root, single_command, website=False, target_name=None):
    return FormatRenderer.render(qmd_path, formats, format_output_paths, docs_root, single_command, website, target_name)


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
    Generic build function that renders a .qmd or .md file and performs optional post‑processing.
    Formats are rendered in a single command by default. Set `single_command=False`
    to render each format in separate commands (parallel per format).
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
                if not should_rerender_for_sidebar(build_targets_set or set()):
                    logger.info(
                        f"Cache hit for {target} ({fmt}), document set unchanged, using cached version."
                    )
                    site_dir = docs_root / "_site"
                    restore_site_directory(target, qmd_hash, site_dir)
                    logger.info(
                        f"{target} build completed successfully (native Markdown, website)."
                    )
                    return True
                logger.info(
                    f"Cache hit for {target} ({fmt}), document set changed, re-rendering HTML to update sidebar."
                )
            logger.info(
                f"Rendering {source_path.name} as native Markdown (website mode, HTML only)"
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
            # Cache the rendered HTML artifact
            output_path = get_format_output_path(source_path, fmt)
            if output_path and output_path.exists():
                update_format_cache(source_path, fmt, output_path, target_name=target)
            else:
                # Try under _site subdirectory
                if docs_root:
                    try:
                        rel = source_path.relative_to(docs_root)
                        site_path = docs_root / "_site" / rel.with_suffix(".html")
                        if site_path.exists():
                            update_format_cache(
                                source_path, fmt, site_path, target_name=target
                            )
                    except ValueError:
                        pass
            # Cache the entire _site directory for future reuse
            site_dir = docs_root / "_site"
            cache_site_directory(target, qmd_hash, site_dir)
            logger.info(
                f"{target} build completed successfully (native Markdown, website)."
            )
            return True

        # Non‑website mode: apply _cached cache policy
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
        logger.info(
            f"Rendering {source_path.name} as native Markdown (formats: {', '.join(formats)})"
        )
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
    # Determine formats to render
    target_format = config.get("to")
    if target_format is None:
        # inspect the QMD to get all formats
        formats = get_formats_from_quarto_file(qmd_path)
        if not formats:
            logger.error(
                f"Could not determine output formats for {qmd_path}. "
                f"Please specify a format in the target config or ensure 'quarto inspect' works."
            )
            return False
    else:
        formats = [target_format]

    # Validate that we can determine output paths for all formats
    format_output_paths = {}  # fmt -> Path (expected output before moves)
    for fmt in formats:
        output_path = get_format_output_path(qmd_path, fmt)
        if output_path is None:
            logger.error(
                f"Cannot determine output path for format '{fmt}' of {qmd_path}. "
                f"Please ensure 'quarto inspect' provides an 'output-file' or that the format is properly defined."
            )
            return False
        format_output_paths[fmt] = output_path

    # Determine which formats need rendering (only for non‑website mode)
    formats_to_render = []
    if not website:
        for fmt in formats:
            if should_render_format(qmd_path, fmt, target, config, output_dir):
                formats_to_render.append(fmt)

    # qmd_hash placeholder — only used when website=True, initialized here to keep type checker happy
    qmd_hash = ""

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
            if "html" in formats:
                if not should_rerender_for_sidebar(build_targets_set or set()):
                    logger.info(
                        f"All formats for {target} are cached, document set unchanged, using cached version."
                    )
                    for fmt in formats:
                        cached = find_cached_artifact(target, qmd_hash, fmt)
                        output_path = format_output_paths.get(fmt)
                        if cached:
                            if output_path:
                                output_path.parent.mkdir(parents=True, exist_ok=True)
                                shutil.copy2(cached, output_path)
                        # Also restore linked artifacts if they exist
                        for linked_ext in get_linked_artifact_extensions(fmt, config):
                            cached_linked = find_cached_artifact(
                                target, qmd_hash, fmt, linked_ext=linked_ext
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
                                            f"Restored cached linked artifact ({linked_ext}) to {linked_output_path}"
                                        )
                                    except Exception as e:
                                        logger.warning(
                                            f"Failed to copy cached linked artifact for {target} ({fmt}): {e}"
                                        )
                    site_dir = docs_root / "_site"
                    restore_site_directory(target, qmd_hash, site_dir)
                    return True
                logger.info(
                    f"All formats for {target} are cached, document set changed, re-rendering HTML to update sidebar."
                )
                # Copy non-HTML cached artifacts to output locations
                for fmt in formats:
                    if fmt == "html":
                        continue
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
                # Re-render HTML only with --to html to avoid re-rendering PDF/beamer
                logger.info(
                    f"Re-rendering {source_path.name} in website mode (HTML only, to update sidebar)"
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
                        f"Quarto render failed for {source_path.name} (website mode, HTML refresh)."
                    )
                    return False
                # Cache the updated HTML artifact
                output_path = format_output_paths.get("html")
                if output_path and output_path.exists():
                    update_format_cache(
                        qmd_path, "html", output_path, target_name=target
                    )
                else:
                    # Try under _site subdirectory
                    if docs_root:
                        try:
                            if output_path:
                                rel = output_path.relative_to(docs_root)
                                site_path = docs_root / "_site" / rel
                                if site_path.exists():
                                    update_format_cache(
                                        qmd_path, "html", site_path, target_name=target
                                    )
                            else:
                                pass

                        except (ValueError, AttributeError):
                            pass
                site_dir = docs_root / "_site"
                cache_site_directory(target, qmd_hash, site_dir)
            else:
                # No HTML format defined – restore all cached artifacts, no re-render needed
                logger.info(
                    f"All formats for {target} are cached (no HTML), restoring from cache."
                )
                for fmt in formats:
                    cached = find_cached_artifact(target, qmd_hash, fmt)
                    if cached:
                        output_path = format_output_paths.get(fmt)
                        if output_path:
                            output_path.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(cached, output_path)
                        # Also restore linked artifacts if they exist
                        for linked_ext in get_linked_artifact_extensions(fmt, config):
                            cached_linked = find_cached_artifact(
                                target, qmd_hash, fmt, linked_ext=linked_ext
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
                                            f"Restored cached linked artifact ({linked_ext}) to {linked_output_path}"
                                        )
                                    except Exception as e:
                                        logger.warning(
                                            f"Failed to copy cached linked artifact for {target} ({fmt}): {e}"
                                        )
                # Restore cached site directory
                site_dir = docs_root / "_site"
                restore_site_directory(target, qmd_hash, site_dir)
        else:
            # Not all formats cached, proceed with render
            logger.info(
                f"Rendering {source_path.name} in website mode (no --to, all formats from YAML)"
            )
            quarto_cmd = ["quarto", "render", str(source_path), "--profile", "website"]
            if not run_command(quarto_cmd, cwd=docs_root):
                logger.error(
                    f"Quarto render failed for {source_path.name} (website mode)."
                )
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
                                    qmd_path, fmt, site_path, target_name=target
                                )
                        except (ValueError, AttributeError):
                            pass
    else:
        if formats_to_render:
            logger.info(f"Rendering {len(formats_to_render)} format(s) for {target}")
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
            logger.info(f"All formats for {target} are up‑to‑date, skipping render.")

    # Step 2: Generate linked artifacts (e.g. C2PA signing)
    # Linked artifacts are generated alongside primary outputs and must be cached together.
    # If a linked artifact is missing from cache, the generation step must run.
    logger.info(f"format_output_paths keys: {list(format_output_paths.keys())}")
    enabled_handlers = get_enabled_handlers(config)
    if enabled_handlers:
        # Determine primary paths for each format that may have linked artifacts
        primary_paths: Dict[str, Path] = {}
        for fmt in formats:
            path = format_output_paths.get(fmt)
            if path:
                if website:
                    # Website output goes to _site subdirectory
                    try:
                        rel = path.relative_to(docs_root)
                        primary_paths[fmt] = docs_root / "_site" / rel
                    except ValueError:
                        primary_paths[fmt] = path
                else:
                    primary_paths[fmt] = path
            # Also consider moved location via copy_pdf (if config has copy_pdf)
            if config.get("copy_pdf") and output_dir and fmt in ("pdf", "beamer"):
                dest_dir = Path(output_dir).absolute() if output_dir else docs_root
                primary_paths[fmt] = dest_dir / f"{stem}.{format_to_extension(fmt)}"

        # Generate linked artifacts for each primary format
        linked_artifacts: Dict[str, Dict[str, Path]] = {}  # fmt -> {ext: path}
        for fmt, primary_path in primary_paths.items():
            if not primary_path.exists():
                continue
            linked_artifacts[fmt] = {}
            for handler in enabled_handlers:
                ext = handler.get_extension(fmt)
                if ext is None:
                    continue
                # Check if linked artifact already exists (from cache restoration)
                # Use original QMD stem for artifact naming (preserves original filename)
                linked_stem = qmd_path.stem
                existing_linked = primary_path.parent / f"{linked_stem}.{ext}"
                if existing_linked.exists():
                    linked_artifacts[fmt][ext] = existing_linked
                    logger.info(
                        f"Linked artifact ({ext}) already exists at {existing_linked}, skipping generation."
                    )
                    continue
                # Generate the linked artifact
                generated_path = handler.generate(
                    qmd_path, fmt, primary_path, docs_root, config, target_name=target
                )
                if generated_path:
                    linked_artifacts[fmt][ext] = generated_path
                    logger.info(
                        f"Generated linked artifact ({ext}) for {fmt} at {generated_path}"
                    )
                else:
                    logger.warning(
                        f"Failed to generate linked artifact ({ext}) for {fmt}"
                    )

        # Update cache with linked artifacts
        for fmt, artifacts in linked_artifacts.items():
            if artifacts:
                primary_path = primary_paths.get(fmt)
                if primary_path and primary_path.exists():
                    update_format_cache(
                        qmd_path,
                        fmt,
                        primary_path,
                        target_name=target,
                        linked_artifacts=artifacts,
                    )

    # In website mode, cache site directory AFTER linked artifact generation
    if website:
        site_dir = docs_root / "_site"
        cache_site_directory(target, qmd_hash, site_dir)

    # Step 3: Move primary output and linked artifacts to output_dir (if enabled)
    if config.get("copy_pdf"):
        # Determine possible primary output paths
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
        # Try each candidate
        primary_path = None
        for cand in candidates:
            if cand and cand.exists():
                primary_path = cand
                break
        if primary_path and primary_path.exists():
            dest_dir = Path(output_dir).absolute() if output_dir else docs_root
            dest_dir.mkdir(parents=True, exist_ok=True)
            primary_ext = format_to_extension(
                "pdf" if "pdf" in format_output_paths else "beamer"
            )
            dest_primary = dest_dir / f"{stem}.{primary_ext}"
            # Determine linked artifact paths (uses original QMD stem to preserve original filename)
            linked_stem = qmd_path.stem
            source_linked = {}
            dest_linked = {}
            for linked_ext in get_linked_artifact_extensions(
                "pdf" if "pdf" in format_output_paths else "beamer", config
            ):
                source_linked[linked_ext] = (
                    primary_path.parent / f"{linked_stem}.{linked_ext}"
                )
                dest_linked[linked_ext] = dest_dir / f"{linked_stem}.{linked_ext}"
            # Avoid moving if source and destination are the same
            if dest_primary.resolve() != primary_path.resolve():
                try:
                    shutil.move(str(primary_path), str(dest_primary))
                    logger.info(
                        f"Moved primary output ({primary_ext}) to {dest_primary}"
                    )
                    # Also move linked artifacts if they exist
                    for linked_ext, src_path in source_linked.items():
                        if src_path.exists():
                            shutil.move(str(src_path), str(dest_linked[linked_ext]))
                            logger.info(
                                f"Moved linked artifact ({linked_ext}) to {dest_linked[linked_ext]}"
                            )
                except Exception as e:
                    logger.error(f"Failed to move primary output: {e}")
                    return False
            else:
                logger.info("Primary output already at destination, skipping move.")

    # Step 5: Copy HTML/Markdown to output_dir (if enabled)
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
            # Note: assumes Markdown format is either 'gfm' or 'markdown'
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
                    f"copy_md enabled but Markdown output not found for {target}"
                )

    logger.info(f"{target} build completed successfully.")
    return True


EXTERNAL_CONFIG: Dict[str, Any] = {}
TARGET_CONFIG: Dict[str, Dict[str, Any]] = {}
BUILD_FUNCTIONS: Dict[str, Callable[..., bool]] = {}
OUTPUT_DIR_TARGETS: set = set()


def initialize_config(config_path: Optional[Path]) -> None:
    """Initialize global configuration from external file."""
    global EXTERNAL_CONFIG, TARGET_CONFIG, BUILD_FUNCTIONS, OUTPUT_DIR_TARGETS
    EXTERNAL_CONFIG = load_external_config(config_path)
    TARGET_CONFIG = get_target_config(DOCS_ROOT, EXTERNAL_CONFIG)
    JUPYTER_CACHE_PATH.mkdir(parents=True, exist_ok=True)

    # Build function mapping per target (auto-generated from TARGET_CONFIG)
    BUILD_FUNCTIONS = {}
    for target, config in TARGET_CONFIG.items():
        # Create a closure that captures target and config
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

    # list of targets that receive output_dir argument (those with output_dir=True in config)
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
            f"Unknown target(s): {invalid}. Available: {list(BUILD_FUNCTIONS.keys())}"
        )
        sys.exit(1)
    return targets


def build_single_target(
    target: str,
    output_dir: Optional[Path],
    single_command: bool,
    website: bool = False,
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
                build_targets_set=build_targets_set,
            )
        else:
            success = func(
                single_command=single_command,
                website=website,
                build_targets_set=build_targets_set,
            )
        logger.info(f"Finished build: {target} -> {'✓' if success else '✗'}")
        return target, success
    except Exception as e:
        logger.error(f"Exception while building {target}: {e}")
        return target, False


# ---------------------------------------------------------------------------
# Shared Asset Merger System
# ---------------------------------------------------------------------------
# Shared assets are files that need content-level merging when combining
# multiple target outputs (e.g., search.json, sitemap.xml).
# Each merger handler is responsible for:
#   1. Declaring which files it handles (by filename pattern)
#   2. Merging source content into destination content appropriately
#   3. Handling the case when destination doesn't exist (simple copy)


@dataclass
class SharedAssetMerger:
    """Base class for shared asset merger handlers."""

    name: str
    # Filename patterns this handler handles (exact match or glob pattern)
    filename_patterns: List[str] = field(default_factory=list)

    def handles_file(self, filename: str) -> bool:
        """Check if this handler handles the given filename."""
        import fnmatch

        for pattern in self.filename_patterns:
            if fnmatch.fnmatch(filename, pattern):
                return True
        return False

    def merge(self, src_path: Path, dst_path: Path) -> bool:
        """
        Merge source file into destination file.
        If dst_path does not exist, simply copy src_path to dst_path.
        Returns True on success, False on error.
        Subclasses should override this.
        """
        raise NotImplementedError


class SearchJsonMerger(SharedAssetMerger):
    """Merger for search.json files (JSON array concatenation with deduplication)."""

    def __init__(self):
        super().__init__(
            name="search_json",
            filename_patterns=["search.json"],
        )

    def merge(self, src_path: Path, dst_path: Path) -> bool:
        """
        Merge two search.json files by concatenating their arrays and deduplicating by objectID.
        If dst_path does not exist, simply copy src_path to dst_path.
        Returns True on success, False on error.
        """
        try:
            import json

            # Read source
            with open(src_path, "r", encoding="utf-8") as f:
                src_data = json.load(f)
            # If destination doesn't exist, copy
            if not dst_path.exists():
                shutil.copy2(src_path, dst_path)
                return True
            # Read destination
            with open(dst_path, "r", encoding="utf-8") as f:
                dst_data = json.load(f)
            # Ensure both are lists
            if not isinstance(src_data, list) or not isinstance(dst_data, list):
                logger.warning(
                    "search.json does not contain a JSON array, overwriting with source."
                )
                shutil.copy2(src_path, dst_path)
                return True
            # Merge: concatenate
            merged = src_data + dst_data
            # Deduplicate by objectID
            seen = {}
            unique = []
            for item in merged:
                obj_id = item.get("objectID")
                if obj_id not in seen:
                    seen[obj_id] = True
                    unique.append(item)
            # Write back
            with open(dst_path, "w", encoding="utf-8") as f:
                json.dump(unique, f, ensure_ascii=False, indent=2)
            logger.debug(f"Merged search.json from {src_path} into {dst_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to merge search.json {src_path} -> {dst_path}: {e}")
            return False


class SitemapXmlMerger(SharedAssetMerger):
    """Merger for sitemap.xml files (XML URL set union)."""

    def __init__(self):
        super().__init__(
            name="sitemap_xml",
            filename_patterns=["sitemap.xml"],
        )

    def merge(self, src_path: Path, dst_path: Path) -> bool:
        """
        Merge two sitemap.xml files by combining their URL entries.
        Deduplicates by URL (loc element content).
        If dst_path does not exist, simply copy src_path to dst_path.
        Returns True on success, False on error.
        """
        try:
            import xml.etree.ElementTree as ET

            # If destination doesn't exist, copy
            if not dst_path.exists():
                shutil.copy2(src_path, dst_path)
                return True

            # Parse both XML files
            src_tree = ET.parse(src_path)
            dst_tree = ET.parse(dst_path)

            src_root = src_tree.getroot()
            dst_root = dst_tree.getroot()

            # Extract namespace if present
            ns = {}
            if src_root.tag.startswith("{"):
                ns_uri = src_root.tag.split("}")[0][1:]
                ns["ns"] = ns_uri

            # Collect existing URLs from destination
            existing_urls = set()
            for url in (
                dst_root.findall(".//ns:url", ns) if ns else dst_root.findall(".//url")
            ):
                loc = url.find("ns:loc", ns) if ns else url.find("loc")
                if loc is not None and loc.text:
                    existing_urls.add(loc.text)

            # Collect URL elements from source that don't exist in destination
            url_elements_to_add = []
            for url in (
                src_root.findall(".//ns:url", ns) if ns else src_root.findall(".//url")
            ):
                loc = url.find("ns:loc", ns) if ns else url.find("loc")
                if loc is not None and loc.text:
                    if loc.text not in existing_urls:
                        url_elements_to_add.append(url)

            # Add new URL elements to destination
            for url_elem in url_elements_to_add:
                dst_root.append(url_elem)

            # Write merged result
            ET.indent(dst_tree, space="  ")
            dst_tree.write(dst_path, encoding="utf-8", xml_declaration=True)

            logger.debug(
                f"Merged sitemap.xml from {src_path} into {dst_path} (added {len(url_elements_to_add)} new URLs)"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to merge sitemap.xml {src_path} -> {dst_path}: {e}")
            return False


class RobotsTxtMerger(SharedAssetMerger):
    """
    Merger for robots.txt files.
    Since robots.txt is typically a simple configuration file, we use source precedence.
    This can be customized based on project needs.
    """

    def __init__(self):
        super().__init__(
            name="robots_txt",
            filename_patterns=["robots.txt"],
        )

    def merge(self, src_path: Path, dst_path: Path) -> bool:
        """
        For robots.txt, source takes precedence (overwrite destination).
        This is because robots.txt is typically a site-wide configuration.
        Returns True on success, False on error.
        """
        try:
            shutil.copy2(src_path, dst_path)
            logger.debug(
                f"Copied robots.txt from {src_path} to {dst_path} (source precedence)"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to copy robots.txt {src_path} -> {dst_path}: {e}")
            return False


class LlmsTxtMerger(SharedAssetMerger):
    """
    Merger for llms.txt files (markdown list of page links).
    Combines page entries from multiple targets and deduplicates by URL.
    """

    def __init__(self):
        super().__init__(
            name="llms_txt",
            filename_patterns=["llms.txt"],
        )

    def _parse_page_entries(self, content: str) -> List[Tuple[str, str]]:
        """
        Parse llms.txt content and extract page entries as (name, url) tuples.
        Returns list of (name, url) tuples found in markdown list items.
        """
        entries = []
        # Match markdown list items with links: - [name](url)
        pattern = re.compile(r"^\s*-\s*\[([^\]]+)\]\(([^)]+)\)\s*$")
        for line in content.splitlines():
            match = pattern.match(line)
            if match:
                name, url = match.groups()
                entries.append((name.strip(), url.strip()))
        return entries

    def _generate_content(
        self, entries: List[Tuple[str, str]], title: str = "Untitled"
    ) -> str:
        """
        Generate llms.txt content from page entries.
        Returns formatted markdown content.
        """
        lines = [f"# {title}", "", "## Pages", ""]
        for name, url in entries:
            lines.append(f"- [{name}]({url})")
        return "\n".join(lines) + "\n"

    def merge(self, src_path: Path, dst_path: Path) -> bool:
        """
        Merge two llms.txt files by combining their page entries.
        Deduplicates by URL (keeping the first occurrence).
        If dst_path does not exist, simply copy src_path to dst_path.
        Returns True on success, False on error.
        """
        try:
            # Read source
            with open(src_path, "r", encoding="utf-8") as f:
                src_content = f.read()

            # If destination doesn't exist, copy
            if not dst_path.exists():
                shutil.copy2(src_path, dst_path)
                return True

            # Read destination
            with open(dst_path, "r", encoding="utf-8") as f:
                dst_content = f.read()

            # Parse entries from both files
            src_entries = self._parse_page_entries(src_content)
            dst_entries = self._parse_page_entries(dst_content)

            # Extract title from destination (or use default)
            title = "Untitled"
            for line in dst_content.splitlines():
                if line.startswith("# "):
                    title = line[2:].strip()
                    break

            # Merge entries: start with destination, add source entries not in destination
            seen_urls = set()
            merged_entries = []

            # Add destination entries first (they take precedence)
            for name, url in dst_entries:
                if url not in seen_urls:
                    seen_urls.add(url)
                    merged_entries.append((name, url))

            # Add source entries that don't exist in destination
            for name, url in src_entries:
                if url not in seen_urls:
                    seen_urls.add(url)
                    merged_entries.append((name, url))

            # Generate merged content
            merged_content = self._generate_content(merged_entries, title)

            # Write back
            with open(dst_path, "w", encoding="utf-8") as f:
                f.write(merged_content)

            logger.debug(
                f"Merged llms.txt from {src_path} into {dst_path} (added {len(merged_entries) - len(dst_entries)} new entries)"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to merge llms.txt {src_path} -> {dst_path}: {e}")
            return False


# Registry of shared asset mergers
SHARED_ASSET_MERGERS: List[SharedAssetMerger] = [
    SearchJsonMerger(),
    SitemapXmlMerger(),
    RobotsTxtMerger(),
    LlmsTxtMerger(),
]


def get_merger_for_file(filename: str) -> Optional[SharedAssetMerger]:
    """Get the appropriate merger handler for a given filename."""
    for merger in SHARED_ASSET_MERGERS:
        if merger.handles_file(filename):
            return merger
    return None


def merge_shared_asset(src_path: Path, dst_path: Path) -> bool:
    """
    Merge a shared asset file from source to destination.
    Returns True if merged successfully, False if no merger found or error.
    """
    merger = get_merger_for_file(src_path.name)
    if merger is None:
        return False
    return merger.merge(src_path, dst_path)


def _is_target_specific_file(file_path: Path, target_name: str, base_dir: Path) -> bool:
    """
    Determine if a file is target-specific and should not be overwritten by other targets.

    Target-specific files include:
    - {target}/{target}.html (e.g., whitepaper/whitepaper.html)
    - {target}/index.html when target name matches folder (e.g., legal/index.html for legal target)
    - {target}.pdf at root level
    - Files under a directory matching the target name

    Returns True if the file is target-specific to the given target.
    """
    try:
        rel_path = file_path.relative_to(base_dir)
        parts = rel_path.parts

        # Check if any directory component matches target name
        for i, part in enumerate(parts[:-1]):  # Exclude filename
            if part == target_name:
                # File is under target directory
                filename = parts[-1]
                stem = filename.rsplit(".", 1)[0] if "." in filename else filename

                # index.html/index.pdf under target dir belongs to that target
                if filename in ("index.html", "index.pdf"):
                    return True
                # {target}.html or {target}.pdf belongs to that target
                if stem == target_name:
                    return True
                # Any file under target dir is target-specific
                return True

        # Check root-level files: {target}.html, {target}.pdf belong to that target
        if len(parts) == 1:
            filename = parts[0]
            stem = filename.rsplit(".", 1)[0] if "." in filename else filename
            if stem == target_name and filename.endswith((".html", ".pdf")):
                return True
    except ValueError:
        pass

    return False


def merge_dirs(src: Path, dst: Path, target_name: Optional[str] = None) -> bool:
    """
    Merge contents of src directory into dst directory using rsync-style algorithm.

    Core principle: The final _site result is a "union without duplicates" at the file content level.
    - All files from all sources are included (nothing should be missing)
    - Shared files like search.json are merged at the content level
    - Target-specific files (e.g., target/target.html) are protected from being overwritten by other targets
    - For index.qmd targets, the folder name IS the target name, so index.html/index.pdf
      from that target belongs to it (e.g., legal/index.html is the legal target's file)

    This function uses rsync for efficient file synchronization with the following behavior:
    - Files in src are copied to dst (overwriting if needed, except for target-specific files)
    - Files in dst that don't exist in src are preserved (union behavior)
    - Directory structure is preserved

    Args:
        src: Source directory to merge from
        dst: Destination directory to merge into
        target_name: Optional target name for determining file ownership

    Returns True on success, False on error.
    """
    try:
        # Ensure destination exists
        dst.mkdir(parents=True, exist_ok=True)

        # First, handle shared assets that need content-level merging
        # Get list of filenames handled by shared asset mergers
        shared_filenames = set()
        for merger in SHARED_ASSET_MERGERS:
            for pattern in merger.filename_patterns:
                # Add exact pattern (e.g., "search.json")
                if "*" not in pattern and "?" not in pattern:
                    shared_filenames.add(pattern)

        # Process shared assets
        for filename in shared_filenames:
            src_file = src / filename
            dst_file = dst / filename
            if src_file.exists():
                if not merge_shared_asset(src_file, dst_file):
                    # No merger found or error - fall back to copy
                    if not dst_file.exists():
                        shutil.copy2(src_file, dst_file)
                        logger.debug(
                            f"Copied shared file {src_file} to {dst_file} (no merger)"
                        )

        # Build exclude list for rsync (files handled by shared asset mergers)
        rsync_excludes = []
        for filename in shared_filenames:
            rsync_excludes.extend(["--exclude", filename])

        # Use rsync for the rest of the files
        # Flags:
        #   -a: archive mode (preserves permissions, timestamps, etc.)
        #   --ignore-existing: skip files that already exist in dst (union behavior)
        #   --exclude: skip files we handle specially

        rsync_cmd = (
            [
                "rsync",
                "-a",
                "--ignore-existing",  # Keep existing files in dst (union behavior)
            ]
            + rsync_excludes
            + [
                str(src) + "/",  # Trailing slash means "contents of src"
                str(dst) + "/",
            ]
        )

        result = subprocess.run(rsync_cmd, capture_output=True, text=True)
        if result.returncode not in (0, 23, 24):
            # 0 = success, 23 = some files vanished, 24 = vanished during transfer
            # These are acceptable for our use case
            logger.debug(f"rsync completed with code {result.returncode}")

        # Second pass: copy target-specific files from src, overwriting any existing files
        # (target-specific files have highest priority)
        if target_name:
            for src_file in src.rglob("*"):
                if src_file.is_file():
                    rel_path = src_file.relative_to(src)
                    dst_file = dst / rel_path

                    # Check if this is a target-specific file
                    if _is_target_specific_file(src_file, target_name, src):
                        # Copy target-specific file regardless of existence (overwrite)
                        dst_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src_file, dst_file)
                        logger.debug(
                            f"Copied target-specific file {src_file} -> {dst_file}"
                        )

        return True
    except Exception as e:
        logger.error(f"Failed to merge {src} into {dst}: {e}")
        return False


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
    logger.info(f"Rendering {target} in isolated docs directory {temp_docs}")

    try:
        # Build in the isolated docs directory
        func = BUILD_FUNCTIONS.get(target)
        if func is None:
            logger.error(f"Unknown target: {target}")
            return False

        # For isolated mode, we run the build in the temp_docs directory
        # The output will go to temp_docs/_site
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


def _cleanup_orphaned_caches(
    successful_targets: set, cache_base: Optional[Path] = None
) -> int:
    """
    Remove cache entries for targets that are no longer in the successful build set.

    This prevents accumulation of stale cache data when source files are deleted
    or target names change.

    Args:
        successful_targets: Set of target names that were successfully built
        cache_base: Base cache directory (defaults to _cached in parent of docs)

    Returns:
        Number of orphaned cache directories removed
    """
    if cache_base is None:
        cache_base = get_cache_base()

    if not cache_base.exists():
        return 0

    # Get all cached target directories
    cached_targets = {d.name for d in cache_base.iterdir() if d.is_dir()}

    # Find orphaned caches: in cache but not in successful targets
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
                f"Removed orphaned cache for target '{target_name}' at {cache_dir}"
            )
            removed_count += 1
        except Exception as e:
            logger.warning(f"Failed to remove orphaned cache for '{target_name}': {e}")

    logger.info(f"Cleaned up {removed_count} orphaned cache directorie(s).")
    return removed_count


def _sync_llms_files(source_dir: Path) -> None:
    """
    Sync LLMS files (llms.txt and *.llms.md) from source_dir to a sibling _llms directory.

    Only operates if the website config has llms-txt enabled.
    """
    config = get_website_config(DOCS_ROOT)
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


def build_targets(
    targets: List[str],
    output_dir: Optional[Path],
    sequence_mode: bool,
    max_jobs: int,
    single_command: bool,
    website: bool = False,
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

    # Execute global pre-build commands from build.yml (e.g., rumdl fmt)
    run_pre_build_commands(EXTERNAL_CONFIG, DOCS_ROOT)

    # Execute target-specific pre-build commands for each target
    for t in targets:
        run_pre_build_commands(EXTERNAL_CONFIG, DOCS_ROOT, target_name=t)

    # Capture the initial cache state before building starts
    capture_initial_cached_targets()

    results: Dict[str, bool] = {}

    # Clean _site directory before building to ensure no stale files remain
    final_site = output_dir if output_dir else (DOCS_ROOT / "_site")
    if final_site.exists():
        logger.info(f"Cleaning existing _site directory: {final_site}")
        try:
            shutil.rmtree(final_site)
            logger.info("Removed existing _site directory")
        except Exception as e:
            logger.error(f"Failed to remove existing _site directory: {e}")
            return False

    # In website mode with parallel execution:
    # Each target gets a complete copy of the docs folder in a temp directory
    # This ensures complete isolation of Quarto's project resources
    if website and (not sequence_mode) and (len(targets) > 1):
        logger.info(
            "Website mode: using isolated docs copies for parallel rendering..."
        )

        # Fixed absolute path that ensures path consistency for both CI and local
        base_temp = BUILD_TEMP_PATH

        if base_temp.exists():
            logger.info(f"Cleaning fixed temp dir: {base_temp}")
            shutil.rmtree(
                base_temp, ignore_errors=True
            )  # Even if you fail, ignore it and proceed

        base_temp.mkdir(parents=True, exist_ok=True)
        logger.info(f"Using fixed temp directory: {base_temp}")

        # Copy function (block infinite loop)
        def copy_for_target(t: str) -> Tuple[str, Path]:
            temp_docs = base_temp / t
            if temp_docs.exists():
                shutil.rmtree(temp_docs, ignore_errors=True)

            logger.info(f"Copying docs to {temp_docs} for {t}...")

            # Explicitly exclude target folder name + prevent circular references in symbolic links
            def _strict_ignore(src, names):
                ignored = set(ignore_quarto_artifacts()(src, names))
                if base_temp.name in names:
                    ignored.add(base_temp.name)
                # Exclude copy if symbolic link points to base_temp
                for name in list(names):
                    p = Path(src) / name
                    if p.is_symlink() and p.resolve() == base_temp.resolve():
                        ignored.add(name)
                return ignored

            shutil.copytree(DOCS_ROOT, temp_docs, ignore=_strict_ignore)
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
                        logger.error(f"Failed to copy docs for {target}: {e}")
                        # Clean up any already copied directories
                        for td in target_temp_dirs.values():
                            if td.exists():
                                shutil.rmtree(td, ignore_errors=True)
                        shutil.rmtree(base_temp, ignore_errors=True)
                        return False

            # Render all targets in parallel, each in its own isolated docs copy
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

            logger.info(
                f"Merging {len(succeeded)} successful targets into {final_output}..."
            )
            # Merge all targets - target-specific files are now protected by _is_target_specific_file
            # Order doesn't matter for target-specific files, but we still sort for consistency
            # Non-index targets first, then index target (for any shared files at root level)
            sorted_succeeded = sorted(succeeded, key=lambda x: (x == "index", x))
            # Iterate over a copy because we may modify results
            for target in sorted_succeeded:
                temp_docs = target_temp_dirs[target]
                temp_site = temp_docs / "_site"
                # If no site directory, copy target-specific artifacts directly from cache
                if not temp_site.exists():
                    cache_dir = get_cache_base() / target
                    if cache_dir.exists():
                        # Find the first hash subdirectory (most recent)
                        hash_dirs = list(cache_dir.iterdir())
                        if hash_dirs:
                            hash_dir = hash_dirs[0]
                            # Determine source path mapping
                            qmd_path = Path(TARGET_CONFIG[target]["qmd"])
                            src_parent = qmd_path.parent
                            src_stem = qmd_path.stem
                            # Copy all files from hash_dir (excluding 'site' directory)
                            for src_file in hash_dir.iterdir():
                                if src_file.name == "site":
                                    continue
                                if src_file.is_file():
                                    # Determine destination path preserving original docs structure
                                    if src_parent == Path("."):
                                        dest_parent = final_output
                                    else:
                                        dest_parent = final_output / src_parent
                                    # Determine destination filename: use source stem, keep extension
                                    dest_name = src_stem + src_file.suffix
                                    dest = dest_parent / dest_name
                                    dest.parent.mkdir(parents=True, exist_ok=True)
                                    shutil.copy2(src_file, dest)
                                    logger.debug(
                                        f"Copied cached artifact {src_file} -> {dest}"
                                    )
                if temp_site.exists():
                    if not merge_dirs(temp_site, final_output, target_name=target):
                        logger.warning(
                            f"Failed to merge {target} output into {final_output}"
                        )
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
                    logger.info(
                        f"Cleaning partial output directory {final_output} due to failures"
                    )
                    shutil.rmtree(final_output)
                return False

            if succeeded:
                successful_set = set(succeeded)
                _cleanup_orphaned_caches(successful_set)

            logger.info(f"All targets completed successfully: {list(results.keys())}")

            # Execute global post-render commands (e.g., generate hierarchical llms.txt)
            _sync_llms_files(final_output)
            run_post_render_commands(EXTERNAL_CONFIG, DOCS_ROOT)

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
    build_targets_set = set(targets)

    if use_parallel:
        logger.info(f"Running {len(targets)} targets in parallel (max_jobs={max_jobs})")
        with ThreadPoolExecutor(max_workers=max_jobs) as executor:
            futures = {
                executor.submit(
                    build_single_target,
                    t,
                    output_dir,
                    single_command,
                    website,
                    build_targets_set,
                ): t
                for t in targets
            }
            for future in as_completed(futures):
                target, success = future.result()
                results[target] = success
    else:
        # Sequential execution (either forced by --sequence, or single target)
        if len(targets) > 1:
            logger.info(
                f"Running {len(targets)} targets sequentially (--sequence mode)"
            )
        for target in targets:
            _, success = build_single_target(
                target, output_dir, single_command, website, build_targets_set
            )
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

    # Sync LLMS files (llms.txt and *.llms.md) into a sibling _llms directory
    if website:
        _sync_llms_files(source_dir=final_site if output_dir is None else output_dir)

    # Execute global post-render commands (e.g., generate hierarchical llms.txt)
    run_post_render_commands(EXTERNAL_CONFIG, DOCS_ROOT)

    return True


def run_pre_build_commands(
    external_config: Dict[str, Any],
    docs_root: Path,
    target_name: Optional[str] = None,
) -> None:
    PreBuildRunner.run(external_config, docs_root, target_name)


def run_post_render_commands(
    external_config: Dict[str, Any],
    docs_root: Path,
    target_name: Optional[str] = None,
) -> None:
    PostRenderRunner.run(external_config, docs_root, target_name)


def main() -> None:
    """Parse command line arguments and dispatch to build functions."""
    parser = argparse.ArgumentParser(
        description="SSCCS Documentation Build Manager",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Behavior:
  - Single target: formats are rendered in a single Quarto command by default.
  - Multiple targets: runs in PARALLEL by default (targets parallel, formats per target in single command)
    unless --parallel-formats is used.
  - Use --sequence/-s to force sequential execution across targets.
  - Use --parallel-formats to render each format in a separate Quarto command (parallel per format).
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
      **/*_files, **/*_output, **/*_extensions, **/*_cached, **/_site
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
  %(prog)s --parallel-formats whitepaper     # Render each format in separate Quarto command
  %(prog)s --config build.yml whitepaper   # Use external configuration file
  %(prog)s -c ./custom-config.yml whitepaper  # Specify custom config path
        """,
    )

    parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=None,
        help="Directory to place the final PDF (default: docs root)",
    )
    parser.add_argument(
        "--sequence",
        "-s",
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
        "--jobs",
        "-j",
        type=int,
        default=_default_jobs,
        help=f"Max number of parallel jobs (default: {_default_jobs} = estimated physical cores, only used in parallel mode)",
    )
    parser.add_argument(
        "--parallel-formats",
        action="store_true",
        help="Render each format in a separate Quarto command (parallel per format) instead of a single command",
    )
    parser.add_argument(
        "--website",
        action="store_true",
        help="Use Quarto website profile (adds --profile website to render commands)",
    )
    parser.add_argument(
        "--config",
        "-c",
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
        single_command=not args.parallel_formats,
        website=args.website,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
