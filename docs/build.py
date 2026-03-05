#!/usr/bin/env python3
"""
Top-level build manager for SSCCS documentation.

This script provides centralized functions for building various outputs
(whitepaper, legal docs, etc.) with consistent error handling and logging.
"""

import argparse
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


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


def build_whitepaper(output_dir: Optional[Path] = None) -> bool:
    """
    Build the SSCCS whitepaper.

    Steps:
        1. quarto render whitepaper/Whitepaper.qmd
        2. python3 _utils/sign_c2pa.py --pdf whitepaper/Whitepaper.pdf
               --manifest whitepaper/Whitepaper.c2pa_manifest.json
               --output whitepaper/Whitepaper.c2pa
        3. Copy whitepaper/Whitepaper.pdf to docs/ (or output_dir)

    Args:
        output_dir: Directory where the final PDF should be placed.
                   Defaults to the docs root.

    Returns:
        True if all steps succeeded, False otherwise.
    """
    logger.info("Building whitepaper...")

    # Ensure we are in the docs directory
    docs_root = Path(__file__).parent.absolute()
    os.chdir(docs_root)
    logger.info(f"Working directory: {docs_root}")

    # Step 1: Quarto render
    quarto_cmd = ["quarto", "render", "whitepaper/Whitepaper.qmd"]
    if not run_command(quarto_cmd):
        logger.error("Quarto render failed. Aborting whitepaper build.")
        return False

    # Step 2: C2PA signing
    sign_cmd = [
        "python3",
        "_utils/sign_c2pa.py",
        "--pdf", "whitepaper/Whitepaper.pdf",
        "--manifest", "whitepaper/Whitepaper.c2pa_manifest.json",
        "--output", "whitepaper/Whitepaper.c2pa",
    ]
    if not run_command(sign_cmd):
        logger.error("C2PA signing failed. Whitepaper PDF may be unsigned.")
        # Continue anyway? The PDF is still generated, but without C2PA.
        # We'll treat this as a warning, not a fatal error.
        logger.warning("Proceeding without C2PA signature.")

    # Step 3: Copy PDF to output location
    source_pdf = docs_root / "whitepaper" / "Whitepaper.pdf"
    if not source_pdf.exists():
        logger.error(f"Generated PDF not found at {source_pdf}")
        return False

    if output_dir is None:
        output_dir = docs_root
    else:
        output_dir = Path(output_dir).absolute()
        output_dir.mkdir(parents=True, exist_ok=True)

    dest_pdf = output_dir / "Whitepaper.pdf"
    try:
        shutil.move(source_pdf, dest_pdf)
        logger.info(f"Copied PDF to {dest_pdf}")
    except Exception as e:
        logger.error(f"Failed to copy PDF: {e}")
        return False

    logger.info("Whitepaper build completed successfully.")
    return True


def build_all(output_dir: Optional[Path] = None) -> bool:
    """
    Build all artifacts (whitepaper, README, legal).
    """
    logger.info("Building all artifacts...")
    success = True
    if not build_whitepaper(output_dir=output_dir):
        success = False
    if not build_readme():
        success = False
    if not build_legal():
        success = False
    if success:
        logger.info("All artifacts built successfully.")
    else:
        logger.error("One or more artifacts failed to build.")
    return success


def build_readme() -> bool:
    """
    Render docs/README.qmd to docs/README.md and copy to root README.md.
    """
    logger.info("Building README...")
    docs_root = Path(__file__).parent.absolute()
    os.chdir(docs_root)
    logger.info(f"Working directory: {docs_root}")

    # Quarto render to GFM
    quarto_cmd = ["quarto", "render", "README.qmd", "--to", "gfm"]
    if not run_command(quarto_cmd):
        logger.error("Quarto render failed for README.")
        return False
    logger.info("README built successfully.")

    # Copy to project root (parent directory)
    rendered_path = docs_root / "README.md"
    root_path = docs_root.parent / "README.md"
    # If root is a symlink pointing to the rendered file, no need to copy
    if root_path.is_symlink() and root_path.resolve() == rendered_path.resolve():
        logger.info(f"Root README.md is a symlink to {rendered_path}; skipping copy.")
    else:
        try:
            shutil.copy2(rendered_path, root_path)
            logger.info(f"Copied README.md to project root: {root_path}")
        except Exception as e:
            logger.error(f"Failed to copy README.md to root: {e}")
            return False

    return True


def build_legal() -> bool:
    """
    Render docs/legal/legal.qmd to docs/legal/legal.md (GitHub‑Flavored Markdown).
    """
    logger.info("Building legal document...")
    docs_root = Path(__file__).parent.absolute()
    os.chdir(docs_root)
    logger.info(f"Working directory: {docs_root}")

    # Quarto render to GFM
    quarto_cmd = ["quarto", "render", "legal/legal.qmd"]
    if not run_command(quarto_cmd):
        logger.error("Quarto render failed for legal document.")
        return False
    logger.info("Legal document built successfully.")
    return True


def main() -> None:
    """Parse command line arguments and dispatch to appropriate build function."""
    parser = argparse.ArgumentParser(
        description="SSCCS Documentation Build Manager"
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=None,
        help="Directory to place the final PDF (default: docs root)",
    )
    subparsers = parser.add_subparsers(dest="target", help="Build target")

    # Whitepaper subcommand
    whitepaper_parser = subparsers.add_parser(
        "whitepaper", help="Build the SSCCS whitepaper"
    )
    # README subcommand
    readme_parser = subparsers.add_parser(
        "readme", help="Render docs/README.qmd to docs/README.md"
    )
    # Legal subcommand
    legal_parser = subparsers.add_parser(
        "legal", help="Render docs/legal/legal.qmd to docs/legal/legal.md"
    )
    # All subcommand
    all_parser = subparsers.add_parser(
        "all", help="Build all artifacts (default behavior)"
    )

    # Set default target to 'all' if no arguments
    parser.set_defaults(target="all")

    args = parser.parse_args()

    if args.target == "whitepaper":
        success = build_whitepaper(output_dir=args.output_dir)
        sys.exit(0 if success else 1)
    elif args.target == "readme":
        success = build_readme()
        sys.exit(0 if success else 1)
    elif args.target == "legal":
        success = build_legal()
        sys.exit(0 if success else 1)
    elif args.target == "all":
        success = build_all(output_dir=args.output_dir)
        sys.exit(0 if success else 1)
    else:
        # Should not happen because we set default target, but keep for safety
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()