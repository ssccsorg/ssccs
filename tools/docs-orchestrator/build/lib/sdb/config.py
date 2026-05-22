from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

BUILD_TEMP_DIR = "_docsbuild"
BUILD_CACHE_DIR = "_cached"
JUPYTER_CACHE_DIR = "_jupyter_cache"
QUARTO_CONFIG_FILES = ["_quarto.yml", "_quarto-website.yml"]


def get_docs_root() -> Path:
    """Return the current working directory as the documentation root."""
    return Path.cwd()


# ---------------------------------------------------------------------------
# BuildContext -- immutable runtime state (replaces global mutable variables)
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
# ConfigManager -- configuration loading, target discovery, gitignore matching
# ---------------------------------------------------------------------------


DEFAULT_EXCLUDE_PATTERNS: List[str] = []


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

    @staticmethod
    def get_cache_base(cache_parent: Path) -> Path:
        """Return the base cache directory under ``cache_parent``.

        Note: ``cache_parent`` should be the PROJECT root (parent of docs/),
        not the docs/ directory itself.  In the original build.py this was
        always ``DOCS_PARENT`` (the hardcoded project root).
        """
        return cache_parent / BUILD_CACHE_DIR

    @staticmethod
    def get_cache_dir(qmd_path: Path) -> Path:
        """Return per-QMD cache directory (``{stem}_cached/`` next to the QMD)."""
        return qmd_path.parent / f"{qmd_path.stem}_cached"

    @staticmethod
    def get_cache_dir_for_target(qmd_path: Path, target_name: str) -> Path:
        """Return per-target cache directory (``{target_name}_cached/`` next to the QMD)."""
        return qmd_path.parent / f"{target_name}_cached"

    @staticmethod
    def get_moved_path(
        qmd_path: Path,
        fmt: str,
        config: Dict[str, Any],
        output_dir: Optional[Path],
        docs_root: Path,
        source_path: Path,
    ) -> Optional[Path]:
        """Compute the final destination path when copy flags are enabled."""
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
    def get_output_path(file_path: Path, fmt: str) -> Optional[Path]:
        """Resolve the rendered output path for a QMD and format using ``quarto inspect``."""
        data = ConfigManager.inspect(file_path)
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
    @lru_cache(maxsize=128)
    def inspect(file_path: Path) -> Optional[Dict[str, Any]]:
        """Run ``quarto inspect`` on a QMD file and return structured metadata."""
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
    def find_existing_output(
        qmd_path: Path,
        fmt: str,
        config: Optional[Dict[str, Any]],
        output_dir: Optional[Path],
        docs_root: Path,
    ) -> Optional[Path]:
        """Locate an already-rendered output file, checking both its primary
        location and any moved destination defined by copy flags."""
        primary = ConfigManager.get_output_path(qmd_path, fmt)
        if primary is None:
            return None
        candidates = [primary]
        if config:
            moved = ConfigManager.get_moved_path(
                qmd_path, fmt, config, output_dir, docs_root, primary
            )
            if moved and moved != primary:
                candidates.append(moved)
        for cand in candidates:
            if cand.exists():
                return cand
        return None

    @staticmethod
    def format_to_extension(fmt: str) -> str:
        """Map a Quarto format name to its file extension."""
        mapping = {"pdf": "pdf", "beamer": "pdf", "html": "html", "gfm": "md", "markdown": "md"}
        return mapping.get(fmt, fmt)


# ---------------------------------------------------------------------------
# CleanupManager -- Quarto artifact patterns and cleanup
# ---------------------------------------------------------------------------


class CleanupManager:
    """Manages Quarto artifact patterns and cleanup operations."""

    IGNORING_ARTIFACT_PATTERNS = [
        "**/__pycache__", "**/*.pyc", "**/*.pyd", "**/*.log",
        "**/*_output", "**/*_extensions", "**/*_cached", "**/*_files",
        "**/*_libs", "**/_llms", "**/_site", "**/_docsbuild",
        "**/.jupyter_cache",
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
