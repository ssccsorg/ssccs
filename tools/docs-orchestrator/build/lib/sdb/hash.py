from __future__ import annotations

import hashlib
import logging
import shlex
from functools import lru_cache
from pathlib import Path
from typing import Set

from .config import QUARTO_CONFIG_FILES
from .quarto import QuartoInspector

logger = logging.getLogger(__name__)


class HashManager:
    """File hashing and QMD dependency graph computation."""

    @staticmethod
    @lru_cache(maxsize=128)
    def compute_file_hash(path: Path) -> str:
        try:
            with open(path, "rb") as f:
                return hashlib.file_digest(f, "sha256").hexdigest()
        except FileNotFoundError:
            raise

    @staticmethod
    @lru_cache(maxsize=32)
    def compute_quarto_file_hash_with_deps(file_path: Path, docs_root: Path) -> str:
        visited: Set[Path] = set()

        def resolve(base: Path, rel: str) -> Path:
            return (base.parent / rel).resolve()

        def collect(path: Path) -> None:
            if path in visited:
                return
            visited.add(path)
            data = QuartoInspector.inspect(path)
            if data is None:
                return
            fi = data.get("fileInformation", {})
            entry = None
            for key, val in fi.items():
                if Path(key).resolve() == path.resolve():
                    entry = val
                    break
            if entry is None:
                return
            for gcfg in [docs_root / file for file in QUARTO_CONFIG_FILES]:
                if gcfg.exists():
                    visited.add(gcfg.resolve())
            for inc in entry.get("includeMap", []):
                target_rel = inc.get("target")
                if target_rel:
                    target = resolve(path, target_rel)
                    if target.suffix.lower() == ".qmd":
                        collect(target)
                    else:
                        visited.add(target)
            for cell in entry.get("codeCells", []):
                source = cell.get("source", "")
                for line in source.splitlines():
                    line = line.strip()
                    if line.startswith("%run"):
                        tokens = shlex.split(line)
                        if len(tokens) >= 2:
                            run_path = tokens[1]
                            run_path = run_path.split("--")[0].strip()
                            if run_path:
                                cell_file = cell.get("file")
                                base_f = Path(cell_file).parent if cell_file else path.parent
                                try:
                                    dep = (base_f / run_path).resolve()
                                    if dep.exists():
                                        visited.add(dep)
                                except (OSError, ValueError) as e:
                                    logger.debug(
                                        f"Skipping unresolvable %run dependency '{run_path}': {e}"
                                    )
            for config_path in data.get("config", []):
                visited.add(Path(config_path).resolve())
            for resource_path in data.get("configResources", []):
                visited.add(Path(resource_path).resolve())
            for fmt_config in data.get("formats", {}).values():
                pandoc = fmt_config.get("pandoc", {})
                for mf in pandoc.get("metadata-files", []):
                    visited.add(resolve(path, mf))
                bib = pandoc.get("bibliography")
                if bib:
                    visited.add(resolve(path, bib))
                csl = pandoc.get("csl")
                if csl:
                    visited.add(resolve(path, csl))

        collect(file_path.resolve())

        hasher = hashlib.sha256()
        hasher.update(file_path.suffix.encode("utf-8"))
        for dep in sorted(visited, key=str):
            try:
                dep_hash = HashManager.compute_file_hash(dep)
                hasher.update(dep_hash.encode("utf-8"))
            except FileNotFoundError:
                hasher.update(b"<missing>")
        hasher.update(file_path.suffix.encode("utf-8"))
        return hasher.hexdigest()
