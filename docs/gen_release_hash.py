#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-SSCCS-Research-Preview-1.0
# Copyright (c) 2026 Taeho Lee, SSCCS Initiative.
#
# Update release_hash in docs/index.qmd from the docs qmd set. The hash covers
# the pages, not the generated support files, and excludes its own value so a
# second run is a no-op.

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.qmd"
HASH_LINE = re.compile(r"(?m)^release_hash:\s*[0-9a-f]{64}\s*$")

# Generated and support directories are not part of the page release surface.
EXCLUDED_DIRS = {
    "_site",
    "_llms",
    "_include",
    "_extensions",
    "_utils",
    ".quarto",
    ".jupyter_cache",
}
EXCLUDED_SUFFIXES = ("_files", "_output", "_libs", "_pages")
SKIPPED_PREFIXES = (".sdbtmp_", "_sdbtmp_")


def qmd_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*.qmd"):
        relative = path.relative_to(ROOT)
        directories = relative.parts[:-1]
        if any(part in EXCLUDED_DIRS for part in directories):
            continue
        if any(part.endswith(EXCLUDED_SUFFIXES) for part in directories):
            continue
        if any(part.startswith(SKIPPED_PREFIXES) for part in directories):
            continue
        if relative.name.endswith("_.qmd"):
            continue
        files.append(path)
    return sorted(files, key=lambda p: p.relative_to(ROOT).as_posix())


def content_for_hash(path: Path) -> bytes:
    data = path.read_bytes()
    if path == INDEX:
        # The release value must not feed back into the hash it is derived from.
        text = data.decode("utf-8")
        data = HASH_LINE.sub("release_hash:", text).encode("utf-8")
    return data


def aggregate(files: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.relative_to(ROOT).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(content_for_hash(path))
        digest.update(b"\0")
    return digest.hexdigest()


def update_index(new_hash: str) -> bool:
    text = INDEX.read_text(encoding="utf-8")
    if not HASH_LINE.search(text):
        raise SystemExit(f"release_hash not found in {INDEX}")
    updated = HASH_LINE.sub(f"release_hash: {new_hash}", text, count=1)
    if updated == text:
        return False
    temporary = INDEX.with_suffix(".tmp")
    temporary.write_text(updated, encoding="utf-8")
    temporary.replace(INDEX)
    return True


def main() -> int:
    files = qmd_files()
    if not files:
        raise SystemExit("no qmd files found under docs/")
    new_hash = aggregate(files)
    changed = update_index(new_hash)
    state = "updated" if changed else "unchanged"
    print(f"release_hash: {new_hash} ({len(files)} qmd files, {state})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
