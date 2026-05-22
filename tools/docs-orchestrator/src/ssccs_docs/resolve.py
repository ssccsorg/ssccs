"""
SDBS resolve — path/link/include resolver (WIP extraction from resolve.py).

Fixes relative paths in QMD/MD files, resolves includes, and
repairs broken links across the documentation tree.
"""

import logging

logger = logging.getLogger(__name__)


def resolve_all(
    docs_root: str,
    check_only: bool = False,
) -> bool:
    """Resolve all paths, links, and includes. (stub)"""
    return True
