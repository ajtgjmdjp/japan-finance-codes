"""Tests for CLI commands (info, verify, --version, unknown)."""

from __future__ import annotations

import sys
from unittest.mock import patch

import pytest

from japan_finance_codes._cli import cli


class TestCLIInfo:
    def test_info_shows_metadata(self, capsys: pytest.CaptureFixture[str]) -> None:
        with patch.object(sys, "argv", ["japan-finance-codes", "info"]):
            cli()
        out = capsys.readouterr().out
        assert "Records:" in out
        assert "Generated at:" in out
        assert "Integrity:" in out


class TestCLIVerify:
    def test_verify_ok(self, capsys: pytest.CaptureFixture[str]) -> None:
        with patch.object(sys, "argv", ["japan-finance-codes", "verify"]):
            cli()
        out = capsys.readouterr().out
        assert "OK" in out


class TestCLIVersion:
    def test_version(self, capsys: pytest.CaptureFixture[str]) -> None:
        with patch.object(sys, "argv", ["japan-finance-codes", "--version"]):
            cli()
        out = capsys.readouterr().out
        assert "japan-finance-codes" in out
        assert "0.2.0" in out


class TestCLIHelp:
    def test_help(self, capsys: pytest.CaptureFixture[str]) -> None:
        with patch.object(sys, "argv", ["japan-finance-codes", "--help"]):
            cli()
        out = capsys.readouterr().out
        assert "info" in out
        assert "verify" in out
        assert "refresh" in out


class TestCLIUnknown:
    def test_unknown_command_exits_nonzero(self) -> None:
        with patch.object(sys, "argv", ["japan-finance-codes", "invalid"]):
            with pytest.raises(SystemExit) as exc_info:
                cli()
            assert exc_info.value.code == 1


class TestCLIRefreshWithoutEdinet:
    def test_refresh_without_edinet_exits(self) -> None:
        """refresh without edinet-mcp installed should exit with error."""
        with (
            patch.object(sys, "argv", ["japan-finance-codes", "refresh"]),
            patch.dict(sys.modules, {"edinet_mcp": None}),
        ):
            with pytest.raises(SystemExit) as exc_info:
                cli()
            assert exc_info.value.code == 1
