from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import ConfigManager

logger = logging.getLogger(__name__)


@dataclass
class LinkedArtifactHandler:
    """Base class for linked artifact handlers."""

    name: str
    extensions: Dict[str, str] = field(default_factory=dict)
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
        from sdb.utils.c2pa import sign_pdf
        if sign_pdf(
            pdf_path=primary_path,
            manifest_path=manifest_path,
            output_path=output_c2pa,
        ):
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
    target_name: str,
    hash_str: str,
    fmt: str,
    cache_parent: Path,
    linked_ext: Optional[str] = None,
) -> Path:
    """
    Return the path to a cached artifact file for the given target, hash,
    and format.

    Parameters
    ----------
    cache_parent
        The project root directory (parent of ``docs/``), under which the
        ``_cached/`` directory lives.  This mirrors ``PROJECT_ROOT`` in
        :mod:`sdb.build`.
    """
    ext = linked_ext if linked_ext else ConfigManager.format_to_extension(fmt)
    return ConfigManager.get_cache_base(cache_parent) / target_name / hash_str / f"{target_name}.{ext}"


def find_cached_artifact(
    target_name: str,
    hash_str: str,
    fmt: str,
    cache_parent: Path,
    linked_ext: Optional[str] = None,
) -> Optional[Path]:
    """
    Return the cached artifact path if it exists, otherwise None.
    If linked_ext is provided, looks for the linked artifact file.

    Parameters
    ----------
    cache_parent
        The project root directory (parent of ``docs/``), under which the
        ``_cached/`` directory lives.
    """
    path = get_cached_artifact_path(target_name, hash_str, fmt, cache_parent, linked_ext=linked_ext)
    if path.exists():
        return path
    return None
