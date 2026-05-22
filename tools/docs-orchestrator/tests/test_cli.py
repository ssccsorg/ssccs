"""Tests for sdb.cli argument parsing."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from sdb.cli import main


def _run_main(argv: list[str]) -> int:
    """Run main() with the given argv and return the exit code.

    Catches SystemExit and returns the code.
    """
    try:
        main(argv)
        return 0
    except SystemExit as e:
        return e.code if e.code is not None else 0


class TestInitCommand:
    """Tests for the ``sdb init`` subcommand."""

    def test_init_defaults(self) -> None:
        """sdb init -> command='init', path=Path('docs'), force=False, template='default'."""
        with patch("sdb.cli.init_module.scaffold") as mock_scaffold:
            mock_scaffold.return_value = True
            code = _run_main(["init"])
            assert code == 0
            mock_scaffold.assert_called_once_with(
                Path("docs"), force=False, template="default"
            )

    def test_init_custom_path_force(self) -> None:
        """sdb init /tmp/test --force -> path=Path('/tmp/test'), force=True."""
        with patch("sdb.cli.init_module.scaffold") as mock_scaffold:
            mock_scaffold.return_value = True
            code = _run_main(["init", "/tmp/test", "--force"])
            assert code == 0
            mock_scaffold.assert_called_once_with(
                Path("/tmp/test"), force=True, template="default"
            )

    def test_init_template_ssccs(self) -> None:
        """sdb init --template ssccs -> template='ssccs'."""
        with patch("sdb.cli.init_module.scaffold") as mock_scaffold:
            mock_scaffold.return_value = True
            code = _run_main(["init", "--template", "ssccs"])
            assert code == 0
            mock_scaffold.assert_called_once_with(
                Path("docs"), force=False, template="ssccs"
            )

    def test_init_failure_exit_code(self) -> None:
        """When scaffold returns False, sdb init should exit with code 1."""
        with patch("sdb.cli.init_module.scaffold") as mock_scaffold:
            mock_scaffold.return_value = False
            code = _run_main(["init"])
            assert code == 1

    def test_init_force_and_template(self) -> None:
        """sdb init /my/path --force --template ssccs."""
        with patch("sdb.cli.init_module.scaffold") as mock_scaffold:
            mock_scaffold.return_value = True
            code = _run_main(
                ["init", "/my/path", "--force", "--template", "ssccs"]
            )
            assert code == 0
            mock_scaffold.assert_called_once_with(
                Path("/my/path"), force=True, template="ssccs"
            )


class TestBuildCommand:
    """Tests for the ``sdb build`` subcommand."""

    def test_build_defaults(self) -> None:
        """sdb build . --website -> command='build', docs_root=Path('.'), website=True, targets=['all']."""
        with (
            patch("sdb.cli.build_module.initialize_config"),
            patch("sdb.cli.build_module.build_targets") as mock_build,
            patch("sdb.cli.build_module.BUILD_FUNCTIONS", {"doc": lambda: True}),
        ):
            mock_build.return_value = True
            code = _run_main(["build", ".", "--website"])
            assert code == 0

    def test_build_with_targets(self) -> None:
        """sdb build docs whitepaper --website -j 4 -> targets=['whitepaper'], website=True, jobs=4."""
        with (
            patch("sdb.cli.build_module.initialize_config"),
            patch("sdb.cli.build_module.parse_targets") as mock_parse,
            patch("sdb.cli.build_module.validate_targets") as mock_validate,
            patch("sdb.cli.build_module.build_targets") as mock_build,
            patch("sdb.cli.build_module.BUILD_FUNCTIONS", {"doc": lambda: True}),
        ):
            mock_parse.return_value = ["whitepaper"]
            mock_validate.return_value = ["whitepaper"]
            mock_build.return_value = True
            code = _run_main(
                ["build", "docs", "whitepaper", "--website", "-j", "4"]
            )
            assert code == 0
            mock_parse.assert_called_once_with(["whitepaper"])
            mock_build.assert_called_once()
            _kwargs: dict[str, Any] = mock_build.call_args.kwargs
            assert _kwargs["max_jobs"] == 4
            assert _kwargs["website"] is True

    def test_build_all_implicit(self) -> None:
        """When no targets specified, defaults to ['all']."""
        with (
            patch("sdb.cli.build_module.initialize_config"),
            patch("sdb.cli.build_module.build_targets") as mock_build,
            patch("sdb.cli.build_module.BUILD_FUNCTIONS", {"doc": lambda: True}),
        ):
            mock_build.return_value = True
            code = _run_main(["build"])
            assert code == 0
            # The 'all' target expands to BUILD_FUNCTIONS keys
            mock_build.assert_called_once()

    def test_build_clean_exit_zero(self) -> None:
        """sdb build docs clean triggers clean_quarto_artifacts."""
        with (
            patch("sdb.cli.build_module.initialize_config"),
            patch("sdb.cli.build_module.clean_quarto_artifacts") as mock_clean,
        ):
            mock_clean.return_value = True
            code = _run_main(["build", "docs", "clean"])
            assert code == 0
            mock_clean.assert_called_once()

    def test_build_clean_exit_one(self) -> None:
        """When clean fails, exit code is 1."""
        with (
            patch("sdb.cli.build_module.initialize_config"),
            patch("sdb.cli.build_module.clean_quarto_artifacts") as mock_clean,
        ):
            mock_clean.return_value = False
            code = _run_main(["build", "docs", "clean"])
            assert code == 1


class TestCheckCommand:
    """Tests for the ``sdb check`` subcommand."""

    def test_check_validate_only(self) -> None:
        """sdb check . --validate-only -> command='check', validate_only=True."""
        with patch("sdb.check.run_check") as mock_run_check:
            mock_run_check.return_value = True
            code = _run_main(["check", ".", "--validate-only"])
            assert code == 0
            mock_run_check.assert_called_once()

    def test_check_defaults(self) -> None:
        """sdb check -> docs_root=Path('.'), validate_only=False, cleanup_uncited=False."""
        with patch("sdb.check.run_check") as mock_run_check:
            mock_run_check.return_value = True
            code = _run_main(["check"])
            assert code == 0
            mock_run_check.assert_called_once_with(
                docs_root=Path(".").resolve(),
                validate_only=False,
                cleanup_uncited=False,
            )


class TestResolveCommand:
    """Tests for the ``sdb resolve`` subcommand."""

    def test_resolve_check_only(self) -> None:
        """sdb resolve . --check-only triggers check_only=True."""
        with patch("sdb.resolve.resolve_all") as mock_resolve_all:
            mock_resolve_all.return_value = True
            code = _run_main(["resolve", ".", "--check-only"])
            assert code == 0
            mock_resolve_all.assert_called_once()


class TestInvalidCommand:
    """When no valid command is provided, argparse should exit."""

    def test_no_command(self) -> None:
        """Running sdb with no subcommand should exit non-zero."""
        code = _run_main([])
        assert code != 0

    def test_unknown_command(self) -> None:
        """Running sdb with an unrecognised command should exit non-zero."""
        code = _run_main(["nonexistent"])
        assert code != 0

