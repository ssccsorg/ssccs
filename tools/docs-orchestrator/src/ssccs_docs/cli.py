"""
SDBS CLI — entry point for all ssccs-docs commands.

Subcommands:
  init     Scaffold a new docs directory with default templates.
  build    Build one or more Quarto targets.
  check    Validate links, citations, and cross-references.
  resolve  Resolve relative paths, includes, and links.
"""

import argparse
import logging
import sys
from pathlib import Path

from ssccs_docs import __version__

from . import init as init_module


logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    stream=sys.stderr,
)


def _add_global_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="ssccs-docs",
        description="Scale-out Documentation Build System (SDBS)",
    )
    _add_global_args(parser)

    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- init ---
    init_parser = subparsers.add_parser(
        "init",
        help="Scaffold a docs directory with default templates",
        description="Create a complete docs directory skeleton with Quarto project config, "
        "format options, citation style, and a starter landing page.",
    )
    init_parser.add_argument(
        "path",
        type=Path,
        nargs="?",
        default=Path("docs"),
        help="Target directory (default: docs/)",
    )
    init_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files",
    )

    # --- build ---
    build_parser = subparsers.add_parser(
        "build",
        help="Build Quarto document targets",
        description="Orchestrate Quarto rendering for one or more document targets. "
        "Supports parallel execution, website mode, and intelligent caching.",
        epilog=(
            "Examples:\n"
            "  ssccs-docs build docs whitepaper\n"
            "  ssccs-docs build docs whitepaper proposal --website -j 4\n"
            "  ssccs-docs build docs snapshot\n"
            "  ssccs-docs build docs clean"
        ),
    )
    build_parser.add_argument(
        "docs_root",
        type=Path,
        nargs="?",
        default=Path("."),
        help="Path to the docs directory (default: current directory)",
    )
    build_parser.add_argument(
        "targets",
        nargs="*",
        default=["all"],
        help="Build targets (default: all)",
    )
    build_parser.add_argument(
        "--output-dir", "-o", type=Path, default=None,
        help="Directory to place final outputs",
    )
    build_parser.add_argument(
        "--website", action="store_true",
        help="Use Quarto website profile (isolated parallel rendering)",
    )
    build_parser.add_argument(
        "--sequence", "-s", action="store_true",
        help="Force sequential execution",
    )
    build_parser.add_argument(
        "--jobs", "-j", type=int, default=None,
        help="Max parallel jobs (default: physical core count)",
    )
    build_parser.add_argument(
        "--parallel-formats", action="store_true",
        help="Render each format in separate Quarto commands",
    )
    build_parser.add_argument(
        "--config", "-c", type=Path, default=None,
        help="Path to external YAML configuration file (default: build.yml in docs root)",
    )

    # --- check ---
    check_parser = subparsers.add_parser(
        "check",
        help="Validate documentation integrity",
        description="Check links, citations, cross-references, and YAML paths "
        "in a docs directory.",
    )
    check_parser.add_argument(
        "docs_root",
        type=Path,
        nargs="?",
        default=Path("."),
        help="Path to the docs directory (default: current directory)",
    )
    check_parser.add_argument(
        "--validate-only", action="store_true",
        help="Report issues without modifying files",
    )
    check_parser.add_argument(
        "--cleanup-uncited", action="store_true",
        help="Remove uncited bibliography entries",
    )

    # --- resolve ---
    resolve_parser = subparsers.add_parser(
        "resolve",
        help="Resolve relative paths and includes",
        description="Fix relative paths in QMD/MD files, update includes, "
        "and resolve broken links.",
    )
    resolve_parser.add_argument(
        "docs_root",
        type=Path,
        nargs="?",
        default=Path("."),
        help="Path to the docs directory (default: current directory)",
    )
    resolve_parser.add_argument(
        "--check-only", action="store_true",
        help="Only report issues, do not modify files",
    )

    args = parser.parse_args(argv)

    if args.command == "init":
        success = init_module.scaffold(args.path, force=args.force)
        sys.exit(0 if success else 1)

    elif args.command == "build":
        sys.exit(0)
        # TODO: delegate to build.build_targets(docs_root=args.docs_root, ...)

    elif args.command == "check":
        sys.exit(0)
        # TODO: delegate to check.run_check(docs_root=args.docs_root, ...)

    elif args.command == "resolve":
        sys.exit(0)
        # TODO: delegate to resolve.resolve_all(docs_root=args.docs_root, ...)


if __name__ == "__main__":
    main()
