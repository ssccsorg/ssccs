"""
SDBS init — scaffold a new docs directory with templates.

Usage:
    sdb init [path] [--force] [--template NAME]
"""

import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

TEMPLATES_PACKAGE = Path(__file__).parent / "templates"

# Default template map (minimal Quarto system settings, project-specific
# values are commented out with # TODO guidance).
DEFAULT_TEMPLATE_MAP: dict[str, str] = {
    "build.yml": "build.yml",
    "_quarto.yml": "_quarto.yml",
    "_quarto-website.yml": "_quarto-website.yml",
    "_quarto_pre-render.py": "_quarto_pre-render.py",
    "_include/author.yml": "_include/author.yml",
    "_include/format.html.yml": "_include/format.html.yml",
    "_include/format.pdf.yml": "_include/format.pdf.yml",
    "_include/format.beamer.yml": "_include/format.beamer.yml",
    "_include/ieee.csl": "_include/ieee.csl",
    "index.qmd": "index.qmd",
    ".gitignore": "_gitignore",
}

# SSCCS-specific template map (adds SSCCS-specific files on top of default)
SSCCS_TEMPLATE_MAP: dict[str, str] = {
    **DEFAULT_TEMPLATE_MAP,
    "_include/_graphviz.py": "_include/_graphviz.py",
    "_include/_title_meta_items.qmd": "_include/_title_meta_items.qmd",
}


def _copy_template(src: Path, dst: Path, force: bool) -> bool:
    """Copy a single template file. Returns True if written, False if skipped."""
    if dst.exists() and not force:
        logger.info(f"  skip {dst.name} (exists, use --force to overwrite)")
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    logger.info(f"  create {dst.relative_to(dst.parent.parent) if dst.parent.parent else dst.name}")
    return True


def scaffold(target_dir: Path, force: bool = False, template: str = "default") -> bool:
    """Scaffold a docs directory with SDBS templates.

    Args:
        target_dir: Directory to create/initialize.
        force: Overwrite existing files.
        template: Template flavour name (subdirectory under templates/).
                  Falls back to 'default' if not found.

    Returns:
        True if all files were copied successfully.
    """
    target = target_dir.resolve()
    logger.info(f"Scaffolding docs directory: {target}")

    if not TEMPLATES_PACKAGE.is_dir():
        logger.error(f"Templates directory not found: {TEMPLATES_PACKAGE}")
        return False

    template_dir = TEMPLATES_PACKAGE / template
    if not template_dir.is_dir():
        logger.warning(
            f"Template '{template}' not found at {template_dir}, "
            f"falling back to 'default'."
        )
        template = "default"
        template_dir = TEMPLATES_PACKAGE / template

    template_map = SSCCS_TEMPLATE_MAP if template == "ssccs" else DEFAULT_TEMPLATE_MAP

    logger.info(f"Using '{template}' template set")

    total = 0
    errors = 0

    for rel_dst, template_name in template_map.items():
        src = template_dir / template_name
        dst = target / rel_dst

        if not src.exists():
            logger.warning(f"  template not found: {src}")
            errors += 1
            continue

        try:
            if _copy_template(src, dst, force):
                total += 1
        except OSError as e:
            logger.error(f"  failed to copy {template_name}: {e}")
            errors += 1

    if errors:
        logger.warning(f"Completed with {errors} error(s), {total} file(s) written.")
        return False

    logger.info(f"Done. {total} file(s) written to {target}")
    logger.info("")
    logger.info("Next steps:")
    if template == "ssccs":
        logger.info("  1. Edit _include/author.yml with your information")
        logger.info("  2. Edit _quarto-website.yml with your site URL and repo")
        logger.info("  3. Review _include/_graphviz.py for DOT diagram utilities")
        logger.info("  4. Add your content as .qmd files")
        logger.info("  5. Run:  sdb build . --website")
    else:
        logger.info("  1. Uncomment and configure _include/author.yml with your information")
        logger.info("  2. Uncomment and configure _quarto-website.yml with your site URL")
        logger.info("  3. Add your content as .qmd files")
        logger.info("  4. Run:  sdb build . --website")
    return True
