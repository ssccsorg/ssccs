"""
Standalone utility to determine the main QMD file path for a Quarto project.

Derived from docs/_utils/qmd_path.py.
"""

import os
import logging

logger = logging.getLogger(__name__)


def resolve_qmd_path(qmd_path: str | None = None) -> str:
    """
    Determine the main QMD file path.

    Resolution order:
    1. If *qmd_path* is given and the file exists, use it.
    2. Otherwise check the ``QUARTO_PROJECT_INPUT_FILE`` environment variable.
    3. Fall back to the first ``.qmd`` file in the current directory.

    Returns the path as a string.

    Raises
    ------
    FileNotFoundError
        When no valid QMD file can be determined.
    """
    if qmd_path:
        if not os.path.isfile(qmd_path):
            raise FileNotFoundError(f"Input file '{qmd_path}' not found.")
        return qmd_path

    qmd_path = os.environ.get("QUARTO_PROJECT_INPUT_FILE")
    if qmd_path and os.path.exists(qmd_path):
        return qmd_path

    qmd_files = [f for f in os.listdir(".") if f.endswith(".qmd")]
    if qmd_files:
        return qmd_files[0]

    raise FileNotFoundError(
        "Cannot determine QMD file. Please specify a path or ensure a "
        ".qmd file exists in the current directory."
    )
