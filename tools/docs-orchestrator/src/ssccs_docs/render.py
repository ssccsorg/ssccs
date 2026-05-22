from __future__ import annotations

import logging
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


# Formats that are considered non-deterministic (cached based on QMD hash only)
NON_DETERMINISTIC_FORMATS = {"pdf", "beamer", "html", "gfm"}


# ---------------------------------------------------------------------------
# CommandRunner - subprocess execution
# ---------------------------------------------------------------------------


class CommandRunner:
    """Subprocess execution with logging."""

    @staticmethod
    def run(cmd: List[str], cwd: Optional[Path] = None) -> bool:
        logger.info(f"Running: {' '.join(cmd)}")
        try:
            result = subprocess.run(
                cmd, cwd=cwd, capture_output=True, text=True, check=False
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


# ---------------------------------------------------------------------------
# FormatRenderer - render formats (single command or parallel per format)
# ---------------------------------------------------------------------------


class FormatRenderer:
    """Renders formats using Quarto (single command or parallel per format)."""

    @staticmethod
    def _parallel(
        qmd_path,
        formats,
        format_output_paths,
        docs_root,
        website=False,
        target_name=None,
    ):
        def render_one(fmt):
            lock = _lock_for_quarto_file(qmd_path)
            with lock:
                cmd = ["quarto", "render", str(qmd_path), "--to", fmt]
                if website:
                    cmd.extend(["--profile", "website"])
                if not CommandRunner.run(cmd, cwd=docs_root):
                    logger.error(
                        f"Quarto render failed for {qmd_path.name} (format {fmt})."
                    )
                    return False
                if fmt in NON_DETERMINISTIC_FORMATS:
                    out = format_output_paths[fmt]
                    if out.exists():
                        from .build import update_format_cache

                        update_format_cache(
                            qmd_path, fmt, out, docs_root, target_name=target_name
                        )
                return True

        with ThreadPoolExecutor(max_workers=len(formats)) as executor:
            futures = {executor.submit(render_one, f): f for f in formats}
            return (
                sum(1 for fu in as_completed(futures) if fu.result())
                == len(formats)
            )

    @staticmethod
    def _single(
        qmd_path,
        formats,
        format_output_paths,
        docs_root,
        website=False,
        target_name=None,
    ):
        lock = _lock_for_quarto_file(qmd_path)
        with lock:
            fmt_str = ",".join(formats)
            cmd = ["quarto", "render", str(qmd_path), "--to", fmt_str]
            if website:
                cmd.extend(["--profile", "website"])
            if not CommandRunner.run(cmd, cwd=docs_root):
                logger.error(
                    f"Quarto render failed for {qmd_path.name} (formats {fmt_str})."
                )
                return False
            for fmt in formats:
                if fmt in NON_DETERMINISTIC_FORMATS:
                    out = format_output_paths[fmt]
                    if out.exists():
                        from .build import update_format_cache

                        update_format_cache(
                            qmd_path, fmt, out, docs_root, target_name=target_name
                        )
            return True

    @staticmethod
    def render(
        qmd_path,
        formats,
        format_output_paths,
        docs_root,
        single_command,
        website=False,
        target_name=None,
    ):
        if single_command:
            return FormatRenderer._single(
                qmd_path,
                formats,
                format_output_paths,
                docs_root,
                website,
                target_name,
            )
        return FormatRenderer._parallel(
            qmd_path,
            formats,
            format_output_paths,
            docs_root,
            website,
            target_name,
        )


# ---------------------------------------------------------------------------
# Per-QMD locks to prevent concurrent Quarto renders on the same source file
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Standalone function aliases
# ---------------------------------------------------------------------------


def _render_formats_parallel(
    qmd_path, formats, format_output_paths, docs_root, website=False, target_name=None
):
    return FormatRenderer._parallel(
        qmd_path, formats, format_output_paths, docs_root, website, target_name
    )


def _render_formats_single(
    qmd_path, formats, format_output_paths, docs_root, website=False, target_name=None
):
    return FormatRenderer._single(
        qmd_path, formats, format_output_paths, docs_root, website, target_name
    )


def _render_formats(
    qmd_path,
    formats,
    format_output_paths,
    docs_root,
    single_command,
    website=False,
    target_name=None,
):
    return FormatRenderer.render(
        qmd_path,
        formats,
        format_output_paths,
        docs_root,
        single_command,
        website,
        target_name,
    )
