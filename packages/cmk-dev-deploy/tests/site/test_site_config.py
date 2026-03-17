# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Unit tests for cmk.dev_deploy.site_config module.

Comprehensive coverage of side-channel .mk file management: path construction,
site running check, stale override detection, write/remove operations.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from cmk.dev_deploy.site.privilege import SSHState
from cmk.dev_deploy.site.site_config import (
    _MK_CONTENT,
    _mk_file_exists,
    check_site_running,
    is_stale_override,
    override_mk_path,
    remove_override,
    write_override,
)

# ---------------------------------------------------------------------------
# TestOverrideMkPath
# ---------------------------------------------------------------------------


class TestOverrideMkPath:
    """override_mk_path returns the correct zzz_dev_inject.mk path."""

    def test_returns_correct_path(self) -> None:
        site_root = Path("/omd/sites/mysite")
        result = override_mk_path(site_root)
        assert result == Path(
            "/omd/sites/mysite/etc/check_mk/multisite.d/zzz_dev_inject.mk"
        )

    def test_zzz_prefix_sorts_after_wato(self) -> None:
        """zzz_ prefix sorts lexicographically after wato (z > w)."""
        result = override_mk_path(Path("/omd/sites/test"))
        assert result.name > "wato"

    def test_filename_ends_with_mk(self) -> None:
        result = override_mk_path(Path("/omd/sites/test"))
        assert result.suffix == ".mk"


# ---------------------------------------------------------------------------
# TestMkContent
# ---------------------------------------------------------------------------


class TestMkContent:
    """_MK_CONTENT is valid Python containing the inject assignment."""

    def test_contains_inject_assignment(self) -> None:
        assert 'load_frontend_vue = "inject"' in _MK_CONTENT

    def test_contains_header_comment(self) -> None:
        assert _MK_CONTENT.startswith("#")

    def test_is_valid_python(self) -> None:
        """_MK_CONTENT can be compiled and executed without error."""
        exec(compile(_MK_CONTENT, "<test>", "exec"), {})  # nosec B102


# ---------------------------------------------------------------------------
# TestCheckSiteRunning
# ---------------------------------------------------------------------------


class TestCheckSiteRunning:
    """check_site_running delegates to run_as_site_user."""

    def test_running_site_returns_true(self) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 0
        with patch(
            "cmk.dev_deploy.site.site_config.run_as_site_user", return_value=mock_result
        ):
            assert check_site_running("v260", SSHState()) is True

    def test_stopped_site_returns_false(self) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 1
        with patch(
            "cmk.dev_deploy.site.site_config.run_as_site_user", return_value=mock_result
        ):
            assert check_site_running("v260", SSHState()) is False

    def test_exception_returns_false(self) -> None:
        with patch(
            "cmk.dev_deploy.site.site_config.run_as_site_user",
            side_effect=Exception("connection failed"),
        ):
            assert check_site_running("v260", SSHState()) is False

    def test_calls_omd_status(self) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 0
        with patch(
            "cmk.dev_deploy.site.site_config.run_as_site_user", return_value=mock_result
        ) as mock_run:
            state = SSHState()
            check_site_running("v260", state)
            mock_run.assert_called_once_with("v260", "omd status", state, timeout=10)


# ---------------------------------------------------------------------------
# TestIsStaleOverride
# ---------------------------------------------------------------------------


class TestMkFileExists:
    """_mk_file_exists falls back to site-user access on PermissionError."""

    def test_direct_access_succeeds(self, tmp_path: Path) -> None:
        """Direct stat works when file exists and is accessible."""
        mk_path = tmp_path / "zzz_dev_inject.mk"
        mk_path.write_text("override")
        assert _mk_file_exists(mk_path, "v260", SSHState()) is True

    def test_direct_access_file_missing(self, tmp_path: Path) -> None:
        """Direct stat returns False when file does not exist."""
        mk_path = tmp_path / "zzz_dev_inject.mk"
        assert _mk_file_exists(mk_path, "v260", SSHState()) is False

    def test_permission_error_falls_back_to_site_user(self) -> None:
        """Falls back to run_as_site_user when direct stat raises PermissionError."""
        mk_path = MagicMock(spec=Path)
        mk_path.exists.side_effect = PermissionError("EACCES")

        mock_result = MagicMock()
        mock_result.returncode = 0
        with patch(
            "cmk.dev_deploy.site.site_config.run_as_site_user",
            return_value=mock_result,
        ) as mock_run:
            assert _mk_file_exists(mk_path, "v260", SSHState()) is True
            mock_run.assert_called_once()

    def test_permission_error_fallback_file_missing(self) -> None:
        """Fallback reports False when site-user test -f fails."""
        mk_path = MagicMock(spec=Path)
        mk_path.exists.side_effect = PermissionError("EACCES")

        mock_result = MagicMock()
        mock_result.returncode = 1
        with patch(
            "cmk.dev_deploy.site.site_config.run_as_site_user",
            return_value=mock_result,
        ):
            assert _mk_file_exists(mk_path, "v260", SSHState()) is False

    def test_permission_error_fallback_exception(self) -> None:
        """Returns False when both direct stat and fallback fail."""
        mk_path = MagicMock(spec=Path)
        mk_path.exists.side_effect = PermissionError("EACCES")

        with patch(
            "cmk.dev_deploy.site.site_config.run_as_site_user",
            side_effect=Exception("ssh failed"),
        ):
            assert _mk_file_exists(mk_path, "v260", SSHState()) is False


class TestIsStaleOverride:
    """is_stale_override covers all branches of stale detection."""

    def test_no_mk_file_not_stale(self, tmp_path: Path) -> None:
        """No .mk file means nothing to clean up."""
        mk_path = tmp_path / "zzz_dev_inject.mk"
        pid_file = tmp_path / "ibazel.pid"
        # Neither file exists
        assert is_stale_override(mk_path, pid_file, "v260", SSHState()) is False

    def test_mk_exists_no_pid_file_is_stale(self, tmp_path: Path) -> None:
        """Override exists but no PID file -> stale."""
        mk_path = tmp_path / "zzz_dev_inject.mk"
        mk_path.write_text("override")
        pid_file = tmp_path / "ibazel.pid"
        # pid_file does not exist
        assert is_stale_override(mk_path, pid_file, "v260", SSHState()) is True

    def test_mk_exists_dead_pid_is_stale(self, tmp_path: Path) -> None:
        """Override exists, PID file has valid PID, but process is dead."""
        mk_path = tmp_path / "zzz_dev_inject.mk"
        mk_path.write_text("override")
        pid_file = tmp_path / "ibazel.pid"
        pid_file.write_text("12345")
        with patch(
            "cmk.dev_deploy.site.site_config.os.kill", side_effect=ProcessLookupError
        ):
            assert is_stale_override(mk_path, pid_file, "v260", SSHState()) is True

    def test_mk_exists_alive_pid_not_stale(self, tmp_path: Path) -> None:
        """Override exists, PID file has valid PID, process is alive."""
        mk_path = tmp_path / "zzz_dev_inject.mk"
        mk_path.write_text("override")
        pid_file = tmp_path / "ibazel.pid"
        pid_file.write_text("12345")
        with patch("cmk.dev_deploy.site.site_config.os.kill"):
            # os.kill(12345, 0) succeeds (no exception) -> alive
            assert is_stale_override(mk_path, pid_file, "v260", SSHState()) is False

    def test_mk_exists_invalid_pid_is_stale(self, tmp_path: Path) -> None:
        """PID file contains non-numeric content -> stale (ValueError)."""
        mk_path = tmp_path / "zzz_dev_inject.mk"
        mk_path.write_text("override")
        pid_file = tmp_path / "ibazel.pid"
        pid_file.write_text("not-a-number")
        assert is_stale_override(mk_path, pid_file, "v260", SSHState()) is True

    def test_mk_exists_pid_read_error_is_stale(self, tmp_path: Path) -> None:
        """PID file read raises OSError -> stale."""
        mk_path = tmp_path / "zzz_dev_inject.mk"
        mk_path.write_text("override")
        pid_file = MagicMock()
        pid_file.exists.return_value = True
        pid_file.read_text.side_effect = OSError("permission denied")
        assert is_stale_override(mk_path, pid_file, "v260", SSHState()) is True

    def test_permission_error_on_mk_path_falls_back(self) -> None:
        """PermissionError on mk_path.exists() falls back to site-user check."""
        mk_path = MagicMock(spec=Path)
        mk_path.exists.side_effect = PermissionError("EACCES")

        # Fallback says file exists
        mock_result = MagicMock()
        mock_result.returncode = 0
        pid_file = MagicMock()
        pid_file.exists.return_value = False  # No PID file -> stale

        with patch(
            "cmk.dev_deploy.site.site_config.run_as_site_user",
            return_value=mock_result,
        ):
            assert is_stale_override(mk_path, pid_file, "v260", SSHState()) is True


# ---------------------------------------------------------------------------
# TestWriteOverride
# ---------------------------------------------------------------------------


class TestWriteOverride:
    """write_override writes the .mk file, preferring direct I/O."""

    def test_direct_write_success(self, tmp_path: Path) -> None:
        mk_path = tmp_path / "multisite.d" / "zzz_dev_inject.mk"
        assert write_override("v260", mk_path, SSHState()) is True
        assert mk_path.exists()
        assert "load_frontend_vue" in mk_path.read_text()

    def test_file_is_world_readable(self, tmp_path: Path) -> None:
        """File must be readable by site user's Apache process."""
        mk_path = tmp_path / "zzz_dev_inject.mk"
        write_override("v260", mk_path, SSHState())
        mode = mk_path.stat().st_mode & 0o777
        assert mode == 0o644

    def test_fallback_on_permission_error(self) -> None:
        """Falls back to run_as_site_user if direct write fails."""
        mk_path = MagicMock(spec=Path)
        mk_path.parent = MagicMock(spec=Path)
        mk_path.parent.mkdir.side_effect = OSError("permission denied")

        mock_result = MagicMock()
        mock_result.returncode = 0
        with patch(
            "cmk.dev_deploy.site.site_config.run_as_site_user",
            return_value=mock_result,
        ) as mock_run:
            assert write_override("v260", mk_path, SSHState()) is True
            mock_run.assert_called_once()

    def test_total_failure_returns_false(self) -> None:
        """Returns False if both direct and fallback fail."""
        mk_path = MagicMock(spec=Path)
        mk_path.parent = MagicMock(spec=Path)
        mk_path.parent.mkdir.side_effect = OSError("permission denied")

        with patch(
            "cmk.dev_deploy.site.site_config.run_as_site_user",
            side_effect=Exception("failed"),
        ):
            assert write_override("v260", mk_path, SSHState()) is False


# ---------------------------------------------------------------------------
# TestRemoveOverride
# ---------------------------------------------------------------------------


class TestRemoveOverride:
    """remove_override removes the .mk file, preferring direct I/O."""

    def test_direct_remove_success(self, tmp_path: Path) -> None:
        mk_path = tmp_path / "zzz_dev_inject.mk"
        mk_path.write_text("override")
        assert remove_override("v260", mk_path, SSHState()) is True
        assert not mk_path.exists()

    def test_remove_nonexistent_is_success(self, tmp_path: Path) -> None:
        """Removing a file that doesn't exist is idempotent success."""
        mk_path = tmp_path / "zzz_dev_inject.mk"
        assert remove_override("v260", mk_path, SSHState()) is True

    def test_fallback_on_permission_error(self) -> None:
        """Falls back to run_as_site_user if direct unlink fails."""
        mk_path = MagicMock(spec=Path)
        mk_path.unlink.side_effect = OSError("permission denied")

        mock_result = MagicMock()
        mock_result.returncode = 0
        with patch(
            "cmk.dev_deploy.site.site_config.run_as_site_user",
            return_value=mock_result,
        ) as mock_run:
            assert remove_override("v260", mk_path, SSHState()) is True
            mock_run.assert_called_once()

    def test_total_failure_returns_false(self) -> None:
        """Returns False if both direct and fallback fail."""
        mk_path = MagicMock(spec=Path)
        mk_path.unlink.side_effect = OSError("permission denied")

        with patch(
            "cmk.dev_deploy.site.site_config.run_as_site_user",
            side_effect=Exception("failed"),
        ):
            assert remove_override("v260", mk_path, SSHState()) is False
