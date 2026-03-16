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
from typing import List, Optional, Dict, Callable, Tuple, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# Special target configurations
SPECIAL_CONFIG: Dict[str, Dict[str, Any]] = {
    "whitepaper": {
        "output_dir": True,
        "c2pa": True,
        "copy_pdf": True,
    },
    "proposal": {
        "output_dir": True,
        "c2pa": True,
        "copy_pdf": True,
    },
    "readme": {
        "to": "gfm",
        "copy_to_root": True,
    },
    "manifesto": {
        "output_dir": True,
        "copy_html": True,
        "copy_md": True,
    },
}


def discover_qmd_targets(docs_root: Path) -> Dict[str, Dict[str, Any]]:
    """
    Scan docs_root for .qmd files and return target configurations.
    Excludes directories like _include, _extensions, _utils, _output, _regseal_files.
    """
    exclude_dirs = {"_include", "_extensions", "_utils", "_output", "_regseal_files"}
    targets = {}
    for qmd_path in docs_root.rglob("*.qmd"):
        # Skip files in excluded directories
        if any(part in exclude_dirs for part in qmd_path.parts):
            continue
        rel_path = qmd_path.relative_to(docs_root)
        # Target name is the stem of the file (extension removed), lowercased.
        # If duplicate stems exist, append parent directory name to disambiguate.
        target_name = rel_path.stem.lower()
        if target_name in targets:
            parent = rel_path.parent.name
            if parent:
                target_name = f"{target_name}_{parent}"
            else:
                suffix = 2
                while f"{target_name}_{suffix}" in targets:
                    suffix += 1
                target_name = f"{target_name}_{suffix}"
        # Default config
        config = {
            "qmd": str(rel_path),
            "output_dir": False,
            "c2pa": False,
            "copy_pdf": False,
            "copy_to_root": False,
            "to": None,
            "copy_html": False,
            "copy_md": False,
        }
        targets[target_name] = config
    return targets


def get_target_config(docs_root: Path) -> Dict[str, Dict[str, Any]]:
    """
    Return merged configuration: special config updates discovered defaults.
    """
    discovered = discover_qmd_targets(docs_root)
    # Merge special config (updates discovered entries)
    for target, config in SPECIAL_CONFIG.items():
        if target not in discovered:
            logger.error(f"Target '{target}' not found in discovered .qmd files")
            sys.exit(1)
        # Update discovered config with special config, preserving missing keys
        discovered[target].update(config)
        # Validate that qmd stem matches target name (case-insensitive)
        qmd_path = Path(discovered[target]["qmd"])
        if qmd_path.stem.lower() != target.lower():
            logger.error(
                f"Target name '{target}' does not match QMD file stem '{qmd_path.stem}' "
                f"(expected '{target}.qmd' or similar)"
            )
            sys.exit(1)
    return discovered


def build_generic(target: str, config: Dict[str, Any], output_dir: Optional[Path] = None) -> bool:
    """
    Generic build function that renders a .qmd file and performs optional post‑processing.
    """
    logger.info(f"Building {target}...")
    docs_root = Path(__file__).parent.absolute()
    os.chdir(docs_root)
    
    qmd_path = Path(config["qmd"])
    if not qmd_path.exists():
        logger.error(f"Qmd file not found: {qmd_path}")
        return False
    
    # Step 1: Quarto render
    quarto_cmd = ["quarto", "render", str(qmd_path)]
    if config.get("to"):
        quarto_cmd.extend(["--to", config["to"]])
    if not run_command(quarto_cmd):
        logger.error(f"Quarto render failed for {target}.")
        return False
    
    # Determine generated files
    stem = qmd_path.stem
    parent = qmd_path.parent
    generated_pdf = parent / f"{stem}.pdf"
    generated_html = parent / f"{stem}.html"
    generated_md = parent / f"{stem}.md"
    
    # Step 2: C2PA signing (if enabled)
    if config.get("c2pa") and generated_pdf.exists():
        manifest_path = parent / f"{stem}.c2pa_manifest.json"
        output_c2pa = parent / f"{stem}.c2pa"
        sign_cmd = [
            "python3", "_utils/sign_c2pa.py",
            "--pdf", str(generated_pdf),
            "--manifest", str(manifest_path),
            "--output", str(output_c2pa),
        ]
        if not run_command(sign_cmd):
            logger.warning(f"C2PA signing failed for {target}. Proceeding without signature.")
    
    # Step 3: Copy PDF to output_dir (if enabled)
    if config.get("copy_pdf") and generated_pdf.exists():
        dest_dir = Path(output_dir).absolute() if output_dir else docs_root
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_pdf = dest_dir / f"{stem}.pdf"
        try:
            shutil.move(str(generated_pdf), str(dest_pdf))
            logger.info(f"Copied PDF to {dest_pdf}")
        except Exception as e:
            logger.error(f"Failed to copy PDF: {e}")
            return False
    
    # Step 4: Copy to project root (if enabled)
    if config.get("copy_to_root") and generated_md.exists():
        root_path = docs_root.parent / "README.md"
        if root_path.is_symlink() and root_path.resolve() == generated_md.resolve():
            logger.info(f"Root README.md is a symlink; skipping copy.")
        else:
            try:
                shutil.copy2(str(generated_md), str(root_path))
                logger.info(f"Copied README.md to project root: {root_path}")
            except Exception as e:
                logger.error(f"Failed to copy README.md to root: {e}")
                return False
    
    # Step 5: Copy HTML/Markdown to output_dir (if enabled)
    if output_dir and (config.get("copy_html") or config.get("copy_md")):
        dest_dir = Path(output_dir).absolute()
        dest_dir.mkdir(parents=True, exist_ok=True)
        if config.get("copy_html") and generated_html.exists():
            dest_html = dest_dir / "index.html"
            try:
                shutil.copy2(str(generated_html), str(dest_html))
                logger.info(f"Copied index.html to {dest_html}")
            except Exception as e:
                logger.error(f"Failed to copy index.html: {e}")
                return False
        if config.get("copy_md") and generated_md.exists():
            dest_md = dest_dir / f"{stem}.md"
            try:
                shutil.copy2(str(generated_md), str(dest_md))
                logger.info(f"Copied {stem}.md to {dest_md}")
            except Exception as e:
                logger.error(f"Failed to copy {stem}.md: {e}")
                return False
    
    logger.info(f"{target} build completed successfully.")
    return True


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


DOCS_ROOT = Path(__file__).parent.absolute()
TARGET_CONFIG = get_target_config(DOCS_ROOT)



# Build function mapping per target (auto‑generated from TARGET_CONFIG)
BUILD_FUNCTIONS: Dict[str, Callable[..., bool]] = {}
for target, config in TARGET_CONFIG.items():
    # Create a closure that captures target and config
    def make_builder(tgt, cfg):
        def builder(output_dir: Optional[Path] = None) -> bool:
            return build_generic(tgt, cfg, output_dir)
        return builder
    BUILD_FUNCTIONS[target] = make_builder(target, config)

# list of targets that receive output_dir argument (those with output_dir=True in config)
OUTPUT_DIR_TARGETS = {t for t, cfg in TARGET_CONFIG.items() if cfg.get("output_dir")}


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
    succeeded = [t for t, s in results.items() if s]
    failed = [t for t, s in results.items() if not s]
    
    if failed:
        if succeeded:
            logger.info(f"Successful targets: {succeeded}")
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
        help="Build targets: any discovered .qmd file (e.g., whitepaper, proposal, readme, legal, guide, manifesto, pt, ...) or 'all' (default: all)",
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