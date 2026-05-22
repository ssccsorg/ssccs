"""Tests for sdb.init.scaffold."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from sdb.init import scaffold


@pytest.fixture
def temp_target() -> Path:
    """Yield a temporary directory that is cleaned up after the test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestScaffoldUnknownTemplate:
    """scaffold() with a non-existent template flavour."""

    def test_fallback_to_default(self, temp_target: Path) -> None:
        """Warns and falls back to 'default' when template flavour not found."""
        with patch("sdb.init.logger") as mock_logger:
            result = scaffold(temp_target, force=False, template="nonexistent_flavour")
            assert result is True
            warning_messages = [
                c[0][0] for c in mock_logger.warning.call_args_list
            ]
            joined = " ".join(warning_messages)
            assert "falling back" in joined
            assert "default" in joined

    def test_returns_false_when_templates_dir_missing(
        self, temp_target: Path
    ) -> None:
        """Returns False if the templates directory itself is missing."""
        with (
            patch("sdb.init.TEMPLATES_PACKAGE", Path("/nonexistent/templates")),
            patch("sdb.init.logger") as mock_logger,
        ):
            result = scaffold(temp_target, force=False, template="default")
            assert result is False
            error_messages = [
                c[0][0] for c in mock_logger.error.call_args_list
            ]
            joined = " ".join(error_messages)
            assert "Templates directory not found" in joined


class TestScaffoldForceOverwrite:
    """scaffold() with force=True overwrites existing files."""

    def test_overwrites_existing_file(self, temp_target: Path) -> None:
        """When force=True, an existing file is overwritten."""
        existing_file = temp_target / "build.yml"
        existing_file.parent.mkdir(parents=True, exist_ok=True)
        existing_file.write_text("old content")

        with patch("sdb.init.logger") as mock_logger:
            result = scaffold(temp_target, force=True, template="default")
            assert result is True
            # The file should now contain the template content, not "old content"
            content = existing_file.read_text()
            assert content != "old content"
            assert len(content) > 0


class TestScaffoldForceFalseSkip:
    """scaffold() with force=False skips existing files."""

    def test_skips_existing_file(self, temp_target: Path) -> None:
        """When force=False, an existing file is left untouched."""
        existing_file = temp_target / "build.yml"
        existing_file.parent.mkdir(parents=True, exist_ok=True)
        existing_file.write_text("original content")

        with patch("sdb.init.logger") as mock_logger:
            result = scaffold(temp_target, force=False, template="default")
            assert result is True
            content = existing_file.read_text()
            assert content == "original content"
            skip_messages = [
                c[0][0] for c in mock_logger.info.call_args_list
                if "skip" in c[0][0].lower()
            ]
            assert len(skip_messages) > 0


class TestScaffoldFullRun:
    """End-to-end checks of scaffold behaviour."""

    def test_creates_files_in_empty_directory(
        self, temp_target: Path
    ) -> None:
        """Scaffolding into an empty directory should create all expected files."""
        result = scaffold(temp_target, force=False, template="default")
        assert result is True
        expected_files = [
            "build.yml",
            "_quarto.yml",
            "index.qmd",
            ".gitignore",
        ]
        for rel_path in expected_files:
            assert (temp_target / rel_path).exists(), (
                f"Expected file {rel_path} was not created"
            )

    def test_ssccs_template_creates_extra_files(
        self, temp_target: Path
    ) -> None:
        """The 'ssccs' template should create ssccs-specific files."""
        result = scaffold(temp_target, force=False, template="ssccs")
        assert result is True
        ssccs_files = [
            "_include/_graphviz.py",
            "_include/_title_meta_items.qmd",
        ]
        for rel_path in ssccs_files:
            assert (temp_target / rel_path).exists(), (
                f"Expected SSCCS-specific file {rel_path} was not created"
            )

    def test_return_false_on_copy_error(self, temp_target: Path) -> None:
        """If a template file is missing from the template dir, scaffold warns
        and returns False."""
        with patch("sdb.init._copy_template") as mock_copy:
            mock_copy.side_effect = OSError("Permission denied")
            with patch("sdb.init.logger"):
                result = scaffold(
                    temp_target, force=False, template="default"
                )
                assert result is False
