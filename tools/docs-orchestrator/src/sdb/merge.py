from __future__ import annotations

import logging
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# SharedAssetMerger — base class for shared asset merger handlers
# ---------------------------------------------------------------------------


@dataclass
class SharedAssetMerger:
    """Base class for shared asset merger handlers."""

    name: str
    # Filename patterns this handler handles (exact match or glob pattern)
    filename_patterns: List[str] = field(default_factory=list)

    def handles_file(self, filename: str) -> bool:
        """Check if this handler handles the given filename."""
        import fnmatch

        for pattern in self.filename_patterns:
            if fnmatch.fnmatch(filename, pattern):
                return True
        return False

    def merge(self, src_path: Path, dst_path: Path) -> bool:
        """
        Merge source file into destination file.
        If dst_path does not exist, simply copy src_path to dst_path.
        Returns True on success, False on error.
        Subclasses should override this.
        """
        raise NotImplementedError


class SearchJsonMerger(SharedAssetMerger):
    """Merger for search.json files (JSON array concatenation with deduplication)."""

    def __init__(self):
        super().__init__(
            name="search_json",
            filename_patterns=["search.json"],
        )

    def merge(self, src_path: Path, dst_path: Path) -> bool:
        """
        Merge two search.json files by concatenating their arrays and deduplicating by objectID.
        If dst_path does not exist, simply copy src_path to dst_path.
        Returns True on success, False on error.
        """
        try:
            import json

            # Read source
            with open(src_path, "r", encoding="utf-8") as f:
                src_data = json.load(f)
            # If destination doesn't exist, copy
            if not dst_path.exists():
                shutil.copy2(src_path, dst_path)
                return True
            # Read destination
            with open(dst_path, "r", encoding="utf-8") as f:
                dst_data = json.load(f)
            # Ensure both are lists
            if not isinstance(src_data, list) or not isinstance(dst_data, list):
                logger.warning(
                    "search.json does not contain a JSON array, overwriting with source."
                )
                shutil.copy2(src_path, dst_path)
                return True
            # Merge: concatenate
            merged = src_data + dst_data
            # Deduplicate by objectID
            seen = {}
            unique = []
            for item in merged:
                obj_id = item.get("objectID")
                if obj_id not in seen:
                    seen[obj_id] = True
                    unique.append(item)
            # Write back
            with open(dst_path, "w", encoding="utf-8") as f:
                json.dump(unique, f, ensure_ascii=False, indent=2)
            logger.debug(f"Merged search.json from {src_path} into {dst_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to merge search.json {src_path} -> {dst_path}: {e}")
            return False


class SitemapXmlMerger(SharedAssetMerger):
    """Merger for sitemap.xml files (XML URL set union)."""

    def __init__(self):
        super().__init__(
            name="sitemap_xml",
            filename_patterns=["sitemap.xml"],
        )

    def merge(self, src_path: Path, dst_path: Path) -> bool:
        """
        Merge two sitemap.xml files by combining their URL entries.
        Deduplicates by URL (loc element content).
        If dst_path does not exist, simply copy src_path to dst_path.
        Returns True on success, False on error.
        """
        try:
            import xml.etree.ElementTree as ET

            # If destination doesn't exist, copy
            if not dst_path.exists():
                shutil.copy2(src_path, dst_path)
                return True

            # Parse both XML files
            src_tree = ET.parse(src_path)
            dst_tree = ET.parse(dst_path)

            src_root = src_tree.getroot()
            dst_root = dst_tree.getroot()

            # Extract namespace if present
            ns = {}
            if src_root.tag.startswith("{"):
                ns_uri = src_root.tag.split("}")[0][1:]
                ns["ns"] = ns_uri

            # Collect existing URLs from destination
            existing_urls = set()
            for url in (
                dst_root.findall(".//ns:url", ns) if ns else dst_root.findall(".//url")
            ):
                loc = url.find("ns:loc", ns) if ns else url.find("loc")
                if loc is not None and loc.text:
                    existing_urls.add(loc.text)

            # Collect URL elements from source that don't exist in destination
            url_elements_to_add = []
            for url in (
                src_root.findall(".//ns:url", ns) if ns else src_root.findall(".//url")
            ):
                loc = url.find("ns:loc", ns) if ns else url.find("loc")
                if loc is not None and loc.text:
                    if loc.text not in existing_urls:
                        url_elements_to_add.append(url)

            # Add new URL elements to destination
            for url_elem in url_elements_to_add:
                dst_root.append(url_elem)

            # Write merged result
            ET.indent(dst_tree, space="  ")
            dst_tree.write(dst_path, encoding="utf-8", xml_declaration=True)

            logger.debug(
                f"Merged sitemap.xml from {src_path} into {dst_path} (added {len(url_elements_to_add)} new URLs)"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to merge sitemap.xml {src_path} -> {dst_path}: {e}")
            return False


class RobotsTxtMerger(SharedAssetMerger):
    """
    Merger for robots.txt files.
    Since robots.txt is typically a simple configuration file, we use source precedence.
    This can be customized based on project needs.
    """

    def __init__(self):
        super().__init__(
            name="robots_txt",
            filename_patterns=["robots.txt"],
        )

    def merge(self, src_path: Path, dst_path: Path) -> bool:
        """
        For robots.txt, source takes precedence (overwrite destination).
        This is because robots.txt is typically a site-wide configuration.
        Returns True on success, False on error.
        """
        try:
            shutil.copy2(src_path, dst_path)
            logger.debug(
                f"Copied robots.txt from {src_path} to {dst_path} (source precedence)"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to copy robots.txt {src_path} -> {dst_path}: {e}")
            return False


class LlmsTxtMerger(SharedAssetMerger):
    """
    Merger for llms.txt files (markdown list of page links).
    Combines page entries from multiple targets and deduplicates by URL.
    """

    def __init__(self):
        super().__init__(
            name="llms_txt",
            filename_patterns=["llms.txt"],
        )

    def _parse_page_entries(self, content: str) -> List[Tuple[str, str]]:
        """
        Parse llms.txt content and extract page entries as (name, url) tuples.
        Returns list of (name, url) tuples found in markdown list items.
        """
        entries = []
        # Match markdown list items with links: - [name](url)
        pattern = re.compile(r"^\s*-\s*\[([^\]]+)\]\(([^)]+)\)\s*$")
        for line in content.splitlines():
            match = pattern.match(line)
            if match:
                name, url = match.groups()
                entries.append((name.strip(), url.strip()))
        return entries

    def _generate_content(
        self, entries: List[Tuple[str, str]], title: str = "Untitled"
    ) -> str:
        """
        Generate llms.txt content from page entries.
        Returns formatted markdown content.
        """
        lines = [f"# {title}", "", "## Pages", ""]
        for name, url in entries:
            lines.append(f"- [{name}]({url})")
        return "\n".join(lines) + "\n"

    def merge(self, src_path: Path, dst_path: Path) -> bool:
        """
        Merge two llms.txt files by combining their page entries.
        Deduplicates by URL (keeping the first occurrence).
        If dst_path does not exist, simply copy src_path to dst_path.
        Returns True on success, False on error.
        """
        try:
            # Read source
            with open(src_path, "r", encoding="utf-8") as f:
                src_content = f.read()

            # If destination doesn't exist, copy
            if not dst_path.exists():
                shutil.copy2(src_path, dst_path)
                return True

            # Read destination
            with open(dst_path, "r", encoding="utf-8") as f:
                dst_content = f.read()

            # Parse entries from both files
            src_entries = self._parse_page_entries(src_content)
            dst_entries = self._parse_page_entries(dst_content)

            # Extract title from destination (or use default)
            title = "Untitled"
            for line in dst_content.splitlines():
                if line.startswith("# "):
                    title = line[2:].strip()
                    break

            # Merge entries: start with destination, add source entries not in destination
            seen_urls = set()
            merged_entries = []

            # Add destination entries first (they take precedence)
            for name, url in dst_entries:
                if url not in seen_urls:
                    seen_urls.add(url)
                    merged_entries.append((name, url))

            # Add source entries that don't exist in destination
            for name, url in src_entries:
                if url not in seen_urls:
                    seen_urls.add(url)
                    merged_entries.append((name, url))

            # Generate merged content
            merged_content = self._generate_content(merged_entries, title)

            # Write back
            with open(dst_path, "w", encoding="utf-8") as f:
                f.write(merged_content)

            logger.debug(
                f"Merged llms.txt from {src_path} into {dst_path} (added {len(merged_entries) - len(dst_entries)} new entries)"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to merge llms.txt {src_path} -> {dst_path}: {e}")
            return False


# Registry of shared asset mergers
SHARED_ASSET_MERGERS: List[SharedAssetMerger] = [
    SearchJsonMerger(),
    SitemapXmlMerger(),
    RobotsTxtMerger(),
    LlmsTxtMerger(),
]


def get_merger_for_file(filename: str) -> Optional[SharedAssetMerger]:
    """Get the appropriate merger handler for a given filename."""
    for merger in SHARED_ASSET_MERGERS:
        if merger.handles_file(filename):
            return merger
    return None


def merge_shared_asset(src_path: Path, dst_path: Path) -> bool:
    """
    Merge a shared asset file from source to destination.
    Returns True if merged successfully, False if no merger found or error.
    """
    merger = get_merger_for_file(src_path.name)
    if merger is None:
        return False
    return merger.merge(src_path, dst_path)


def _is_target_specific_file(file_path: Path, target_name: str, base_dir: Path) -> bool:
    """
    Determine if a file is target-specific and should not be overwritten by other targets.

    Target-specific files include:
    - {target}/{target}.html (e.g., whitepaper/whitepaper.html)
    - {target}/index.html when target name matches folder (e.g., legal/index.html for legal target)
    - {target}.pdf at root level
    - Files under a directory matching the target name

    Returns True if the file is target-specific to the given target.
    """
    try:
        rel_path = file_path.relative_to(base_dir)
        parts = rel_path.parts

        # Check if any directory component matches target name
        for i, part in enumerate(parts[:-1]):  # Exclude filename
            if part == target_name:
                # File is under target directory
                filename = parts[-1]
                stem = filename.rsplit(".", 1)[0] if "." in filename else filename

                # index.html/index.pdf under target dir belongs to that target
                if filename in ("index.html", "index.pdf"):
                    return True
                # {target}.html or {target}.pdf belongs to that target
                if stem == target_name:
                    return True
                # Any file under target dir is target-specific
                return True

        # Check root-level files: {target}.html, {target}.pdf belong to that target
        if len(parts) == 1:
            filename = parts[0]
            stem = filename.rsplit(".", 1)[0] if "." in filename else filename
            if stem == target_name and filename.endswith((".html", ".pdf")):
                return True
    except ValueError:
        pass

    return False


def merge_dirs(src: Path, dst: Path, target_name: Optional[str] = None) -> bool:
    """
    Merge contents of src directory into dst directory using rsync-style algorithm.

    Core principle: The final _site result is a "union without duplicates" at the file content level.
    - All files from all sources are included (nothing should be missing)
    - Shared files like search.json are merged at the content level
    - Target-specific files (e.g., target/target.html) are protected from being overwritten by other targets
    - For index.qmd targets, the folder name IS the target name, so index.html/index.pdf
      from that target belongs to it (e.g., legal/index.html is the legal target's file)

    This function uses rsync for efficient file synchronization with the following behavior:
    - Files in src are copied to dst (overwriting if needed, except for target-specific files)
    - Files in dst that don't exist in src are preserved (union behavior)
    - Directory structure is preserved

    Args:
        src: Source directory to merge from
        dst: Destination directory to merge into
        target_name: Optional target name for determining file ownership

    Returns True on success, False on error.
    """
    try:
        # Ensure destination exists
        dst.mkdir(parents=True, exist_ok=True)

        # First, handle shared assets that need content-level merging
        # Get list of filenames handled by shared asset mergers
        shared_filenames = set()
        for merger in SHARED_ASSET_MERGERS:
            for pattern in merger.filename_patterns:
                # Add exact pattern (e.g., "search.json")
                if "*" not in pattern and "?" not in pattern:
                    shared_filenames.add(pattern)

        # Process shared assets
        for filename in shared_filenames:
            src_file = src / filename
            dst_file = dst / filename
            if src_file.exists():
                if not merge_shared_asset(src_file, dst_file):
                    # No merger found or error - fall back to copy
                    if not dst_file.exists():
                        shutil.copy2(src_file, dst_file)
                        logger.debug(
                            f"Copied shared file {src_file} to {dst_file} (no merger)"
                        )

        # Build exclude list for rsync (files handled by shared asset mergers)
        rsync_excludes = []
        for filename in shared_filenames:
            rsync_excludes.extend(["--exclude", filename])

        # Use rsync for the rest of the files
        # Flags:
        #   -a: archive mode (preserves permissions, timestamps, etc.)
        #   --ignore-existing: skip files that already exist in dst (union behavior)
        #   --exclude: skip files we handle specially

        rsync_cmd = (
            [
                "rsync",
                "-a",
                "--ignore-existing",  # Keep existing files in dst (union behavior)
            ]
            + rsync_excludes
            + [
                str(src) + "/",  # Trailing slash means "contents of src"
                str(dst) + "/",
            ]
        )

        result = subprocess.run(rsync_cmd, capture_output=True, text=True)
        if result.returncode not in (0, 23, 24):
            # 0 = success, 23 = some files vanished, 24 = vanished during transfer
            # These are acceptable for our use case
            logger.debug(f"rsync completed with code {result.returncode}")

        # Second pass: copy target-specific files from src, overwriting any existing files
        # (target-specific files have highest priority)
        if target_name:
            for src_file in src.rglob("*"):
                if src_file.is_file():
                    rel_path = src_file.relative_to(src)
                    dst_file = dst / rel_path

                    # Check if this is a target-specific file
                    if _is_target_specific_file(src_file, target_name, src):
                        # Copy target-specific file regardless of existence (overwrite)
                        dst_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src_file, dst_file)
                        logger.debug(
                            f"Copied target-specific file {src_file} -> {dst_file}"
                        )

        return True
    except Exception as e:
        logger.error(f"Failed to merge {src} into {dst}: {e}")
        return False
