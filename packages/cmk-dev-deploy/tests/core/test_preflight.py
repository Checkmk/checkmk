# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Unit tests for cmk.dev_deploy.preflight (Bazel environment validation)."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from cmk.dev_deploy.core.preflight import (
    _bazel_info_check,
    _output_base_healthy,
    preflight_bazel_check,
    PreflightWarning,
)


class TestBazelInfoCheck:
    """Tests for bazel info health check — three branches."""

    def test_returns_ok_on_success(self, tmp_path: Path) -> None:
        with patch(
            "cmk.dev_deploy.core.preflight.subprocess.run",
            return_value=MagicMock(returncode=0),
        ):
            assert _bazel_info_check(tmp_path) == "ok"

    def test_returns_timeout_on_cold_server(self, tmp_path: Path) -> None:
        with patch(
            "cmk.dev_deploy.core.preflight.subprocess.run",
            side_effect=subprocess.TimeoutExpired(["bazel"], 3),
        ):
            assert _bazel_info_check(tmp_path) == "timeout"

    def test_returns_error_on_failure(self, tmp_path: Path) -> None:
        with patch(
            "cmk.dev_deploy.core.preflight.subprocess.run",
            return_value=MagicMock(returncode=1),
        ):
            assert _bazel_info_check(tmp_path) == "error"

    def test_returns_error_on_oserror(self, tmp_path: Path) -> None:
        """bazel not installed -> OSError -> 'error'."""
        with patch(
            "cmk.dev_deploy.core.preflight.subprocess.run",
            side_effect=OSError("No such file"),
        ):
            assert _bazel_info_check(tmp_path) == "error"


# ---------------------------------------------------------------------------
# T12: _output_base_healthy
# ---------------------------------------------------------------------------


class TestOutputBaseHealthy:
    """Tests for output base health check."""

    def test_healthy_output_base(self, tmp_path: Path) -> None:
        with patch(
            "cmk.dev_deploy.core.preflight.subprocess.run",
            return_value=MagicMock(returncode=0, stdout=str(tmp_path) + "\n"),
        ):
            assert _output_base_healthy(tmp_path) is None

    def test_nonexistent_output_base(self, tmp_path: Path) -> None:
        missing = tmp_path / "nonexistent"
        with patch(
            "cmk.dev_deploy.core.preflight.subprocess.run",
            return_value=MagicMock(returncode=0, stdout=str(missing) + "\n"),
        ):
            result = _output_base_healthy(tmp_path)
        assert result is not None
        assert "does not exist" in result

    def test_unwritable_output_base(self, tmp_path: Path) -> None:
        """Output base exists but cannot write to it."""
        read_only = tmp_path / "readonly"
        read_only.mkdir()

        def _mock_run(_cmd: list[str], **_kwargs: object) -> MagicMock:
            return MagicMock(returncode=0, stdout=str(read_only) + "\n")

        with patch("cmk.dev_deploy.core.preflight.subprocess.run", side_effect=_mock_run):
            # Make the health check file write fail
            with patch.object(Path, "write_text", side_effect=OSError("Read-only")):
                result = _output_base_healthy(tmp_path)
        assert result is not None
        assert "not writable" in result

    def test_bazel_info_fails(self, tmp_path: Path) -> None:
        with patch(
            "cmk.dev_deploy.core.preflight.subprocess.run",
            return_value=MagicMock(returncode=1, stderr="error\n"),
        ):
            result = _output_base_healthy(tmp_path)
        assert result is not None
        assert "failed" in result

    def test_timeout_returns_none(self, tmp_path: Path) -> None:
        """Timeout in output_base check is non-fatal (already caught earlier)."""
        with patch(
            "cmk.dev_deploy.core.preflight.subprocess.run",
            side_effect=subprocess.TimeoutExpired(["bazel"], 3),
        ):
            assert _output_base_healthy(tmp_path) is None


# ---------------------------------------------------------------------------
# T13: PreflightWarning dataclass
# ---------------------------------------------------------------------------


class TestPreflightWarning:
    """Tests for the PreflightWarning dataclass."""

    def test_defaults(self) -> None:
        w = PreflightWarning(message="test")
        assert w.message == "test"
        assert w.detail == ""
        assert w.recovery == ""
        assert w.blocking is False

    def test_blocking_warning(self) -> None:
        w = PreflightWarning(message="broken", blocking=True, recovery="fix it")
        assert w.blocking is True
        assert w.recovery == "fix it"

    def test_frozen(self) -> None:
        """PreflightWarning should be immutable."""
        w = PreflightWarning(message="test")
        try:
            w.message = "changed"  # type: ignore[misc]
            assert False, "Should have raised FrozenInstanceError"
        except AttributeError:
            pass


# ---------------------------------------------------------------------------
# Integration: preflight_bazel_check
# ---------------------------------------------------------------------------


class TestPreflightBazelCheck:
    """Integration tests for the full preflight check flow."""

    def test_all_ok(self, tmp_path: Path) -> None:
        """Clean environment returns no warnings."""
        with patch(
            "cmk.dev_deploy.core.preflight.subprocess.run",
            return_value=MagicMock(returncode=0, stdout=str(tmp_path) + "\n"),
        ):
            warnings = preflight_bazel_check(tmp_path)
        assert len(warnings) == 0

    def test_timeout_skips_remaining(self, tmp_path: Path) -> None:
        """Cold server timeout returns early, skipping output_base check."""
        with patch(
            "cmk.dev_deploy.core.preflight.subprocess.run",
            side_effect=subprocess.TimeoutExpired(["bazel"], 3),
        ):
            warnings = preflight_bazel_check(tmp_path)
        # No blocking warnings — timeout is non-blocking
        assert all(not w.blocking for w in warnings)

    def test_broken_bazel_is_blocking(self, tmp_path: Path) -> None:
        """Broken Bazel installation produces a blocking warning."""

        def _side_effect(cmd: list[str], **_kwargs: object) -> MagicMock:
            if cmd == ["bazel", "info"]:
                return MagicMock(returncode=1)
            return MagicMock(returncode=0, stdout=str(tmp_path) + "\n")

        with patch("cmk.dev_deploy.core.preflight.subprocess.run", side_effect=_side_effect):
            warnings = preflight_bazel_check(tmp_path)
        blocking = [w for w in warnings if w.blocking]
        assert len(blocking) == 1
        assert "broken" in blocking[0].message.lower()
