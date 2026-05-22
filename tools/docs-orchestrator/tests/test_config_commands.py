"""Tests for sdb.build._run_config_commands."""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from sdb.build import _run_config_commands


@pytest.fixture
def docs_root() -> Path:
    return Path("/tmp/test_docs")


@pytest.fixture
def mock_subprocess() -> MagicMock:
    with patch("sdb.build.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0, stdout="", stderr=""
        )
        yield mock_run


@pytest.fixture
def mock_which() -> MagicMock:
    with patch("sdb.build.shutil.which") as mock_w:
        mock_w.return_value = "/usr/bin/echo"
        yield mock_w


@pytest.fixture
def mock_dispatch() -> MagicMock:
    with patch("sdb.build._try_dispatch_inline") as mock_d:
        mock_d.return_value = False
        yield mock_d


@pytest.fixture
def mock_logger() -> MagicMock:
    with patch("sdb.build.logger") as mock_log:
        yield mock_log


class TestEmptySection:
    """Empty or falsy sections should be no-ops."""

    def test_none(self, docs_root: Path) -> None:
        _run_config_commands(None, docs_root, "Pre-build")
        _run_config_commands(None, docs_root, "Post-render", target_name="foo")

    def test_empty_list(self, docs_root: Path) -> None:
        _run_config_commands([], docs_root, "Pre-build")

    def test_empty_dict(self, docs_root: Path) -> None:
        _run_config_commands({}, docs_root, "Post-render")


class TestListStyleGlobalCommands:
    """When section is a list, all entries are global commands."""

    def test_single_command(
        self,
        docs_root: Path,
        mock_subprocess: MagicMock,
        mock_which: MagicMock,
        mock_dispatch: MagicMock,
    ) -> None:
        section = [["echo", "hello"]]
        _run_config_commands(section, docs_root, "Pre-build")
        mock_subprocess.assert_called_once_with(
            ["echo", "hello"],
            cwd=docs_root,
            capture_output=True,
            text=True,
        )

    def test_multiple_commands(
        self,
        docs_root: Path,
        mock_subprocess: MagicMock,
        mock_which: MagicMock,
        mock_dispatch: MagicMock,
    ) -> None:
        section = [["echo", "one"], ["echo", "two"]]
        _run_config_commands(section, docs_root, "Pre-build")
        assert mock_subprocess.call_count == 2

    def test_global_commands_with_target_name_nonexistent(
        self,
        docs_root: Path,
        mock_subprocess: MagicMock,
        mock_which: MagicMock,
        mock_dispatch: MagicMock,
    ) -> None:
        """List-style section with target_name that doesn't exist in target_commands
        runs nothing (list-style implies no target-keyed entries).
        """
        section = [["echo", "hello"]]
        _run_config_commands(section, docs_root, "Pre-build", target_name="foo")
        mock_subprocess.assert_not_called()


class TestDictStyleWithGlobalKey:
    """Dict-style section with a '_global' key."""

    def test_global_only(
        self,
        docs_root: Path,
        mock_subprocess: MagicMock,
        mock_which: MagicMock,
        mock_dispatch: MagicMock,
    ) -> None:
        section = {"_global": [["echo", "hello"]]}
        _run_config_commands(section, docs_root, "Pre-build")
        mock_subprocess.assert_called_once_with(
            ["echo", "hello"],
            cwd=docs_root,
            capture_output=True,
            text=True,
        )

    def test_global_no_target(
        self,
        docs_root: Path,
        mock_subprocess: MagicMock,
        mock_which: MagicMock,
        mock_dispatch: MagicMock,
    ) -> None:
        section = {
            "_global": [["echo", "global"]],
            "whitepaper": [["echo", "whitepaper"]],
        }
        _run_config_commands(section, docs_root, "Pre-build")
        mock_subprocess.assert_called_once_with(
            ["echo", "global"],
            cwd=docs_root,
            capture_output=True,
            text=True,
        )

    def test_global_missing_key(
        self,
        docs_root: Path,
        mock_subprocess: MagicMock,
        mock_which: MagicMock,
        mock_dispatch: MagicMock,
    ) -> None:
        section = {"_global": []}
        _run_config_commands(section, docs_root, "Pre-build")
        mock_subprocess.assert_not_called()


class TestDictStyleTargetSpecific:
    """Dict-style section with target-specific commands."""

    def test_target_specific_commands(
        self,
        docs_root: Path,
        mock_subprocess: MagicMock,
        mock_which: MagicMock,
        mock_dispatch: MagicMock,
    ) -> None:
        section = {
            "_global": [["echo", "global"]],
            "whitepaper": [["echo", "whitepaper"]],
        }
        _run_config_commands(
            section, docs_root, "Pre-build", target_name="whitepaper"
        )
        # Only the target-specific command runs when target_name is provided;
        # global commands only run when target_name is None.
        mock_subprocess.assert_called_once_with(
            ["echo", "whitepaper"],
            cwd=docs_root,
            capture_output=True,
            text=True,
        )

    def test_only_global_when_target_missing(
        self,
        docs_root: Path,
        mock_subprocess: MagicMock,
        mock_which: MagicMock,
        mock_dispatch: MagicMock,
    ) -> None:
        """target_name that doesn't exist in target_commands -> nothing runs.
        Global commands only execute when target_name is None.
        """
        section = {
            "_global": [["echo", "global"]],
            "whitepaper": [["echo", "whitepaper"]],
        }
        _run_config_commands(
            section, docs_root, "Pre-build", target_name="proposal"
        )
        mock_subprocess.assert_not_called()

    def test_target_without_global(
        self,
        docs_root: Path,
        mock_subprocess: MagicMock,
        mock_which: MagicMock,
        mock_dispatch: MagicMock,
    ) -> None:
        section = {"whitepaper": [["echo", "whitepaper"]]}
        _run_config_commands(
            section, docs_root, "Post-render", target_name="whitepaper"
        )
        mock_subprocess.assert_called_once_with(
            ["echo", "whitepaper"],
            cwd=docs_root,
            capture_output=True,
            text=True,
        )


class TestInvalidSectionType:
    """Non-list, non-dict sections should warn and return gracefully."""

    def test_string_section(
        self, docs_root: Path, mock_logger: MagicMock
    ) -> None:
        _run_config_commands("some_string", docs_root, "Pre-build")
        mock_logger.warning.assert_called_once()
        warning_msg = mock_logger.warning.call_args[0][0]
        assert "Invalid" in warning_msg
        assert "str" in warning_msg

    def test_int_section(
        self, docs_root: Path, mock_logger: MagicMock
    ) -> None:
        _run_config_commands(42, docs_root, "Post-render")
        mock_logger.warning.assert_called_once()
        warning_msg = mock_logger.warning.call_args[0][0]
        assert "Invalid" in warning_msg
        assert "int" in warning_msg


class TestInvalidCommandEntry:
    """Invalid entries within a valid section should be skipped with warning."""

    def test_string_instead_of_list(
        self,
        docs_root: Path,
        mock_subprocess: MagicMock,
        mock_dispatch: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        mock_dispatch.return_value = False
        with patch("sdb.build.shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/echo"
            section = [["echo", "valid"], "invalid_string"]
            _run_config_commands(section, docs_root, "Pre-build")
            mock_subprocess.assert_called_once_with(
                ["echo", "valid"],
                cwd=docs_root,
                capture_output=True,
                text=True,
            )
            warning_calls = [
                c for c in mock_logger.warning.call_args_list
                if "Invalid" in c[0][0] or "skipping" in c[0][0]
            ]
            assert len(warning_calls) >= 1

    def test_empty_command_list(
        self,
        docs_root: Path,
        mock_subprocess: MagicMock,
        mock_dispatch: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        mock_dispatch.return_value = False
        with patch("sdb.build.shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/echo"
            section = [["echo", "valid"], []]
            _run_config_commands(section, docs_root, "Pre-build")
            mock_subprocess.assert_called_once_with(
                ["echo", "valid"],
                cwd=docs_root,
                capture_output=True,
                text=True,
            )

    def test_target_command_invalid_type(
        self,
        docs_root: Path,
        mock_subprocess: MagicMock,
        mock_dispatch: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        mock_dispatch.return_value = False
        with patch("sdb.build.shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/echo"
            # Use a dict (not list or str) to trigger the invalid-type warning.
            section = {
                "_global": [["echo", "global"]],
                "whitepaper": {"invalid": "format"},
            }
            _run_config_commands(
                section, docs_root, "Post-render", target_name="whitepaper"
            )
            # The invalid target command is skipped; global commands do not run
            # when target_name is provided, so nothing executes.
            mock_subprocess.assert_not_called()
            mock_logger.warning.assert_any_call(
                "Invalid post-render entry for target "
                "'whitepaper': {'invalid': 'format'}, skipping."
            )


class TestPhaseLabelInLogs:
    """Verify that the phase argument is reflected in log messages."""

    def test_pre_build_label(
        self,
        docs_root: Path,
        mock_subprocess: MagicMock,
        mock_which: MagicMock,
        mock_dispatch: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        section = [["echo", "hello"]]
        _run_config_commands(section, docs_root, "Pre-build")
        info_messages = [
            c[0][0] for c in mock_logger.info.call_args_list
        ]
        joined = " ".join(info_messages)
        assert "Pre-build" in joined

    def test_post_render_label(
        self,
        docs_root: Path,
        mock_subprocess: MagicMock,
        mock_which: MagicMock,
        mock_dispatch: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        section = [["echo", "hello"]]
        _run_config_commands(section, docs_root, "Post-render")
        info_messages = [
            c[0][0] for c in mock_logger.info.call_args_list
        ]
        joined = " ".join(info_messages)
        assert "Post-render" in joined
