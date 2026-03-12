#!/usr/bin/env python3
"""
Top-level build manager for SSCCS documentation.

Behavior:
  - Single target: runs normally
  - Multiple targets: runs in PARALLEL by default
  - Use --sequence/-s to force sequential execution

Usage:
  ./build.py whitepaper                     # Single target
  ./build.py whitepaper readme              # Multiple -> parallel by default
  ./build.py whitepaper,readme,legal        # Multiple -> parallel by default
  ./build.py -s whitepaper proposal readme  # Force sequential execution
  ./build.py -j 2 whitepaper,proposal       # Parallel with 2 jobs
  ./build.py -o ./dist whitepaper proposal  # With output directory
"""

import argparse
import logging
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Optional, Dict, Callable, Tuple

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
    """Build the SSCCS whitepaper with C2PA signing."""
    logger.info("Building whitepaper...")
    docs_root = Path(__file__).parent.absolute()
    os.chdir(docs_root)

    # Step 1: Quarto render
    quarto_cmd = ["quarto", "render", "whitepaper/whitepaper.qmd"]
    if not run_command(quarto_cmd):
        logger.error("Quarto render failed. Aborting whitepaper build.")
        return False

    # Step 2: C2PA signing (non-fatal)
    sign_cmd = [
        "python3", "_utils/sign_c2pa.py",
        "--pdf", "whitepaper/whitepaper.pdf",
        "--manifest", "whitepaper/whitepaper.c2pa_manifest.json",
        "--output", "whitepaper/whitepaper.c2pa",
    ]
    if not run_command(sign_cmd):
        logger.warning("C2PA signing failed. Proceeding without signature.")

    # Step 3: Copy PDF
    source_pdf = docs_root / "whitepaper" / "whitepaper.pdf"
    if not source_pdf.exists():
        logger.error(f"Generated PDF not found at {source_pdf}")
        return False

    dest_dir = Path(output_dir).absolute() if output_dir else docs_root
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_pdf = dest_dir / "whitepaper.pdf"

    try:
        shutil.move(source_pdf, dest_pdf)
        logger.info(f"Copied PDF to {dest_pdf}")
    except Exception as e:
        logger.error(f"Failed to copy PDF: {e}")
        return False

    logger.info("Whitepaper build completed successfully.")
    return True


def build_proposal(output_dir: Optional[Path] = None) -> bool:
    """Build the SSCCS proposal with C2PA signing."""
    logger.info("Building proposal...")
    docs_root = Path(__file__).parent.absolute()
    os.chdir(docs_root)

    # Step 1: Quarto render
    quarto_cmd = ["quarto", "render", "proposal/proposal.qmd"]
    if not run_command(quarto_cmd):
        logger.error("Quarto render failed. Aborting proposal build.")
        return False

    # Step 2: C2PA signing (non-fatal)
    sign_cmd = [
        "python3", "_utils/sign_c2pa.py",
        "--pdf", "proposal/proposal.pdf",
        "--manifest", "proposal/proposal.c2pa_manifest.json",
        "--output", "proposal/proposal.c2pa",
    ]
    if not run_command(sign_cmd):
        logger.warning("C2PA signing failed. Proceeding without signature.")

    # Step 3: Copy PDF
    source_pdf = docs_root / "proposal" / "proposal.pdf"
    if not source_pdf.exists():
        logger.error(f"Generated PDF not found at {source_pdf}")
        return False

    dest_dir = Path(output_dir).absolute() if output_dir else docs_root
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_pdf = dest_dir / "proposal.pdf"

    try:
        shutil.move(source_pdf, dest_pdf)
        logger.info(f"Copied PDF to {dest_pdf}")
    except Exception as e:
        logger.error(f"Failed to copy PDF: {e}")
        return False

    logger.info("Proposal build completed successfully.")
    return True


def build_readme() -> bool:
    """Render docs/README.qmd to docs/README.md and copy to root."""
    logger.info("Building README...")
    docs_root = Path(__file__).parent.absolute()
    os.chdir(docs_root)

    quarto_cmd = ["quarto", "render", "README.qmd", "--to", "gfm"]
    if not run_command(quarto_cmd):
        logger.error("Quarto render failed for README.")
        return False

    rendered_path = docs_root / "README.md"
    root_path = docs_root.parent / "README.md"

    if root_path.is_symlink() and root_path.resolve() == rendered_path.resolve():
        logger.info(f"Root README.md is a symlink; skipping copy.")
    else:
        try:
            shutil.copy2(rendered_path, root_path)
            logger.info(f"Copied README.md to project root: {root_path}")
        except Exception as e:
            logger.error(f"Failed to copy README.md to root: {e}")
            return False

    logger.info("README built successfully.")
    return True


def build_legal() -> bool:
    """Render docs/legal/legal.qmd to docs/legal/legal.md."""
    logger.info("Building legal document...")
    docs_root = Path(__file__).parent.absolute()
    os.chdir(docs_root)

    quarto_cmd = ["quarto", "render", "legal/legal.qmd"]
    if not run_command(quarto_cmd):
        logger.error("Quarto render failed for legal document.")
        return False

    logger.info("Legal document built successfully.")
    return True


def build_guide() -> bool:
    """Render docs/GUIDE.qmd to docs/GUIDE.md."""
    logger.info("Building guide...")
    docs_root = Path(__file__).parent.absolute()
    os.chdir(docs_root)

    quarto_cmd = ["quarto", "render", "GUIDE.qmd"]
    if not run_command(quarto_cmd):
        logger.error("Quarto render failed for guide.")
        return False

    logger.info("Guide built successfully.")
    return True


def build_manifesto(output_dir: Optional[Path] = None) -> bool:
    """Render MANIFESTO.qmd to HTML (index.html) and Markdown (MANIFESTO.md)."""
    logger.info("Building manifesto...")
    docs_root = Path(__file__).parent.absolute()
    os.chdir(docs_root)

    # Quarto render to HTML
    quarto_cmd = ["quarto", "render", "MANIFESTO.qmd"]
    if not run_command(quarto_cmd):
        logger.error("Quarto render failed for manifesto.")
        return False

    # Optionally copy HTML to output_dir if provided
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        source_html = docs_root / "index.html"
        dest_html = output_dir / "index.html"
        try:
            shutil.copy2(source_html, dest_html)
            logger.info(f"Copied index.html to {dest_html}")
        except Exception as e:
            logger.error(f"Failed to copy index.html: {e}")
            return False
        source_md = docs_root / "MANIFESTO.md"
        dest_md = output_dir / "MANIFESTO.md"
        try:
            shutil.copy2(source_md, dest_md)
            logger.info(f"Copied MANIFESTO.md to {dest_md}")
        except Exception as e:
            logger.error(f"Failed to copy MANIFESTO.md: {e}")
            return False

    logger.info("Manifesto build completed successfully.")
    return True


# Build function mapping per target
BUILD_FUNCTIONS: Dict[str, Callable[..., bool]] = {
    "whitepaper": build_whitepaper,
    "proposal": build_proposal,
    "readme": build_readme,
    "legal": build_legal,
    "guide": build_guide,
    "manifesto": build_manifesto,
}

# list of targets that receive output_dir argument
OUTPUT_DIR_TARGETS = {"whitepaper", "proposal", "manifesto"}


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
        logger.error(f"Unknown target(s): {invalid}. Available: {list(BUILD_FUNCTIONS.keys())}")
        sys.exit(1)
    return targets


def build_single_target(target: str, output_dir: Optional[Path]) -> Tuple[str, bool]:
    """Wrapper to run a single build function and return (target_name, success)."""
    logger.info(f"Starting build: {target}")
    func = BUILD_FUNCTIONS[target]
    try:
        if target in OUTPUT_DIR_TARGETS:
            success = func(output_dir=output_dir)
        else:
            success = func()
        logger.info(f"Finished build: {target} -> {'✓' if success else '✗'}")
        return target, success
    except Exception as e:
        logger.error(f"Exception while building {target}: {e}")
        return target, False


def build_targets(
    targets: List[str],
    output_dir: Optional[Path],
    sequence_mode: bool,
    max_jobs: int
) -> bool:
    """
    Build multiple targets.
    
    Behavior:
      -If sequence_mode=True: run sequentially regardless of target count
      -If sequence_mode=False and len(targets) > 1: run in parallel (default)
      - If sequence_mode=False and len(targets) == 1: run normally (no threading overhead)
    """
    if not targets:
        logger.info("No targets specified. Nothing to build.")
        return True

    results: Dict[str, bool] = {}

    # Decide execution mode: parallel only if NOT sequence_mode AND multiple targets
    use_parallel = (not sequence_mode) and (len(targets) > 1)

    if use_parallel:
        logger.info(f"Running {len(targets)} targets in parallel (max_jobs={max_jobs})")
        with ThreadPoolExecutor(max_workers=max_jobs) as executor:
            futures = {
                executor.submit(build_single_target, t, output_dir): t
                for t in targets
            }
            for future in as_completed(futures):
                target, success = future.result()
                results[target] = success
    else:
        # Sequential execution (either forced by --sequence, or single target)
        if len(targets) > 1:
            logger.info(f"Running {len(targets)} targets sequentially (--sequence mode)")
        for target in targets:
            _, success = build_single_target(target, output_dir)
            results[target] = success

    # Summary of results
    failed = [t for t, s in results.items() if not s]
    if failed:
        logger.error(f"Failed targets: {failed}")
        return False

    logger.info(f"All targets completed successfully: {list(results.keys())}")
    return True


def main() -> None:
    """Parse command line arguments and dispatch to build functions."""
    parser = argparse.ArgumentParser(
        description="SSCCS Documentation Build Manager",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Behavior:
  - Single target: runs normally
  - Multiple targets: runs in PARALLEL by default
  - Use --sequence/-s to force sequential execution

Examples:
  %(prog)s whitepaper                     # Single target
  %(prog)s whitepaper readme              # Multiple -> parallel by default
  %(prog)s whitepaper,readme,legal        # Multiple -> parallel by default
  %(prog)s -s whitepaper proposal readme  # Force sequential execution
  %(prog)s -j 2 whitepaper,proposal       # Parallel with 2 jobs
  %(prog)s -o ./dist whitepaper proposal  # Specify output directory
        """
    )

    parser.add_argument(
        "--output-dir", "-o",
        type=Path,
        default=None,
        help="Directory to place the final PDF (default: docs root)",
    )
    parser.add_argument(
        "--sequence", "-s",
        action="store_true",
        help="Force sequential execution even with multiple targets",
    )
    parser.add_argument(
        "--jobs", "-j",
        type=int,
        default=4,
        help="Max number of parallel jobs (default: 4, only used in parallel mode)",
    )
    parser.add_argument(
        "targets",
        nargs="*",
        default=["all"],
        help="Build targets: whitepaper, proposal, readme, legal, guide, manifesto, all (default: all)",
    )

    args = parser.parse_args()

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
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()