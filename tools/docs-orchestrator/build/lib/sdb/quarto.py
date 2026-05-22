from __future__ import annotations

import json
import logging
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


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
    def get_moved_path(
        qmd_path: Path, fmt: str, config: Optional[Dict[str, Any]],
        output_dir: Optional[Path], docs_root: Path, source_path: Path,
    ) -> Optional[Path]:
        stem = qmd_path.stem
        if fmt in ("pdf", "beamer") and config and config.get("copy_pdf"):
            dest_dir = output_dir.absolute() if output_dir else docs_root
            return dest_dir / f"{stem}.pdf"
        if fmt == "html" and config and config.get("copy_html"):
            dest_dir = output_dir.absolute() if output_dir else docs_root
            return dest_dir / "index.html"
        if fmt in ("gfm", "markdown") and config and config.get("copy_md"):
            dest_dir = output_dir.absolute() if output_dir else docs_root
            return dest_dir / f"{stem}.md"
        if fmt == "gfm" and config and config.get("copy_to_root"):
            return docs_root.parent / "README.md"
        return None

    @staticmethod
    def find_existing_output(
        qmd_path: Path, fmt: str, config: Optional[Dict[str, Any]],
        output_dir: Optional[Path], docs_root: Path,
    ) -> Optional[Path]:
        primary = QuartoInspector.get_output_path(qmd_path, fmt)
        if primary is None:
            return None
        candidates = [primary]
        if config:
            moved = QuartoInspector.get_moved_path(
                qmd_path, fmt, config, output_dir, docs_root, primary,
            )
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
    def get_cache_base(docs_root: Path) -> Path:
        return docs_root.parent / "_cached"

    @staticmethod
    def format_to_extension(fmt: str) -> str:
        mapping = {"pdf": "pdf", "beamer": "pdf", "html": "html", "gfm": "md", "markdown": "md"}
        return mapping.get(fmt, fmt)
