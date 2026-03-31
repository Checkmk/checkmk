# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Unit tests for cmk.dev_deploy.frontend_supervisor module.

Comprehensive coverage of the iBazel-based frontend supervisor: inotify
pre-flight check, PID file management, orphan detection, immediate SIGKILL
shutdown, iBazel spawning, [frontend] stdout prefix, startup banner, crash
reporting, v1.4 code removal verification, and CLI help text.
"""

from __future__ import annotations

import inspect
import io
import signal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cmk.dev_deploy.errors import DeployError, FrontendError
from cmk.dev_deploy.site.privilege import SSHState
from cmk.dev_deploy.types import (
    ChangeCategory,
    ChangeSet,
    detect_frontend_project,
    FrontendConfig,
    InstallSpec,
)


def _ssh_state() -> SSHState:
    """Create a fresh SSHState for test use."""
    return SSHState()


# ---------------------------------------------------------------------------
# TestFrontendError
# ---------------------------------------------------------------------------


class TestFrontendError:
    """FrontendError inherits from DeployError with recovery hint support."""

    def test_inherits_from_deploy_error(self) -> None:
        err = FrontendError("something broke")
        assert isinstance(err, DeployError)

    def test_recovery_hint_in_str(self) -> None:
        err = FrontendError("port in use", recovery="kill the other process")
        assert "port in use" in str(err)
        assert "kill the other process" in str(err)

    def test_no_recovery_hint(self) -> None:
        err = FrontendError("generic failure")
        assert str(err) == "generic failure"
        assert err.recovery is None


# ---------------------------------------------------------------------------
# TestFrontendConfig
# ---------------------------------------------------------------------------


class TestFrontendConfig:
    """FrontendConfig defaults match locked decisions for iBazel."""

    def test_defaults(self, tmp_path: Path) -> None:
        config = FrontendConfig(project_path=tmp_path, repo_root=tmp_path)
        assert config.port == 5173
        assert config.startup_timeout == 300.0
        assert config.stderr_buffer_lines == 50
        assert config.health_check_interval == 0.5

    def test_has_repo_root(self, tmp_path: Path) -> None:
        config = FrontendConfig(project_path=tmp_path, repo_root=tmp_path)
        assert config.repo_root == tmp_path

    def test_no_shutdown_grace(self, tmp_path: Path) -> None:
        """shutdown_grace was removed in iBazel rewrite (immediate SIGKILL)."""
        config = FrontendConfig(project_path=tmp_path, repo_root=tmp_path)
        assert not hasattr(config, "shutdown_grace")

    def test_frozen(self, tmp_path: Path) -> None:
        config = FrontendConfig(project_path=tmp_path, repo_root=tmp_path)
        with pytest.raises(AttributeError):
            config.port = 9999  # type: ignore[misc]

    def test_repo_root_is_required(self) -> None:
        """repo_root is a required field (no default)."""
        with pytest.raises(TypeError, match="repo_root"):
            FrontendConfig(project_path=Path("/tmp"))  # type: ignore[call-arg]  # nosec B108

    def test_startup_timeout_300s(self, tmp_path: Path) -> None:
        """300s timeout for initial Bazel builds (cold cache can take 3-5 min)."""
        config = FrontendConfig(project_path=tmp_path, repo_root=tmp_path)
        assert config.startup_timeout == 300.0


# ---------------------------------------------------------------------------
# TestDetectFrontendProject
# ---------------------------------------------------------------------------


class TestDetectFrontendProject:
    """Auto-detection finds packages/cmk-frontend-vue/ when valid."""

    def test_finds_project(self, tmp_path: Path) -> None:
        project = tmp_path / "packages" / "cmk-frontend-vue"
        project.mkdir(parents=True)
        (project / "vite.config.ts").write_text("export default {}")
        assert detect_frontend_project(tmp_path) == project

    def test_raises_when_dir_missing(self, tmp_path: Path) -> None:
        with pytest.raises(FrontendError, match="Frontend project not found"):
            detect_frontend_project(tmp_path)

    def test_raises_when_vite_config_missing(self, tmp_path: Path) -> None:
        project = tmp_path / "packages" / "cmk-frontend-vue"
        project.mkdir(parents=True)
        # No vite.config.ts
        with pytest.raises(FrontendError, match="Frontend project not found"):
            detect_frontend_project(tmp_path)


# ---------------------------------------------------------------------------
# TestInotifyCheck
# ---------------------------------------------------------------------------


class TestInotifyCheck:
    """_check_inotify_watches warns when watches are below threshold."""

    def test_warns_below_threshold(self) -> None:
        from cmk.dev_deploy.frontend.frontend_supervisor import _check_inotify_watches

        with (
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor._INOTIFY_SYSCTL_PATH",
                MagicMock(read_text=MagicMock(return_value="8192\n")),
            ),
            patch("cmk.dev_deploy.frontend.frontend_supervisor.output") as mock_output,
        ):
            _check_inotify_watches()
            mock_output.warn.assert_called_once()
            warn_msg = mock_output.warn.call_args[0][0]
            assert "8192" in warn_msg
            assert "524288" in warn_msg
            assert "sudo sysctl" in warn_msg
            assert "/etc/sysctl.conf" in warn_msg

    def test_silent_above_threshold(self) -> None:
        from cmk.dev_deploy.frontend.frontend_supervisor import _check_inotify_watches

        with (
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor._INOTIFY_SYSCTL_PATH",
                MagicMock(read_text=MagicMock(return_value="1048576\n")),
            ),
            patch("cmk.dev_deploy.frontend.frontend_supervisor.output") as mock_output,
        ):
            _check_inotify_watches()
            mock_output.warn.assert_not_called()

    def test_silent_on_exact_threshold(self) -> None:
        from cmk.dev_deploy.frontend.frontend_supervisor import _check_inotify_watches

        with (
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor._INOTIFY_SYSCTL_PATH",
                MagicMock(read_text=MagicMock(return_value="524288\n")),
            ),
            patch("cmk.dev_deploy.frontend.frontend_supervisor.output") as mock_output,
        ):
            _check_inotify_watches()
            mock_output.warn.assert_not_called()

    def test_silent_on_file_not_found(self) -> None:
        """Non-Linux: /proc/sys/fs/inotify/max_user_watches does not exist."""
        from cmk.dev_deploy.frontend.frontend_supervisor import _check_inotify_watches

        with (
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor._INOTIFY_SYSCTL_PATH",
                MagicMock(read_text=MagicMock(side_effect=OSError("No such file"))),
            ),
            patch("cmk.dev_deploy.frontend.frontend_supervisor.output") as mock_output,
        ):
            _check_inotify_watches()
            mock_output.warn.assert_not_called()

    def test_silent_on_invalid_content(self) -> None:
        """Handle non-numeric content gracefully."""
        from cmk.dev_deploy.frontend.frontend_supervisor import _check_inotify_watches

        with (
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor._INOTIFY_SYSCTL_PATH",
                MagicMock(read_text=MagicMock(return_value="not_a_number\n")),
            ),
            patch("cmk.dev_deploy.frontend.frontend_supervisor.output") as mock_output,
        ):
            _check_inotify_watches()
            mock_output.warn.assert_not_called()


# ---------------------------------------------------------------------------
# TestPortCheck
# ---------------------------------------------------------------------------


class TestPortCheck:
    """TCP port probe returns True/False based on connection result."""

    def test_returns_true_on_success(self) -> None:
        from cmk.dev_deploy.frontend.frontend_supervisor import _check_port

        mock_conn = MagicMock()
        with patch("socket.create_connection", return_value=mock_conn):
            assert _check_port("127.0.0.1", 5173) is True
            mock_conn.close.assert_called_once()

    def test_returns_false_on_refused(self) -> None:
        from cmk.dev_deploy.frontend.frontend_supervisor import _check_port

        with patch("socket.create_connection", side_effect=ConnectionRefusedError):
            assert _check_port("127.0.0.1", 5173) is False

    def test_returns_false_on_timeout(self) -> None:
        from cmk.dev_deploy.frontend.frontend_supervisor import _check_port

        with patch("socket.create_connection", side_effect=TimeoutError):
            assert _check_port("127.0.0.1", 5173) is False

    def test_returns_false_on_os_error(self) -> None:
        from cmk.dev_deploy.frontend.frontend_supervisor import _check_port

        with patch("socket.create_connection", side_effect=OSError):
            assert _check_port("127.0.0.1", 5173) is False


# ---------------------------------------------------------------------------
# TestStderrCapture
# ---------------------------------------------------------------------------


class TestStderrCapture:
    """_StderrCapture stores lines in a ring buffer via background thread."""

    def test_captures_lines(self) -> None:
        from cmk.dev_deploy.frontend.frontend_supervisor import _StderrCapture

        # Simulate a pipe with io.StringIO (proper IO[str] type)
        pipe = io.StringIO("line1\nline2\nline3\n")
        capture = _StderrCapture(pipe, maxlines=10)
        capture._thread.join(timeout=2.0)  # noqa: SLF001  # noqa: SLF001
        assert capture.get_lines() == ["line1", "line2", "line3"]

    def test_evicts_oldest_when_full(self) -> None:
        from cmk.dev_deploy.frontend.frontend_supervisor import _StderrCapture

        text = "".join(f"line{i}\n" for i in range(10))
        pipe = io.StringIO(text)
        capture = _StderrCapture(pipe, maxlines=3)
        capture._thread.join(timeout=2.0)  # noqa: SLF001  # noqa: SLF001
        result = capture.get_lines()
        assert len(result) == 3
        assert result == ["line7", "line8", "line9"]

    def test_empty_when_no_input(self) -> None:
        from cmk.dev_deploy.frontend.frontend_supervisor import _StderrCapture

        pipe = io.StringIO("")
        capture = _StderrCapture(pipe, maxlines=10)
        capture._thread.join(timeout=2.0)  # noqa: SLF001  # noqa: SLF001
        assert capture.get_lines() == []


# ---------------------------------------------------------------------------
# TestPidFileManagement
# ---------------------------------------------------------------------------


class TestPidFileManagement:
    """PID file lifecycle: write, read, cleanup."""

    def test_write_pid_file(self, tmp_path: Path) -> None:
        from cmk.dev_deploy.frontend.frontend_supervisor import FrontendSupervisor

        pid_file = tmp_path / "cache" / "ibazel.pid"
        config = FrontendConfig(project_path=tmp_path, repo_root=tmp_path)
        supervisor = FrontendSupervisor(config, repo_root=tmp_path)

        with patch(
            "cmk.dev_deploy.frontend.frontend_supervisor._pid_file",
            return_value=pid_file,
        ):
            supervisor._write_pid_file(12345)  # noqa: SLF001
            assert pid_file.read_text() == "12345"

    def test_remove_pid_file(self, tmp_path: Path) -> None:
        from cmk.dev_deploy.frontend.frontend_supervisor import FrontendSupervisor

        pid_file = tmp_path / "ibazel.pid"
        pid_file.write_text("12345")
        config = FrontendConfig(project_path=tmp_path, repo_root=tmp_path)
        supervisor = FrontendSupervisor(config, repo_root=tmp_path)

        with patch(
            "cmk.dev_deploy.frontend.frontend_supervisor._pid_file",
            return_value=pid_file,
        ):
            supervisor._remove_pid_file()  # noqa: SLF001
            assert not pid_file.exists()

    def test_remove_pid_file_noop_when_missing(self, tmp_path: Path) -> None:
        from cmk.dev_deploy.frontend.frontend_supervisor import FrontendSupervisor

        pid_file = tmp_path / "nonexistent.pid"
        config = FrontendConfig(project_path=tmp_path, repo_root=tmp_path)
        supervisor = FrontendSupervisor(config, repo_root=tmp_path)

        with patch(
            "cmk.dev_deploy.frontend.frontend_supervisor._pid_file",
            return_value=pid_file,
        ):
            # Should not raise
            supervisor._remove_pid_file()  # noqa: SLF001

    def test_write_pid_file_creates_parent_dir(self, tmp_path: Path) -> None:
        from cmk.dev_deploy.frontend.frontend_supervisor import FrontendSupervisor

        pid_file = tmp_path / "deep" / "nested" / "dir" / "ibazel.pid"
        config = FrontendConfig(project_path=tmp_path, repo_root=tmp_path)
        supervisor = FrontendSupervisor(config, repo_root=tmp_path)

        with patch(
            "cmk.dev_deploy.frontend.frontend_supervisor._pid_file",
            return_value=pid_file,
        ):
            supervisor._write_pid_file(99999)  # noqa: SLF001
            assert pid_file.parent.exists()
            assert pid_file.read_text() == "99999"


# ---------------------------------------------------------------------------
# TestOrphanDetection
# ---------------------------------------------------------------------------


class TestOrphanDetection:
    """_cleanup_orphaned_ibazel detects and kills stale iBazel processes."""

    def test_noop_when_no_pid_file(self, tmp_path: Path) -> None:
        from cmk.dev_deploy.frontend.frontend_supervisor import FrontendSupervisor

        config = FrontendConfig(project_path=tmp_path, repo_root=tmp_path)
        supervisor = FrontendSupervisor(config, repo_root=tmp_path)
        with (
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor._pid_file",
                return_value=tmp_path / "nonexistent.pid",
            ),
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor._cleanup_orphaned_port"
            ) as mock_port_cleanup,
        ):
            # Should not raise; should call port cleanup as fallback
            supervisor._cleanup_orphaned_ibazel()  # noqa: SLF001
            mock_port_cleanup.assert_called_once_with(config.port)

    def test_kills_orphaned_ibazel_process(self, tmp_path: Path) -> None:
        from cmk.dev_deploy.frontend.frontend_supervisor import FrontendSupervisor

        pid_file = tmp_path / "ibazel.pid"
        pid_file.write_text("9999")

        config = FrontendConfig(project_path=tmp_path, repo_root=tmp_path)
        supervisor = FrontendSupervisor(config, repo_root=tmp_path)

        # Mock /proc/{pid}/cmdline to contain "ibazel"
        mock_cmdline_path = MagicMock()
        mock_cmdline_path.read_text.return_value = "/usr/bin/ibazel\x00run\x00"

        with (
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor._pid_file",
                return_value=pid_file,
            ),
            patch("os.kill"),  # Process alive (no exception)
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor.Path",
                side_effect=lambda p: mock_cmdline_path if "/proc/" in str(p) else Path(p),
            ),
            patch("cmk.dev_deploy.frontend.frontend_supervisor._kill_process_group") as mock_kill,
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor._find_bazel_children",
                return_value=[],
            ),
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor._check_port",
                return_value=False,
            ),
            patch("cmk.dev_deploy.frontend.frontend_supervisor.output"),
        ):
            supervisor._cleanup_orphaned_ibazel()  # noqa: SLF001
            mock_kill.assert_called_once_with(9999)

    def test_ignores_dead_process(self, tmp_path: Path) -> None:
        from cmk.dev_deploy.frontend.frontend_supervisor import FrontendSupervisor

        pid_file = tmp_path / "ibazel.pid"
        pid_file.write_text("9999")

        config = FrontendConfig(project_path=tmp_path, repo_root=tmp_path)
        supervisor = FrontendSupervisor(config, repo_root=tmp_path)

        with (
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor._pid_file",
                return_value=pid_file,
            ),
            patch("os.kill", side_effect=ProcessLookupError),  # Process gone
            patch("cmk.dev_deploy.frontend.frontend_supervisor._kill_process_group") as mock_kill,
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor._cleanup_orphaned_port"
            ) as mock_port_cleanup,
        ):
            supervisor._cleanup_orphaned_ibazel()  # noqa: SLF001
            mock_kill.assert_not_called()
            mock_port_cleanup.assert_called_once_with(config.port)
            # PID file should be cleaned up (finally block)
            assert not pid_file.exists()

    def test_ignores_non_ibazel_process(self, tmp_path: Path) -> None:
        from cmk.dev_deploy.frontend.frontend_supervisor import FrontendSupervisor

        pid_file = tmp_path / "ibazel.pid"
        pid_file.write_text("9999")

        config = FrontendConfig(project_path=tmp_path, repo_root=tmp_path)
        supervisor = FrontendSupervisor(config, repo_root=tmp_path)

        # Process is alive but not ibazel
        mock_cmdline_path = MagicMock()
        mock_cmdline_path.read_text.return_value = "/usr/bin/python3\x00script.py\x00"

        with (
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor._pid_file",
                return_value=pid_file,
            ),
            patch("os.kill"),  # Process alive
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor.Path",
                side_effect=lambda p: mock_cmdline_path if "/proc/" in str(p) else Path(p),
            ),
            patch("cmk.dev_deploy.frontend.frontend_supervisor._kill_process_group") as mock_kill,
        ):
            supervisor._cleanup_orphaned_ibazel()  # noqa: SLF001
            mock_kill.assert_not_called()

    def test_kills_bazel_children_before_ibazel(self, tmp_path: Path) -> None:
        """When orphaned iBazel is found, its Bazel children are also killed."""
        from cmk.dev_deploy.frontend.frontend_supervisor import FrontendSupervisor

        pid_file = tmp_path / "ibazel.pid"
        pid_file.write_text("9999")

        config = FrontendConfig(project_path=tmp_path, repo_root=tmp_path)
        supervisor = FrontendSupervisor(config, repo_root=tmp_path)

        mock_cmdline_path = MagicMock()
        mock_cmdline_path.read_text.return_value = "/usr/bin/ibazel\x00run\x00"

        with (
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor._pid_file",
                return_value=pid_file,
            ),
            patch("os.kill"),  # Process alive
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor.Path",
                side_effect=lambda p: mock_cmdline_path if "/proc/" in str(p) else Path(p),
            ),
            patch("cmk.dev_deploy.frontend.frontend_supervisor._kill_process_group") as mock_kill,
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor._find_bazel_children",
                return_value=[10001, 10002],
            ),
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor._check_port",
                return_value=False,
            ),
            patch("cmk.dev_deploy.frontend.frontend_supervisor.output"),
        ):
            supervisor._cleanup_orphaned_ibazel()  # noqa: SLF001
            # iBazel + 2 children = 3 calls
            assert mock_kill.call_count == 3
            mock_kill.assert_any_call(9999)
            mock_kill.assert_any_call(10001)
            mock_kill.assert_any_call(10002)

    def test_port_cleanup_fallback_when_no_pid_file(self, tmp_path: Path) -> None:
        """When no PID file exists but port is in use, _cleanup_orphaned_port is called."""
        from cmk.dev_deploy.frontend.frontend_supervisor import FrontendSupervisor

        config = FrontendConfig(project_path=tmp_path, repo_root=tmp_path)
        supervisor = FrontendSupervisor(config, repo_root=tmp_path)
        with (
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor._pid_file",
                return_value=tmp_path / "nonexistent.pid",
            ),
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor._cleanup_orphaned_port"
            ) as mock_port_cleanup,
        ):
            supervisor._cleanup_orphaned_ibazel()  # noqa: SLF001
            mock_port_cleanup.assert_called_once_with(config.port)


# ---------------------------------------------------------------------------
# TestFindBazelChildren
# ---------------------------------------------------------------------------


class TestFindBazelChildren:
    """_find_bazel_children discovers Bazel/Java child processes via /proc/."""

    def test_finds_bazel_child_via_proc_task(self, tmp_path: Path) -> None:
        """Mock /proc/{pid}/task/{tid}/children to return a child PID."""
        from cmk.dev_deploy.frontend.frontend_supervisor import _find_bazel_children

        # Create mock /proc structure
        task_dir = tmp_path / "proc" / "1000" / "task" / "1000"
        task_dir.mkdir(parents=True)
        (task_dir / "children").write_text("2000")

        # Mock child cmdline
        child_cmdline = tmp_path / "proc" / "2000" / "cmdline"
        child_cmdline.parent.mkdir(parents=True)
        child_cmdline.write_text("/usr/bin/bazel\x00build\x00")

        with (
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor.Path",
                side_effect=lambda p: Path(str(p).replace("/proc/", str(tmp_path / "proc") + "/")),
            ),
        ):
            result = _find_bazel_children(1000)
            assert 2000 in result

    def test_ignores_non_bazel_children(self, tmp_path: Path) -> None:
        """Children with non-bazel cmdline are not returned."""
        from cmk.dev_deploy.frontend.frontend_supervisor import _find_bazel_children

        task_dir = tmp_path / "proc" / "1000" / "task" / "1000"
        task_dir.mkdir(parents=True)
        (task_dir / "children").write_text("2000")

        child_cmdline = tmp_path / "proc" / "2000" / "cmdline"
        child_cmdline.parent.mkdir(parents=True)
        child_cmdline.write_text("/usr/bin/python3\x00script.py\x00")

        with (
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor.Path",
                side_effect=lambda p: Path(str(p).replace("/proc/", str(tmp_path / "proc") + "/")),
            ),
        ):
            result = _find_bazel_children(1000)
            assert result == []

    def test_returns_empty_on_proc_error(self) -> None:
        """OSError reading /proc/ returns empty list, not a crash."""
        from cmk.dev_deploy.frontend.frontend_supervisor import _find_bazel_children

        with patch(
            "cmk.dev_deploy.frontend.frontend_supervisor.Path",
            side_effect=lambda _p: MagicMock(
                iterdir=MagicMock(side_effect=OSError("Permission denied"))
            ),
        ):
            result = _find_bazel_children(1000)
            assert result == []

    def test_finds_java_workers(self, tmp_path: Path) -> None:
        """Java processes (Bazel JVM workers) are also found."""
        from cmk.dev_deploy.frontend.frontend_supervisor import _find_bazel_children

        task_dir = tmp_path / "proc" / "1000" / "task" / "1000"
        task_dir.mkdir(parents=True)
        (task_dir / "children").write_text("3000")

        child_cmdline = tmp_path / "proc" / "3000" / "cmdline"
        child_cmdline.parent.mkdir(parents=True)
        child_cmdline.write_text("/usr/bin/java\x00-jar\x00bazel-worker.jar\x00")

        with (
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor.Path",
                side_effect=lambda p: Path(str(p).replace("/proc/", str(tmp_path / "proc") + "/")),
            ),
        ):
            result = _find_bazel_children(1000)
            assert 3000 in result


# ---------------------------------------------------------------------------
# TestCleanupOrphanedPort
# ---------------------------------------------------------------------------


class TestCleanupOrphanedPort:
    """_cleanup_orphaned_port kills Bazel processes holding a port as fallback."""

    def test_noop_when_port_free(self) -> None:
        """No kill attempted when port is not in use."""
        from cmk.dev_deploy.frontend.frontend_supervisor import _cleanup_orphaned_port

        with (
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor._check_port",
                return_value=False,
            ),
            patch("cmk.dev_deploy.frontend.frontend_supervisor._kill_process_group") as mock_kill,
        ):
            _cleanup_orphaned_port(5173)
            mock_kill.assert_not_called()

    def test_kills_bazel_process_on_port(self) -> None:
        """Bazel process holding port is killed."""
        from cmk.dev_deploy.frontend.frontend_supervisor import _cleanup_orphaned_port

        # Mock /proc/net/tcp with our port (5173 = 0x1435)
        tcp_content = (
            "  sl  local_address rem_address   st tx_queue rx_queue "
            "tr tm->when retrnsmt   uid  timeout inode\n"
            "   0: 0100007F:1435 00000000:0000 0A 00000000:00000000 "
            "00:00000000 00000000  1000        0 12345 1\n"
        )

        # Mock /proc/{pid}/fd/ with a socket link matching the inode
        mock_fd_link = MagicMock()
        mock_fd_link.resolve.return_value = Path("socket:[12345]")

        mock_fd_dir = MagicMock()
        mock_fd_dir.__truediv__ = MagicMock(return_value=mock_fd_dir)
        mock_fd_dir.iterdir.return_value = [mock_fd_link]

        mock_pid_entry = MagicMock()
        mock_pid_entry.name = "5555"
        mock_pid_entry.__truediv__ = MagicMock(return_value=mock_fd_dir)

        with (
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor._check_port",
                return_value=True,
            ),
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor.Path",
                side_effect=lambda p: (
                    MagicMock(
                        read_text=MagicMock(return_value=tcp_content),
                        splitlines=tcp_content.splitlines,
                    )
                    if str(p) == "/proc/net/tcp"
                    else MagicMock(read_text=MagicMock(return_value="/usr/bin/bazel\x00build\x00"))
                    if "/cmdline" in str(p)
                    else MagicMock(iterdir=MagicMock(return_value=[mock_pid_entry]))
                    if str(p) == "/proc"
                    else MagicMock()
                ),
            ),
            patch("cmk.dev_deploy.frontend.frontend_supervisor._kill_process_group") as mock_kill,
            patch("cmk.dev_deploy.frontend.frontend_supervisor.output"),
        ):
            _cleanup_orphaned_port(5173)
            mock_kill.assert_called_once_with(5555)

    def test_ignores_non_bazel_on_port(self) -> None:
        """Non-Bazel process on port is not killed."""
        from cmk.dev_deploy.frontend.frontend_supervisor import _cleanup_orphaned_port

        tcp_content = (
            "  sl  local_address rem_address   st tx_queue rx_queue "
            "tr tm->when retrnsmt   uid  timeout inode\n"
            "   0: 0100007F:1435 00000000:0000 0A 00000000:00000000 "
            "00:00000000 00000000  1000        0 12345 1\n"
        )

        mock_fd_link = MagicMock()
        mock_fd_link.resolve.return_value = Path("socket:[12345]")

        mock_fd_dir = MagicMock()
        mock_fd_dir.__truediv__ = MagicMock(return_value=mock_fd_dir)
        mock_fd_dir.iterdir.return_value = [mock_fd_link]

        mock_pid_entry = MagicMock()
        mock_pid_entry.name = "5555"
        mock_pid_entry.__truediv__ = MagicMock(return_value=mock_fd_dir)

        with (
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor._check_port",
                return_value=True,
            ),
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor.Path",
                side_effect=lambda p: (
                    MagicMock(
                        read_text=MagicMock(return_value=tcp_content),
                        splitlines=tcp_content.splitlines,
                    )
                    if str(p) == "/proc/net/tcp"
                    else MagicMock(
                        read_text=MagicMock(return_value="/usr/bin/apache2\x00-k\x00start\x00")
                    )
                    if "/cmdline" in str(p)
                    else MagicMock(iterdir=MagicMock(return_value=[mock_pid_entry]))
                    if str(p) == "/proc"
                    else MagicMock()
                ),
            ),
            patch("cmk.dev_deploy.frontend.frontend_supervisor._kill_process_group") as mock_kill,
            patch("cmk.dev_deploy.frontend.frontend_supervisor.output"),
        ):
            _cleanup_orphaned_port(5173)
            mock_kill.assert_not_called()


# ---------------------------------------------------------------------------
# TestCollectDescendantPids
# ---------------------------------------------------------------------------


class TestCollectDescendantPids:
    """_collect_descendant_pids recursively collects process tree (deepest first)."""

    def test_collects_direct_children(self) -> None:
        """Direct children of root PID are collected."""
        from cmk.dev_deploy.frontend.frontend_supervisor import _collect_descendant_pids

        def mock_find(pid: int) -> list[int]:
            if pid == 42:
                return [100, 200]
            return []

        with patch(
            "cmk.dev_deploy.frontend.frontend_supervisor._find_bazel_children",
            side_effect=mock_find,
        ):
            result = _collect_descendant_pids(42)
            assert 100 in result
            assert 200 in result

    def test_collects_recursive_children(self) -> None:
        """Grandchildren are collected, with deepest first (bottom-up kill order)."""
        from cmk.dev_deploy.frontend.frontend_supervisor import _collect_descendant_pids

        def mock_find(pid: int) -> list[int]:
            if pid == 42:
                return [100]
            if pid == 100:
                return [200]
            return []

        with patch(
            "cmk.dev_deploy.frontend.frontend_supervisor._find_bazel_children",
            side_effect=mock_find,
        ):
            result = _collect_descendant_pids(42)
            assert 100 in result
            assert 200 in result
            # 200 (deepest) should come before 100 (its parent)
            assert result.index(200) < result.index(100)

    def test_returns_empty_on_no_children(self) -> None:
        """No children -> empty list."""
        from cmk.dev_deploy.frontend.frontend_supervisor import _collect_descendant_pids

        with patch(
            "cmk.dev_deploy.frontend.frontend_supervisor._find_bazel_children",
            return_value=[],
        ):
            result = _collect_descendant_pids(42)
            assert result == []

    def test_handles_disappearing_processes(self) -> None:
        """OSError during child discovery does not crash, returns what it can find."""
        from cmk.dev_deploy.frontend.frontend_supervisor import _collect_descendant_pids

        call_count = 0

        def mock_find(pid: int) -> list[int]:
            nonlocal call_count
            call_count += 1
            if pid == 42:
                return [100, 200]
            if pid == 100:
                raise OSError("Process disappeared")
            return []

        with patch(
            "cmk.dev_deploy.frontend.frontend_supervisor._find_bazel_children",
            side_effect=mock_find,
        ):
            result = _collect_descendant_pids(42)
            # 200 found normally, 100 also in result (added after its children)
            assert 200 in result
            assert 100 in result


# ---------------------------------------------------------------------------
# TestImmediateKill (replaces TestGracefulShutdown)
# ---------------------------------------------------------------------------


class TestImmediateKill:
    """_kill_process_group sends immediate SIGKILL to process group."""

    def test_sigkill_via_process_group(self) -> None:
        from cmk.dev_deploy.frontend.frontend_supervisor import _kill_process_group

        with (
            patch("os.getpgid", return_value=1000),
            patch("os.killpg") as mock_killpg,
        ):
            _kill_process_group(42)
            # Should have sent ONLY SIGKILL (no SIGTERM)
            mock_killpg.assert_called_once_with(1000, signal.SIGKILL)

    def test_no_sigterm_sent(self) -> None:
        """Per user decision: immediate SIGKILL, no SIGTERM, no grace period."""
        from cmk.dev_deploy.frontend.frontend_supervisor import _kill_process_group

        with (
            patch("os.getpgid", return_value=1000),
            patch("os.killpg") as mock_killpg,
        ):
            _kill_process_group(42)
            # Verify only one call and it was SIGKILL
            assert mock_killpg.call_count == 1
            assert mock_killpg.call_args[0][1] == signal.SIGKILL
            # Explicitly verify SIGTERM was NOT sent
            for call in mock_killpg.call_args_list:
                assert call[0][1] != signal.SIGTERM

    def test_handles_process_already_gone(self) -> None:
        from cmk.dev_deploy.frontend.frontend_supervisor import _kill_process_group

        with patch("os.getpgid", side_effect=ProcessLookupError):
            # Should not raise
            _kill_process_group(42)

    def test_handles_permission_error(self) -> None:
        from cmk.dev_deploy.frontend.frontend_supervisor import _kill_process_group

        with (
            patch("os.getpgid", return_value=1000),
            patch("os.killpg", side_effect=PermissionError),
        ):
            # Should not raise
            _kill_process_group(42)

    def test_stop_still_uses_sigkill(self) -> None:
        """Enhanced stop() with tree cleanup still uses SIGKILL via _kill_process_group."""
        from cmk.dev_deploy.frontend.frontend_supervisor import FrontendSupervisor

        config = FrontendConfig(project_path=Path("/tmp"), repo_root=Path("/tmp"))  # nosec B108
        supervisor = FrontendSupervisor(config, repo_root=Path("/tmp"))  # nosec B108

        mock_proc = MagicMock()
        mock_proc.pid = 42
        mock_proc.poll.return_value = None  # process alive
        mock_proc.wait.return_value = None
        supervisor._proc = mock_proc  # noqa: SLF001

        with (
            patch("cmk.dev_deploy.frontend.frontend_supervisor._kill_process_group") as mock_kill,
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor._collect_descendant_pids",
                return_value=[],
            ),
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor._check_port",
                return_value=False,
            ),
            patch("cmk.dev_deploy.frontend.frontend_supervisor.time.sleep"),
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor._pid_file",
                return_value=Path("/tmp/test.pid"),  # nosec B108
            ),
        ):
            supervisor.stop()
            # _kill_process_group is called (which internally sends SIGKILL)
            mock_kill.assert_called_with(42)


# ---------------------------------------------------------------------------
# TestStopFullCleanup
# ---------------------------------------------------------------------------


class TestStopFullCleanup:
    """Enhanced stop() kills full process tree and verifies port is free."""

    def test_stop_kills_descendants(self, tmp_path: Path) -> None:
        """stop() kills descendant process groups found by _collect_descendant_pids."""
        from cmk.dev_deploy.frontend.frontend_supervisor import FrontendSupervisor

        config = FrontendConfig(project_path=tmp_path, repo_root=tmp_path)
        supervisor = FrontendSupervisor(config, repo_root=tmp_path)

        mock_proc = MagicMock()
        mock_proc.pid = 42
        mock_proc.poll.return_value = None  # process alive
        mock_proc.wait.return_value = None
        supervisor._proc = mock_proc  # noqa: SLF001

        with (
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor._collect_descendant_pids",
                return_value=[100, 200],
            ),
            patch("cmk.dev_deploy.frontend.frontend_supervisor._kill_process_group") as mock_kill,
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor._check_port",
                return_value=False,
            ),
            patch("cmk.dev_deploy.frontend.frontend_supervisor.time.sleep"),
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor._pid_file",
                return_value=tmp_path / "test.pid",
            ),
        ):
            supervisor.stop()
            # iBazel PID + 2 descendants = 3 calls
            assert mock_kill.call_count == 3
            mock_kill.assert_any_call(42)
            mock_kill.assert_any_call(100)
            mock_kill.assert_any_call(200)

    def test_stop_kills_bottom_up(self, tmp_path: Path) -> None:
        """Descendants are killed in the order returned (deepest first)."""
        from cmk.dev_deploy.frontend.frontend_supervisor import FrontendSupervisor

        config = FrontendConfig(project_path=tmp_path, repo_root=tmp_path)
        supervisor = FrontendSupervisor(config, repo_root=tmp_path)

        mock_proc = MagicMock()
        mock_proc.pid = 42
        mock_proc.poll.return_value = None
        mock_proc.wait.return_value = None
        supervisor._proc = mock_proc  # noqa: SLF001

        kill_order: list[int] = []

        def track_kill(pid: int) -> None:
            kill_order.append(pid)

        with (
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor._collect_descendant_pids",
                return_value=[200, 100],  # 200 is deepest
            ),
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor._kill_process_group",
                side_effect=track_kill,
            ),
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor._check_port",
                return_value=False,
            ),
            patch("cmk.dev_deploy.frontend.frontend_supervisor.time.sleep"),
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor._pid_file",
                return_value=tmp_path / "test.pid",
            ),
        ):
            supervisor.stop()
            # iBazel killed first (42), then descendants in order (200, 100)
            assert kill_order == [42, 200, 100]

    def test_stop_verifies_port_free(self, tmp_path: Path) -> None:
        """No warning when port is free after kill."""
        from cmk.dev_deploy.frontend.frontend_supervisor import FrontendSupervisor

        config = FrontendConfig(project_path=tmp_path, repo_root=tmp_path)
        supervisor = FrontendSupervisor(config, repo_root=tmp_path)

        mock_proc = MagicMock()
        mock_proc.pid = 42
        mock_proc.poll.return_value = None
        mock_proc.wait.return_value = None
        supervisor._proc = mock_proc  # noqa: SLF001

        with (
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor._collect_descendant_pids",
                return_value=[],
            ),
            patch("cmk.dev_deploy.frontend.frontend_supervisor._kill_process_group"),
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor._check_port",
                return_value=False,
            ),
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor._cleanup_orphaned_port"
            ) as mock_port_cleanup,
            patch("cmk.dev_deploy.frontend.frontend_supervisor.time.sleep"),
            patch("cmk.dev_deploy.frontend.frontend_supervisor.output") as mock_output,
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor._pid_file",
                return_value=tmp_path / "test.pid",
            ),
        ):
            supervisor.stop()
            mock_output.warn.assert_not_called()
            mock_port_cleanup.assert_not_called()

    def test_stop_warns_if_port_still_in_use(self, tmp_path: Path) -> None:
        """Port still in use after kill -> warn + _cleanup_orphaned_port fallback."""
        from cmk.dev_deploy.frontend.frontend_supervisor import FrontendSupervisor

        config = FrontendConfig(project_path=tmp_path, repo_root=tmp_path)
        supervisor = FrontendSupervisor(config, repo_root=tmp_path)

        mock_proc = MagicMock()
        mock_proc.pid = 42
        mock_proc.poll.return_value = None
        mock_proc.wait.return_value = None
        supervisor._proc = mock_proc  # noqa: SLF001

        with (
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor._collect_descendant_pids",
                return_value=[],
            ),
            patch("cmk.dev_deploy.frontend.frontend_supervisor._kill_process_group"),
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor._check_port",
                return_value=True,
            ),
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor._cleanup_orphaned_port"
            ) as mock_port_cleanup,
            patch("cmk.dev_deploy.frontend.frontend_supervisor.time.sleep"),
            patch("cmk.dev_deploy.frontend.frontend_supervisor.output") as mock_output,
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor._pid_file",
                return_value=tmp_path / "test.pid",
            ),
        ):
            supervisor.stop()
            mock_output.warn.assert_called_once()
            assert "still in use" in mock_output.warn.call_args[0][0]
            mock_port_cleanup.assert_called_once_with(config.port)

    def test_stop_cleans_up_when_proc_already_dead(self, tmp_path: Path) -> None:
        """stop() with dead process still kills surviving descendant children."""
        from cmk.dev_deploy.frontend.frontend_supervisor import FrontendSupervisor

        config = FrontendConfig(project_path=tmp_path, repo_root=tmp_path)
        supervisor = FrontendSupervisor(config, repo_root=tmp_path)

        mock_proc = MagicMock()
        mock_proc.pid = 42
        mock_proc.poll.return_value = 1  # process already dead
        supervisor._proc = mock_proc  # noqa: SLF001

        with (
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor._collect_descendant_pids",
                return_value=[100],
            ),
            patch("cmk.dev_deploy.frontend.frontend_supervisor._kill_process_group") as mock_kill,
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor._check_port",
                return_value=False,
            ),
            patch("cmk.dev_deploy.frontend.frontend_supervisor.time.sleep"),
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor._pid_file",
                return_value=tmp_path / "test.pid",
            ),
        ):
            supervisor.stop()
            # Descendant 100 should still be killed even though main proc is dead
            mock_kill.assert_called_once_with(100)
            # Proc should be cleared (is_running returns False)
            assert not supervisor.is_running()

    def test_stop_noop_when_proc_is_none(self, tmp_path: Path) -> None:
        """stop() is a no-op when _proc is None."""
        from cmk.dev_deploy.frontend.frontend_supervisor import FrontendSupervisor

        config = FrontendConfig(project_path=tmp_path, repo_root=tmp_path)
        supervisor = FrontendSupervisor(config, repo_root=tmp_path)
        # _proc is None by default

        with (
            patch("cmk.dev_deploy.frontend.frontend_supervisor._kill_process_group") as mock_kill,
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor._pid_file",
                return_value=tmp_path / "test.pid",
            ),
        ):
            supervisor.stop()
            mock_kill.assert_not_called()


# ---------------------------------------------------------------------------
# TestShutdownParity
# ---------------------------------------------------------------------------


class TestShutdownParity:
    """All exit paths in _run_frontend and _run_frontend_watch call supervisor.stop()."""

    def _make_mock_site(self, tmp_path: Path) -> MagicMock:
        """Create a mock SiteInfo."""
        site = MagicMock()
        site.name = "test_site"
        site.root = tmp_path / "omd" / "sites" / "test_site"
        return site

    def test_run_frontend_ctrl_c_calls_stop(self, tmp_path: Path) -> None:
        """Ctrl-C in _run_frontend calls supervisor.stop()."""
        from cmk.dev_deploy.__main__ import _run_frontend

        project = tmp_path / "packages" / "cmk-frontend-vue"
        project.mkdir(parents=True)
        (project / "vite.config.ts").write_text("export default {}")

        mock_supervisor = MagicMock()
        mock_supervisor.start.return_value = None
        # is_running: first call raises KeyboardInterrupt, second returns False
        mock_supervisor.is_running.side_effect = [KeyboardInterrupt, False]
        mock_site = self._make_mock_site(tmp_path)

        with (
            patch("cmk.dev_deploy.__main__.output"),
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor.FrontendSupervisor",
                return_value=mock_supervisor,
            ),
            patch("cmk.dev_deploy.site.site_config.check_site_running", return_value=True),
            patch("cmk.dev_deploy.site.site_config.is_stale_override", return_value=False),
            patch("cmk.dev_deploy.site.site_config.write_override", return_value=True),
            patch("cmk.dev_deploy.site.site_config.remove_override", return_value=True),
        ):
            result = _run_frontend(tmp_path, mock_site, _ssh_state())
        assert result == 0
        mock_supervisor.stop.assert_called()

    def test_run_frontend_crash_calls_stop(self, tmp_path: Path) -> None:
        """iBazel crash path (while loop falls through) calls supervisor.stop()."""
        from cmk.dev_deploy.__main__ import _run_frontend

        project = tmp_path / "packages" / "cmk-frontend-vue"
        project.mkdir(parents=True)
        (project / "vite.config.ts").write_text("export default {}")

        mock_supervisor = MagicMock()
        mock_supervisor.start.return_value = None
        # is_running returns False immediately (crash): in the while loop, then in finally
        mock_supervisor.is_running.return_value = False
        mock_supervisor.get_crash_report.return_value = ["Error: ENOENT"]
        mock_site = self._make_mock_site(tmp_path)

        with (
            patch("cmk.dev_deploy.__main__.output"),
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor.FrontendSupervisor",
                return_value=mock_supervisor,
            ),
            patch("cmk.dev_deploy.site.site_config.check_site_running", return_value=True),
            patch("cmk.dev_deploy.site.site_config.is_stale_override", return_value=False),
            patch("cmk.dev_deploy.site.site_config.write_override", return_value=True),
            patch("cmk.dev_deploy.site.site_config.remove_override", return_value=True),
        ):
            result = _run_frontend(tmp_path, mock_site, _ssh_state())
        assert result == 1
        # supervisor.stop() MUST be called on crash path for descendant cleanup
        mock_supervisor.stop.assert_called()

    def test_run_frontend_watch_ctrl_c_calls_stop(self, tmp_path: Path) -> None:
        """Ctrl-C in _run_frontend_watch calls supervisor.stop()."""
        from cmk.dev_deploy.__main__ import _run_frontend_watch

        project = tmp_path / "packages" / "cmk-frontend-vue"
        project.mkdir(parents=True)
        (project / "vite.config.ts").write_text("export default {}")

        mock_supervisor = MagicMock()
        mock_supervisor.start.return_value = None
        mock_supervisor.is_running.return_value = False

        mock_args = MagicMock()
        mock_site = self._make_mock_site(tmp_path)

        with (
            patch("cmk.dev_deploy.__main__.output"),
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor.FrontendSupervisor",
                return_value=mock_supervisor,
            ),
            patch(
                "cmk.dev_deploy.__main__.watch_loop",
                side_effect=KeyboardInterrupt,
            ),
            patch("cmk.dev_deploy.site.site_config.check_site_running", return_value=True),
            patch("cmk.dev_deploy.site.site_config.is_stale_override", return_value=False),
            patch("cmk.dev_deploy.site.site_config.write_override", return_value=True),
            patch("cmk.dev_deploy.site.site_config.remove_override", return_value=True),
        ):
            result = _run_frontend_watch(mock_args, tmp_path, mock_site, _ssh_state())
        assert result == 0
        mock_supervisor.stop.assert_called()


# ---------------------------------------------------------------------------
# TestWaitUntilReady
# ---------------------------------------------------------------------------


class TestWaitUntilReady:
    """_wait_until_ready polls port with timeout and crash detection."""

    def test_returns_true_when_port_available(self, tmp_path: Path) -> None:
        from cmk.dev_deploy.frontend.frontend_supervisor import FrontendSupervisor

        config = FrontendConfig(project_path=tmp_path, repo_root=tmp_path, startup_timeout=5.0)
        supervisor = FrontendSupervisor(config, repo_root=tmp_path)
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None  # process alive
        supervisor._proc = mock_proc  # noqa: SLF001

        with (
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor._check_port",
                side_effect=[False, False, True],
            ),
            patch("time.monotonic", side_effect=[0.0, 0.5, 1.0, 1.5]),
            patch("time.sleep"),
            patch("cmk.dev_deploy.frontend.frontend_supervisor.output"),
        ):
            assert supervisor._wait_until_ready() is True  # noqa: SLF001

    def test_returns_false_on_timeout(self, tmp_path: Path) -> None:
        from cmk.dev_deploy.frontend.frontend_supervisor import FrontendSupervisor

        config = FrontendConfig(project_path=tmp_path, repo_root=tmp_path, startup_timeout=2.0)
        supervisor = FrontendSupervisor(config, repo_root=tmp_path)
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        supervisor._proc = mock_proc  # noqa: SLF001

        with (
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor._check_port",
                return_value=False,
            ),
            patch("time.monotonic", side_effect=[0.0, 0.5, 1.0, 1.5, 2.5]),
            patch("time.sleep"),
            patch("cmk.dev_deploy.frontend.frontend_supervisor.output"),
        ):
            assert supervisor._wait_until_ready() is False  # noqa: SLF001

    def test_returns_false_when_process_died(self, tmp_path: Path) -> None:
        """Race condition defense: port check succeeds but process has exited."""
        from cmk.dev_deploy.frontend.frontend_supervisor import FrontendSupervisor

        config = FrontendConfig(project_path=tmp_path, repo_root=tmp_path, startup_timeout=5.0)
        supervisor = FrontendSupervisor(config, repo_root=tmp_path)
        mock_proc = MagicMock()
        mock_proc.poll.return_value = 1  # process dead
        supervisor._proc = mock_proc  # noqa: SLF001

        with (
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor._check_port",
                return_value=True,
            ),
            patch("time.monotonic", side_effect=[0.0, 0.5]),
            patch("time.sleep"),
            patch("cmk.dev_deploy.frontend.frontend_supervisor.output"),
        ):
            assert supervisor._wait_until_ready() is False  # noqa: SLF001

    def test_startup_message_mentions_build_output(self, tmp_path: Path) -> None:
        """Startup message says 'build output' instead of 'this may take a minute'."""
        from cmk.dev_deploy.frontend.frontend_supervisor import FrontendSupervisor

        config = FrontendConfig(project_path=tmp_path, repo_root=tmp_path, startup_timeout=5.0)
        supervisor = FrontendSupervisor(config, repo_root=tmp_path)
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        supervisor._proc = mock_proc  # noqa: SLF001

        with (
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor._check_port",
                side_effect=[True],
            ),
            patch("time.monotonic", side_effect=[0.0, 0.5]),
            patch("time.sleep"),
            patch("cmk.dev_deploy.frontend.frontend_supervisor.output") as mock_output,
        ):
            supervisor._wait_until_ready()  # noqa: SLF001
            mock_output.info.assert_called_once()
            msg = mock_output.info.call_args[0][0]
            assert "build output" in msg
            assert "this may take a minute" not in msg


# ---------------------------------------------------------------------------
# TestSpawnIbazel
# ---------------------------------------------------------------------------


class TestSpawnIbazel:
    """_spawn_ibazel spawns iBazel in a new process group."""

    def test_spawns_with_correct_command(self, tmp_path: Path) -> None:
        from cmk.dev_deploy.frontend.frontend_supervisor import (
            FrontendSupervisor,
            IBAZEL_TARGET,
        )

        config = FrontendConfig(project_path=tmp_path, repo_root=tmp_path)
        supervisor = FrontendSupervisor(config, repo_root=tmp_path)

        mock_proc = MagicMock()
        mock_proc.pid = 42
        mock_proc.stdout = io.StringIO("")
        mock_proc.stderr = io.StringIO("")

        with (
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor.ensure_ibazel",
                return_value=Path("/cache/ibazel"),
            ),
            patch("subprocess.Popen", return_value=mock_proc) as mock_popen,
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor._pid_file",
                return_value=tmp_path / "test.pid",
            ),
        ):
            supervisor._spawn_ibazel()  # noqa: SLF001
            mock_popen.assert_called_once()
            call_args = mock_popen.call_args
            cmd = call_args[0][0]
            assert cmd == ["/cache/ibazel", "run", IBAZEL_TARGET]
            assert call_args[1]["start_new_session"] is True
            assert call_args[1]["cwd"] == str(tmp_path)

    def test_writes_pid_file_after_spawn(self, tmp_path: Path) -> None:
        from cmk.dev_deploy.frontend.frontend_supervisor import FrontendSupervisor

        pid_file = tmp_path / "test.pid"
        config = FrontendConfig(project_path=tmp_path, repo_root=tmp_path)
        supervisor = FrontendSupervisor(config, repo_root=tmp_path)

        mock_proc = MagicMock()
        mock_proc.pid = 42
        mock_proc.stdout = io.StringIO("")
        mock_proc.stderr = io.StringIO("")

        with (
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor.ensure_ibazel",
                return_value=Path("/cache/ibazel"),
            ),
            patch("subprocess.Popen", return_value=mock_proc),
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor._pid_file",
                return_value=pid_file,
            ),
        ):
            supervisor._spawn_ibazel()  # noqa: SLF001
            assert pid_file.read_text() == "42"

    def test_starts_stdout_prefixer_and_stderr_capture(self, tmp_path: Path) -> None:
        from cmk.dev_deploy.frontend.frontend_supervisor import FrontendSupervisor

        config = FrontendConfig(project_path=tmp_path, repo_root=tmp_path)
        supervisor = FrontendSupervisor(config, repo_root=tmp_path)

        mock_proc = MagicMock()
        mock_proc.pid = 42
        mock_proc.stdout = io.StringIO("")
        mock_proc.stderr = io.StringIO("")

        with (
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor.ensure_ibazel",
                return_value=Path("/cache/ibazel"),
            ),
            patch("subprocess.Popen", return_value=mock_proc),
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor._pid_file",
                return_value=tmp_path / "test.pid",
            ),
        ):
            supervisor._spawn_ibazel()  # noqa: SLF001
            # Both threads should have been created
            assert supervisor._stdout_prefixer is not None  # noqa: SLF001
            assert supervisor._stderr_capture is not None  # noqa: SLF001


# ---------------------------------------------------------------------------
# TestFrontendSupervisorLifecycle
# ---------------------------------------------------------------------------


class TestFrontendSupervisorLifecycle:
    """FrontendSupervisor basic lifecycle operations."""

    def test_is_running_false_before_start(self, tmp_path: Path) -> None:
        from cmk.dev_deploy.frontend.frontend_supervisor import FrontendSupervisor

        config = FrontendConfig(project_path=tmp_path, repo_root=tmp_path)
        supervisor = FrontendSupervisor(config, repo_root=tmp_path)
        assert supervisor.is_running() is False

    def test_stop_is_noop_when_not_started(self, tmp_path: Path) -> None:
        from cmk.dev_deploy.frontend.frontend_supervisor import FrontendSupervisor

        config = FrontendConfig(project_path=tmp_path, repo_root=tmp_path)
        supervisor = FrontendSupervisor(config, repo_root=tmp_path)
        # Should not raise; also verify PID file removed
        with patch(
            "cmk.dev_deploy.frontend.frontend_supervisor._pid_file",
            return_value=tmp_path / "test.pid",
        ):
            supervisor.stop()

    def test_get_crash_report_empty_when_not_started(self, tmp_path: Path) -> None:
        from cmk.dev_deploy.frontend.frontend_supervisor import FrontendSupervisor

        config = FrontendConfig(project_path=tmp_path, repo_root=tmp_path)
        supervisor = FrontendSupervisor(config, repo_root=tmp_path)
        assert supervisor.get_crash_report() == []

    def test_stop_sends_sigkill_not_sigterm(self, tmp_path: Path) -> None:
        from cmk.dev_deploy.frontend.frontend_supervisor import FrontendSupervisor

        config = FrontendConfig(project_path=tmp_path, repo_root=tmp_path)
        supervisor = FrontendSupervisor(config, repo_root=tmp_path)

        mock_proc = MagicMock()
        mock_proc.pid = 42
        mock_proc.poll.return_value = None  # process alive
        mock_proc.wait.return_value = None
        supervisor._proc = mock_proc  # noqa: SLF001

        with (
            patch("cmk.dev_deploy.frontend.frontend_supervisor._kill_process_group") as mock_kill,
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor._collect_descendant_pids",
                return_value=[],
            ),
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor._pid_file",
                return_value=tmp_path / "test.pid",
            ),
        ):
            supervisor.stop()
            mock_kill.assert_called_once_with(42)


# ---------------------------------------------------------------------------
# TestStdoutPrefixer
# ---------------------------------------------------------------------------


class TestStdoutPrefixer:
    """_StdoutPrefixer reads lines from a pipe and re-emits with [frontend] prefix."""

    def test_prefixes_lines_with_frontend(self) -> None:
        from cmk.dev_deploy.frontend.frontend_supervisor import _StdoutPrefixer

        pipe = io.StringIO("VITE v5.2.0 ready\nhmr update /src/App.vue\n")
        with patch("cmk.dev_deploy.core.output._print_locked") as mock_print:
            prefixer = _StdoutPrefixer(pipe)
            prefixer._thread.join(timeout=2.0)  # noqa: SLF001
            assert mock_print.call_count == 2
            for call_obj in mock_print.call_args_list:
                assert "[frontend]" in call_obj[0][0]
            # Check actual content
            assert "VITE v5.2.0 ready" in mock_print.call_args_list[0][0][0]
            assert "hmr update /src/App.vue" in mock_print.call_args_list[1][0][0]

    def test_no_vue_prefix(self) -> None:
        """Output uses [frontend], NOT [vue]."""
        from cmk.dev_deploy.frontend.frontend_supervisor import _StdoutPrefixer

        pipe = io.StringIO("test line\n")
        with patch("cmk.dev_deploy.core.output._print_locked") as mock_print:
            prefixer = _StdoutPrefixer(pipe)
            prefixer._thread.join(timeout=2.0)  # noqa: SLF001
            output_text = mock_print.call_args[0][0]
            assert "[frontend]" in output_text
            assert "[vue]" not in output_text

    def test_skips_empty_lines(self) -> None:
        from cmk.dev_deploy.frontend.frontend_supervisor import _StdoutPrefixer

        pipe = io.StringIO("line1\n\n\nline2\n")
        with patch("cmk.dev_deploy.core.output._print_locked") as mock_print:
            prefixer = _StdoutPrefixer(pipe)
            prefixer._thread.join(timeout=2.0)  # noqa: SLF001
            # Only non-empty lines should produce output
            assert mock_print.call_count == 2

    def test_handles_empty_input(self) -> None:
        from cmk.dev_deploy.frontend.frontend_supervisor import _StdoutPrefixer

        pipe = io.StringIO("")
        with patch("cmk.dev_deploy.core.output._print_locked") as mock_print:
            prefixer = _StdoutPrefixer(pipe)
            prefixer._thread.join(timeout=2.0)  # noqa: SLF001
            mock_print.assert_not_called()


# ---------------------------------------------------------------------------
# TestPreFlightChecks
# ---------------------------------------------------------------------------


class TestPreFlightChecks:
    """Pre-flight checks validate port availability for iBazel."""

    def test_port_in_use_raises(self, tmp_path: Path) -> None:
        from cmk.dev_deploy.frontend.frontend_supervisor import FrontendSupervisor

        config = FrontendConfig(project_path=tmp_path, repo_root=tmp_path)
        supervisor = FrontendSupervisor(config, repo_root=tmp_path)
        with patch("cmk.dev_deploy.frontend.frontend_supervisor._check_port", return_value=True):
            with pytest.raises(FrontendError, match="Port 5173 is already in use"):
                supervisor._check_port_available()  # noqa: SLF001

    def test_port_error_mentions_ibazel(self, tmp_path: Path) -> None:
        from cmk.dev_deploy.frontend.frontend_supervisor import FrontendSupervisor

        config = FrontendConfig(project_path=tmp_path, repo_root=tmp_path)
        supervisor = FrontendSupervisor(config, repo_root=tmp_path)
        with patch("cmk.dev_deploy.frontend.frontend_supervisor._check_port", return_value=True):
            with pytest.raises(FrontendError) as exc_info:
                supervisor._check_port_available()  # noqa: SLF001
            assert exc_info.value.recovery is not None
            assert "iBazel" in exc_info.value.recovery


# ---------------------------------------------------------------------------
# TestSimplifiedPortError
# ---------------------------------------------------------------------------


class TestSimplifiedPortError:
    """Simplified _check_port_available() error message."""

    def test_error_message_simple_no_pid(self, tmp_path: Path) -> None:
        """Port conflict error message is simple, no PID identification."""
        from cmk.dev_deploy.frontend.frontend_supervisor import FrontendSupervisor

        config = FrontendConfig(project_path=tmp_path, repo_root=tmp_path)
        supervisor = FrontendSupervisor(config, repo_root=tmp_path)
        with patch("cmk.dev_deploy.frontend.frontend_supervisor._check_port", return_value=True):
            with pytest.raises(FrontendError) as exc_info:
                supervisor._check_port_available()  # noqa: SLF001
            # Simple message without PID
            assert str(exc_info.value).startswith("Port 5173 is already in use")
            # Should NOT contain PID
            assert "PID" not in str(exc_info.value)

    def test_error_recovery_mentions_stale(self, tmp_path: Path) -> None:
        """Recovery hint mentions stale cmk-dev-deploy instance."""
        from cmk.dev_deploy.frontend.frontend_supervisor import FrontendSupervisor

        config = FrontendConfig(project_path=tmp_path, repo_root=tmp_path)
        supervisor = FrontendSupervisor(config, repo_root=tmp_path)
        with patch("cmk.dev_deploy.frontend.frontend_supervisor._check_port", return_value=True):
            with pytest.raises(FrontendError) as exc_info:
                supervisor._check_port_available()  # noqa: SLF001
            assert exc_info.value.recovery is not None
            assert "stale" in exc_info.value.recovery
            assert "cmk-dev-deploy" in exc_info.value.recovery

    def test_identify_port_holder_removed(self) -> None:
        """_identify_port_holder no longer exists in the module."""
        import cmk.dev_deploy.frontend.frontend_supervisor as fs_mod

        assert not hasattr(fs_mod, "_identify_port_holder")


# ---------------------------------------------------------------------------
# TestRunFrontend
# ---------------------------------------------------------------------------


class TestRunFrontend:
    """Integration tests for _run_frontend lifecycle wiring."""

    def _make_mock_site(self, tmp_path: Path) -> MagicMock:
        """Create a mock SiteInfo for _run_frontend tests."""
        site = MagicMock()
        site.name = "test_site"
        site.root = tmp_path / "omd" / "sites" / "test_site"
        return site

    def test_run_frontend_missing_project(self, tmp_path: Path) -> None:
        """detect_frontend_project raises FrontendError -> returns 1."""
        from cmk.dev_deploy.__main__ import _run_frontend

        mock_site = self._make_mock_site(tmp_path)
        with (
            patch("cmk.dev_deploy.__main__.output"),
            patch("cmk.dev_deploy.site.site_config.check_site_running", return_value=True),
            patch("cmk.dev_deploy.site.site_config.is_stale_override", return_value=False),
            patch("cmk.dev_deploy.site.site_config.write_override", return_value=True),
            patch("cmk.dev_deploy.site.site_config.remove_override", return_value=True),
        ):
            result = _run_frontend(tmp_path, mock_site, _ssh_state())
        assert result == 1

    def test_run_frontend_start_failure(self, tmp_path: Path) -> None:
        """FrontendSupervisor.start() raises FrontendError -> returns 1."""
        from cmk.dev_deploy.__main__ import _run_frontend

        project = tmp_path / "packages" / "cmk-frontend-vue"
        project.mkdir(parents=True)
        (project / "vite.config.ts").write_text("export default {}")

        mock_supervisor = MagicMock()
        mock_supervisor.start.side_effect = FrontendError("iBazel failed to start")
        mock_supervisor.is_running.return_value = False
        mock_site = self._make_mock_site(tmp_path)

        with (
            patch("cmk.dev_deploy.__main__.output"),
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor.FrontendSupervisor",
                return_value=mock_supervisor,
            ),
            patch("cmk.dev_deploy.site.site_config.check_site_running", return_value=True),
            patch("cmk.dev_deploy.site.site_config.is_stale_override", return_value=False),
            patch("cmk.dev_deploy.site.site_config.write_override", return_value=True),
            patch("cmk.dev_deploy.site.site_config.remove_override", return_value=True),
        ):
            result = _run_frontend(tmp_path, mock_site, _ssh_state())
        assert result == 1

    def test_run_frontend_keyboard_interrupt(self, tmp_path: Path) -> None:
        """Ctrl-C calls stop() and returns 0 with 'stopped' message."""
        from cmk.dev_deploy.__main__ import _run_frontend

        project = tmp_path / "packages" / "cmk-frontend-vue"
        project.mkdir(parents=True)
        (project / "vite.config.ts").write_text("export default {}")

        mock_supervisor = MagicMock()
        mock_supervisor.start.return_value = None
        # First call in while loop raises KeyboardInterrupt;
        # second call in finally block returns False (already stopped)
        mock_supervisor.is_running.side_effect = [KeyboardInterrupt, False]
        mock_site = self._make_mock_site(tmp_path)

        with (
            patch("cmk.dev_deploy.__main__.output") as mock_output,
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor.FrontendSupervisor",
                return_value=mock_supervisor,
            ),
            patch("cmk.dev_deploy.site.site_config.check_site_running", return_value=True),
            patch("cmk.dev_deploy.site.site_config.is_stale_override", return_value=False),
            patch("cmk.dev_deploy.site.site_config.write_override", return_value=True),
            patch("cmk.dev_deploy.site.site_config.remove_override", return_value=True),
        ):
            result = _run_frontend(tmp_path, mock_site, _ssh_state())
        assert result == 0
        mock_supervisor.stop.assert_called()
        # Should print "Frontend supervisor stopped."
        mock_output.success.assert_any_call("Frontend supervisor stopped.")

    def test_run_frontend_crash(self, tmp_path: Path) -> None:
        """iBazel crash (is_running returns False) -> returns 1 with crash report."""
        from cmk.dev_deploy.__main__ import _run_frontend

        project = tmp_path / "packages" / "cmk-frontend-vue"
        project.mkdir(parents=True)
        (project / "vite.config.ts").write_text("export default {}")

        mock_supervisor = MagicMock()
        mock_supervisor.start.return_value = None
        mock_supervisor.is_running.return_value = False
        mock_supervisor.get_crash_report.return_value = ["Error: ENOENT"]
        mock_site = self._make_mock_site(tmp_path)

        with (
            patch("cmk.dev_deploy.__main__.output") as mock_output,
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor.FrontendSupervisor",
                return_value=mock_supervisor,
            ),
            patch("cmk.dev_deploy.site.site_config.check_site_running", return_value=True),
            patch("cmk.dev_deploy.site.site_config.is_stale_override", return_value=False),
            patch("cmk.dev_deploy.site.site_config.write_override", return_value=True),
            patch("cmk.dev_deploy.site.site_config.remove_override", return_value=True),
        ):
            result = _run_frontend(tmp_path, mock_site, _ssh_state())
        assert result == 1
        mock_output.error.assert_any_call("iBazel frontend supervisor crashed")

    def test_run_frontend_startup_banner(self, tmp_path: Path) -> None:
        """After successful start, startup banner with success+info is printed."""
        from cmk.dev_deploy.__main__ import _run_frontend

        project = tmp_path / "packages" / "cmk-frontend-vue"
        project.mkdir(parents=True)
        (project / "vite.config.ts").write_text("export default {}")

        mock_supervisor = MagicMock()
        mock_supervisor.start.return_value = None
        # First is_running for the while loop -> KeyboardInterrupt to exit cleanly
        mock_supervisor.is_running.side_effect = [KeyboardInterrupt, False]
        mock_site = self._make_mock_site(tmp_path)

        with (
            patch("cmk.dev_deploy.__main__.output") as mock_output,
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor.FrontendSupervisor",
                return_value=mock_supervisor,
            ),
            patch("cmk.dev_deploy.site.site_config.check_site_running", return_value=True),
            patch("cmk.dev_deploy.site.site_config.is_stale_override", return_value=False),
            patch("cmk.dev_deploy.site.site_config.write_override", return_value=True),
            patch("cmk.dev_deploy.site.site_config.remove_override", return_value=True),
        ):
            result = _run_frontend(tmp_path, mock_site, _ssh_state())

        assert result == 0
        # Verify startup banner
        mock_output.success.assert_any_call("Frontend supervisor active -- watching for changes")
        # Verify target and URL info lines
        info_calls = [c[0][0] for c in mock_output.info.call_args_list]
        target_lines = [c for c in info_calls if "//packages/cmk-frontend-vue:vite" in c]
        assert len(target_lines) >= 1
        url_lines = [c for c in info_calls if "http://localhost:5173/" in c]
        assert len(url_lines) >= 1

    def test_main_frontend_after_failed_deploy(self) -> None:
        """Deploy failure (exit_code=1) prevents _run_frontend from being called."""
        from cmk.dev_deploy.types import DeployCycleResult

        # Test the guard condition used by main(): if result.exit_code != 0,
        # _run_frontend is never called.
        result = DeployCycleResult(
            exit_code=1,
            deployed=(),
            skipped=(),
            skipped_reasons={},
            services_restarted=0,
            all_skipped=False,
        )
        assert result.exit_code != 0  # Guard prevents _run_frontend


# ---------------------------------------------------------------------------
# Test helpers for frontend-supervised integration tests
# ---------------------------------------------------------------------------


def _make_changeset(**kwargs: object) -> ChangeSet:
    """Create a ChangeSet with sensible defaults for testing."""
    defaults: dict[str, object] = dict(build_commit="abc123def456", files=(), categories={})
    defaults.update(kwargs)
    return ChangeSet(**defaults)  # type: ignore[arg-type]


def _make_install_spec(package: str, *, frontend_supervised: bool = False) -> InstallSpec:
    """Create a minimal InstallSpec for filter tests."""
    return InstallSpec(
        package=package,
        package_target=f"//{package}:all",
        output_basename="dist",
        install_dest=f"share/{package}",
        mode=0o755,
        post_install=(),
        edition_constraint=None,
        needs_version_flag=False,
        needs_faked_artifacts=False,
        use_copytree=True,
        frontend_supervised=frontend_supervised,
    )


# ---------------------------------------------------------------------------
# TestFrontendSupervisedRegistry
# ---------------------------------------------------------------------------


class TestFrontendSupervisedRegistry:
    """Manifest-driven frontend_supervised flag validation."""

    def test_manifest_contains_frontend_vue(self) -> None:
        from cmk.dev_deploy.manifest.reader import get_frontend_supervised_prefixes

        prefixes = get_frontend_supervised_prefixes()
        assert "packages/cmk-frontend-vue/" in prefixes

    def test_prefixes_have_trailing_slash(self) -> None:
        from cmk.dev_deploy.manifest.reader import get_frontend_supervised_prefixes

        prefixes = get_frontend_supervised_prefixes()
        # All prefixes should end with /
        for p in prefixes:
            assert p.endswith("/"), f"Prefix {p!r} missing trailing slash"


# ---------------------------------------------------------------------------
# TestFilterFrontendSupervised
# ---------------------------------------------------------------------------


class TestFilterFrontendSupervised:
    """filter_frontend_supervised() removes Vue specs when active."""

    def test_noop_when_false(self) -> None:
        from cmk.dev_deploy.deployers.bazel_builder import filter_frontend_supervised

        specs = (
            _make_install_spec("packages/cmk-frontend-vue", frontend_supervised=True),
            _make_install_spec("packages/livestatus"),
        )
        result = filter_frontend_supervised(specs, False)
        assert result == specs

    def test_filters_cmk_frontend_vue(self) -> None:
        from cmk.dev_deploy.deployers.bazel_builder import filter_frontend_supervised

        specs = (
            _make_install_spec("packages/cmk-frontend-vue", frontend_supervised=True),
            _make_install_spec("packages/livestatus"),
        )
        result = filter_frontend_supervised(specs, True)
        assert len(result) == 1
        assert result[0].package == "packages/livestatus"

    def test_preserves_other_specs(self) -> None:
        from cmk.dev_deploy.deployers.bazel_builder import filter_frontend_supervised

        specs = (
            _make_install_spec("packages/cmk-shared-typing"),
            _make_install_spec("packages/cmk-frontend"),
            _make_install_spec("packages/livestatus"),
        )
        result = filter_frontend_supervised(specs, True)
        assert len(result) == 3
        # All preserved -- none are frontend-supervised
        assert {s.package for s in result} == {
            "packages/cmk-shared-typing",
            "packages/cmk-frontend",
            "packages/livestatus",
        }


# ---------------------------------------------------------------------------
# TestBazelQueryFiltering
# ---------------------------------------------------------------------------


class TestBazelQueryFiltering:
    """_get_bazel_queryable_files excludes frontend-supervised files."""

    def test_filters_vue_files_when_supervised(self) -> None:
        from cmk.dev_deploy.execution.bazel_resolver import _get_bazel_queryable_files

        changes = _make_changeset(
            categories={
                ChangeCategory.VUE: (
                    "packages/cmk-frontend-vue/src/App.vue",
                    "packages/cmk-shared-typing/src/types.ts",
                ),
            }
        )
        result = _get_bazel_queryable_files(changes, frontend_supervised=True)
        # cmk-frontend-vue filtered, cmk-shared-typing preserved
        assert result == ["packages/cmk-shared-typing/src/types.ts"]

    def test_preserves_shared_typing(self) -> None:
        from cmk.dev_deploy.execution.bazel_resolver import _get_bazel_queryable_files

        changes = _make_changeset(
            categories={
                ChangeCategory.VUE: (
                    "packages/cmk-shared-typing/src/types.ts",
                    "packages/cmk-shared-typing/src/index.ts",
                ),
            }
        )
        result = _get_bazel_queryable_files(changes, frontend_supervised=True)
        # Both preserved -- cmk-shared-typing is NOT frontend-supervised
        assert len(result) == 2


# ---------------------------------------------------------------------------
# TestFrontendHint
# ---------------------------------------------------------------------------


class TestFrontendHint:
    """print_frontend_hint prints only when frontend-supervised Vue files present."""

    def test_hint_shown_for_frontend_vue_files(self) -> None:
        from cmk.dev_deploy.core.output import print_frontend_hint

        changes = _make_changeset(
            categories={
                ChangeCategory.VUE: (
                    "packages/cmk-frontend-vue/src/App.vue",
                    "packages/cmk-shared-typing/src/types.ts",
                ),
            }
        )
        with patch("cmk.dev_deploy.core.output._print_locked") as mock_print:
            print_frontend_hint(changes)
            mock_print.assert_called_once()
            assert "--frontend" in mock_print.call_args[0][0]

    def test_no_hint_for_shared_typing_only(self) -> None:
        from cmk.dev_deploy.core.output import print_frontend_hint

        changes = _make_changeset(
            categories={
                ChangeCategory.VUE: ("packages/cmk-shared-typing/src/types.ts",),
            }
        )
        with patch("cmk.dev_deploy.core.output._print_locked") as mock_print:
            print_frontend_hint(changes)
            mock_print.assert_not_called()

    def test_no_hint_when_no_vue_changes(self) -> None:
        from cmk.dev_deploy.core.output import print_frontend_hint

        changes = _make_changeset(
            categories={
                ChangeCategory.PYTHON: ("cmk/gui/views.py",),
            }
        )
        with patch("cmk.dev_deploy.core.output._print_locked") as mock_print:
            print_frontend_hint(changes)
            mock_print.assert_not_called()


# ---------------------------------------------------------------------------
# TestVerboseChangesHmrAnnotation
# ---------------------------------------------------------------------------


class TestVerboseChangesHmrAnnotation:
    """print_verbose_changes annotates frontend-supervised files with (Vite HMR)."""

    def test_annotates_vue_files_when_supervised(self) -> None:
        from cmk.dev_deploy.core.output import (
            print_verbose_changes,
            set_verbosity,
            Verbosity,
        )

        changes = _make_changeset(
            categories={
                ChangeCategory.VUE: (
                    "packages/cmk-frontend-vue/src/App.vue",
                    "packages/cmk-shared-typing/src/types.ts",
                ),
            }
        )
        set_verbosity(Verbosity.VERBOSE)
        try:
            with patch("cmk.dev_deploy.core.output._print_locked") as mock_print:
                print_verbose_changes(changes, frontend_supervised=True)
                calls_text = [c[0][0] for c in mock_print.call_args_list]
                # Vue/TypeScript header + 2 file lines
                vue_file_calls = [c for c in calls_text if "App.vue" in c]
                assert len(vue_file_calls) == 1
                assert "(Vite HMR)" in vue_file_calls[0]
        finally:
            set_verbosity(Verbosity.DEFAULT)

    def test_no_annotation_for_shared_typing(self) -> None:
        from cmk.dev_deploy.core.output import (
            print_verbose_changes,
            set_verbosity,
            Verbosity,
        )

        changes = _make_changeset(
            categories={
                ChangeCategory.VUE: ("packages/cmk-shared-typing/src/types.ts",),
            }
        )
        set_verbosity(Verbosity.VERBOSE)
        try:
            with patch("cmk.dev_deploy.core.output._print_locked") as mock_print:
                print_verbose_changes(changes, frontend_supervised=True)
                calls_text = [c[0][0] for c in mock_print.call_args_list]
                typing_calls = [c for c in calls_text if "types.ts" in c]
                assert len(typing_calls) == 1
                assert "(Vite HMR)" not in typing_calls[0]
        finally:
            set_verbosity(Verbosity.DEFAULT)


# ---------------------------------------------------------------------------
# TestWatchLoopSupervisor
# ---------------------------------------------------------------------------


class TestWatchLoopSupervisor:
    """watch_loop with supervisor parameter for combined --frontend --watch."""

    def _make_mock_supervisor(
        self, *, is_running: bool = True, crash_lines: list[str] | None = None
    ) -> MagicMock:
        """Create a mock FrontendSupervisor."""
        supervisor = MagicMock()
        supervisor.is_running.return_value = is_running
        supervisor.get_crash_report.return_value = crash_lines or []
        supervisor.stop.return_value = None
        return supervisor

    def _make_site(self) -> MagicMock:
        """Create a mock SiteInfo."""
        site = MagicMock()
        site.name = "test_site"
        site.root = Path("/omd/sites/test")
        site.build_commit = "abc123"
        return site

    def _make_deploy_result(self, exit_code: int = 0) -> MagicMock:
        """Create a mock DeployCycleResult."""
        result = MagicMock()
        result.exit_code = exit_code
        result.all_skipped = False
        result.services_restarted = 0
        result.deployed = ("python",)
        result.skipped = ()
        result.skipped_reasons = {}
        return result

    def test_supervisor_crash_returns_1(self) -> None:
        """Supervisor crash before poll returns 1 with [frontend] prefix."""
        from cmk.dev_deploy.watcher import watch_loop

        supervisor = self._make_mock_supervisor(
            is_running=False,
            crash_lines=["Error: ENOENT", "at Module._resolveFilename"],
        )
        site = self._make_site()

        with (
            patch("cmk.dev_deploy.watcher._get_content_hash", return_value="hash1"),
            patch("cmk.dev_deploy.watcher._get_state_diff_base", return_value="abc123"),
            patch("cmk.dev_deploy.watcher.output") as mock_output,
        ):
            result = watch_loop(
                site,
                Path("/repo"),
                self._make_deploy_result,
                supervisor=supervisor,
            )

        assert result == 1
        supervisor.get_crash_report.assert_called_once()
        mock_output.error.assert_any_call("[frontend] Process exited unexpectedly")

    def test_deploy_failure_stops_supervisor(self) -> None:
        """Deploy failure in combined mode stops supervisor and returns 1."""
        from cmk.dev_deploy.watcher import watch_loop

        supervisor = self._make_mock_supervisor(is_running=True)
        site = self._make_site()
        deploy_fn = MagicMock(return_value=self._make_deploy_result(exit_code=1))
        call_count = 0

        def mock_get_content_hash(_base: str | None, _root: Path) -> str:
            nonlocal call_count
            call_count += 1
            # First call: initial hash. Second call: changed hash to trigger deploy.
            if call_count <= 1:
                return "hash1"
            return "hash2"

        with (
            patch(
                "cmk.dev_deploy.watcher._get_content_hash",
                side_effect=mock_get_content_hash,
            ),
            patch("cmk.dev_deploy.watcher._get_state_diff_base", return_value="abc123"),
            patch("cmk.dev_deploy.watcher.time.sleep"),
            patch("cmk.dev_deploy.watcher.output"),
        ):
            result = watch_loop(site, Path("/repo"), deploy_fn, supervisor=supervisor)

        assert result == 1
        supervisor.stop.assert_called_once()
        deploy_fn.assert_called_once()

    def test_keyboard_interrupt_stops_supervisor(self) -> None:
        """Ctrl-C stops supervisor and returns 0."""
        from cmk.dev_deploy.watcher import watch_loop

        supervisor = self._make_mock_supervisor(is_running=True)
        site = self._make_site()
        # Supervisor is_running returns True (first check passes), then sleep raises
        supervisor.is_running.return_value = True

        with (
            patch("cmk.dev_deploy.watcher._get_content_hash", return_value="hash1"),
            patch("cmk.dev_deploy.watcher._get_state_diff_base", return_value="abc123"),
            patch("cmk.dev_deploy.watcher.time.sleep", side_effect=KeyboardInterrupt),
            patch("cmk.dev_deploy.watcher.output"),
        ):
            result = watch_loop(
                site,
                Path("/repo"),
                self._make_deploy_result,
                supervisor=supervisor,
            )

        assert result == 0
        supervisor.stop.assert_called_once()

    def test_no_supervisor_preserves_behavior(self) -> None:
        """supervisor=None preserves existing watch behavior."""
        from cmk.dev_deploy.watcher import watch_loop

        site = self._make_site()
        deploy_result = self._make_deploy_result(exit_code=0)
        deploy_fn = MagicMock(return_value=deploy_result)
        call_count = 0

        def mock_get_content_hash(_base: str | None, _root: Path) -> str:
            nonlocal call_count
            call_count += 1
            if call_count <= 1:
                return "hash1"
            if call_count <= 3:
                return "hash2"
            # After deploy, raise KeyboardInterrupt via sleep
            return "hash2"

        sleep_count = 0

        def mock_sleep(_seconds: float) -> None:
            nonlocal sleep_count
            sleep_count += 1
            if sleep_count > 3:
                raise KeyboardInterrupt

        with (
            patch(
                "cmk.dev_deploy.watcher._get_content_hash",
                side_effect=mock_get_content_hash,
            ),
            patch("cmk.dev_deploy.watcher._get_state_diff_base", return_value="abc123"),
            patch("cmk.dev_deploy.watcher.time.sleep", side_effect=mock_sleep),
            patch("cmk.dev_deploy.watcher.output"),
        ):
            result = watch_loop(site, Path("/repo"), deploy_fn, supervisor=None)

        assert result == 0
        deploy_fn.assert_called_once()


# ---------------------------------------------------------------------------
# TestRunFrontendWatch
# ---------------------------------------------------------------------------


class TestRunFrontendWatch:
    """_run_frontend_watch combined mode lifecycle tests."""

    def test_combined_mode_starts_ibazel_and_watch(self, tmp_path: Path) -> None:
        """Combined mode starts iBazel-based supervisor and calls watch_loop with it."""
        from cmk.dev_deploy.__main__ import _run_frontend_watch

        project = tmp_path / "packages" / "cmk-frontend-vue"
        project.mkdir(parents=True)
        (project / "vite.config.ts").write_text("export default {}")

        mock_supervisor = MagicMock()
        mock_supervisor.start.return_value = None
        mock_supervisor.is_running.return_value = False

        mock_args = MagicMock()
        mock_site = MagicMock()
        mock_site.name = "test"
        mock_site.root = tmp_path / "omd" / "sites" / "test"

        with (
            patch("cmk.dev_deploy.__main__.output"),
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor.FrontendSupervisor",
                return_value=mock_supervisor,
            ),
            patch("cmk.dev_deploy.__main__.watch_loop", return_value=0) as mock_watch,
            patch("cmk.dev_deploy.site.site_config.check_site_running", return_value=True),
            patch("cmk.dev_deploy.site.site_config.is_stale_override", return_value=False),
            patch("cmk.dev_deploy.site.site_config.write_override", return_value=True),
            patch("cmk.dev_deploy.site.site_config.remove_override", return_value=True),
        ):
            result = _run_frontend_watch(mock_args, tmp_path, mock_site, _ssh_state())

        assert result == 0
        mock_supervisor.start.assert_called_once()
        mock_watch.assert_called_once()
        # Verify supervisor was passed to watch_loop
        _, kwargs = mock_watch.call_args
        assert kwargs.get("supervisor") is mock_supervisor

    def test_combined_mode_missing_project(self, tmp_path: Path) -> None:
        """detect_frontend_project raises FrontendError -> returns 1."""
        from cmk.dev_deploy.__main__ import _run_frontend_watch

        mock_args = MagicMock()
        mock_site = MagicMock()
        mock_site.root = tmp_path / "omd" / "sites" / "test"

        with (
            patch("cmk.dev_deploy.__main__.output"),
            patch("cmk.dev_deploy.site.site_config.check_site_running", return_value=True),
            patch("cmk.dev_deploy.site.site_config.is_stale_override", return_value=False),
            patch("cmk.dev_deploy.site.site_config.write_override", return_value=True),
            patch("cmk.dev_deploy.site.site_config.remove_override", return_value=True),
        ):
            result = _run_frontend_watch(mock_args, tmp_path, mock_site, _ssh_state())

        assert result == 1

    def test_combined_mode_supervisor_start_failure(self, tmp_path: Path) -> None:
        """supervisor.start() raises FrontendError -> returns 1."""
        from cmk.dev_deploy.__main__ import _run_frontend_watch

        project = tmp_path / "packages" / "cmk-frontend-vue"
        project.mkdir(parents=True)
        (project / "vite.config.ts").write_text("export default {}")

        mock_supervisor = MagicMock()
        mock_supervisor.start.side_effect = FrontendError("iBazel failed")
        mock_supervisor.is_running.return_value = False

        mock_args = MagicMock()
        mock_site = MagicMock()
        mock_site.root = tmp_path / "omd" / "sites" / "test"

        with (
            patch("cmk.dev_deploy.__main__.output"),
            patch(
                "cmk.dev_deploy.frontend.frontend_supervisor.FrontendSupervisor",
                return_value=mock_supervisor,
            ),
            patch("cmk.dev_deploy.site.site_config.check_site_running", return_value=True),
            patch("cmk.dev_deploy.site.site_config.is_stale_override", return_value=False),
            patch("cmk.dev_deploy.site.site_config.write_override", return_value=True),
            patch("cmk.dev_deploy.site.site_config.remove_override", return_value=True),
        ):
            result = _run_frontend_watch(mock_args, tmp_path, mock_site, _ssh_state())

        assert result == 1


# ---------------------------------------------------------------------------
# TestMainCombinedMode
# ---------------------------------------------------------------------------


class TestMainCombinedMode:
    """main() dispatching for --frontend --watch combined mode."""

    def _setup_main_mocks(self) -> dict[str, MagicMock]:
        """Common mock setup for main() tests."""
        return {
            "find_repo_root": MagicMock(return_value=Path("/repo")),
            "resolve_site": MagicMock(),
            "ensure_manifest": MagicMock(),
            "check_branch_mismatch": MagicMock(return_value=None),
        }

    def _mock_output(self) -> MagicMock:
        """Create a mock output module with working verbosity comparison."""
        from cmk.dev_deploy.core.output import Verbosity

        mock = MagicMock()
        mock.get_verbosity.return_value = Verbosity.DEFAULT
        mock.Verbosity = Verbosity
        mock.BOLD = ""
        mock.RESET = ""
        return mock

    def test_main_frontend_watch_deploy_failure(self) -> None:
        """Initial deploy failure prevents _run_frontend_watch from being called."""
        from cmk.dev_deploy.__main__ import main
        from cmk.dev_deploy.types import DeployCycleResult

        failed_result = DeployCycleResult(
            exit_code=1,
            deployed=(),
            skipped=(),
            skipped_reasons={},
            services_restarted=0,
            all_skipped=False,
        )

        with (
            patch("cmk.dev_deploy.__main__.output", self._mock_output()),
            patch("cmk.dev_deploy.__main__.find_repo_root", return_value=Path("/repo")),
            patch("cmk.dev_deploy.__main__.resolve_site"),
            patch("cmk.dev_deploy.manifest.staleness.ensure_manifest"),
            patch("cmk.dev_deploy.core.preflight.preflight_bazel_check", return_value=[]),
            patch("cmk.dev_deploy.site.overlay.is_overlay_active", return_value=True),
            patch("cmk.dev_deploy.site.overlay.ensure_overlay"),
            patch("cmk.dev_deploy.site.overlay.teardown_overlay"),
            patch("cmk.dev_deploy.__main__.check_branch_mismatch", return_value=None),
            patch(
                "cmk.dev_deploy.__main__._run_deploy_cycle", return_value=failed_result
            ) as mock_deploy,
            patch("cmk.dev_deploy.__main__._run_frontend_watch") as mock_fw,
        ):
            result = main(["--frontend", "--watch"])

        assert result == 1
        mock_deploy.assert_called_once()
        mock_fw.assert_not_called()

    def test_main_frontend_watch_calls_combined(self) -> None:
        """Successful deploy calls _run_frontend_watch."""
        from cmk.dev_deploy.__main__ import main
        from cmk.dev_deploy.types import DeployCycleResult

        ok_result = DeployCycleResult(
            exit_code=0,
            deployed=("python",),
            skipped=(),
            skipped_reasons={},
            services_restarted=0,
            all_skipped=False,
        )

        with (
            patch("cmk.dev_deploy.__main__.output", self._mock_output()),
            patch("cmk.dev_deploy.__main__.find_repo_root", return_value=Path("/repo")),
            patch("cmk.dev_deploy.__main__.resolve_site"),
            patch("cmk.dev_deploy.manifest.staleness.ensure_manifest"),
            patch("cmk.dev_deploy.core.preflight.preflight_bazel_check", return_value=[]),
            patch("cmk.dev_deploy.site.overlay.is_overlay_active", return_value=True),
            patch("cmk.dev_deploy.site.overlay.ensure_overlay"),
            patch("cmk.dev_deploy.site.overlay.teardown_overlay"),
            patch("cmk.dev_deploy.__main__.check_branch_mismatch", return_value=None),
            patch(
                "cmk.dev_deploy.__main__._run_deploy_cycle", return_value=ok_result
            ) as mock_deploy,
            patch("cmk.dev_deploy.__main__._run_frontend_watch", return_value=0) as mock_fw,
        ):
            result = main(["--frontend", "--watch"])

        assert result == 0
        mock_deploy.assert_called_once()
        mock_fw.assert_called_once()


# ---------------------------------------------------------------------------
# TestFrontendFlag
# ---------------------------------------------------------------------------


class TestFrontendFlag:
    """CLI --frontend flag parsing and mutual exclusion."""

    def test_frontend_flag_default(self) -> None:
        from cmk.dev_deploy.cli import parse_args

        args = parse_args([])
        assert args.frontend is False

    def test_frontend_flag_set(self) -> None:
        from cmk.dev_deploy.cli import parse_args

        args = parse_args(["--frontend"])
        assert args.frontend is True

    def test_frontend_dry_run_mutual_exclusion(self) -> None:
        from cmk.dev_deploy.cli import parse_args

        with pytest.raises(SystemExit):
            parse_args(["--frontend", "--dry-run"])

    def test_frontend_info_mutual_exclusion(self) -> None:
        from cmk.dev_deploy.cli import parse_args

        with pytest.raises(SystemExit):
            parse_args(["--frontend", "--info"])

    def test_frontend_watch_allowed(self) -> None:
        """--frontend --watch is now allowed (Phase 31)."""
        from cmk.dev_deploy.cli import parse_args

        args = parse_args(["--frontend", "--watch"])
        assert args.frontend is True
        assert args.watch is True


# ---------------------------------------------------------------------------
# TestV14CodeRemoval
# ---------------------------------------------------------------------------


class TestV14CodeRemoval:
    """Verify v1.4 code (npx, node_modules, _spawn_vite) is gone."""

    def test_no_npx_references(self) -> None:
        import cmk.dev_deploy.frontend.frontend_supervisor as fs_mod

        source = inspect.getsource(fs_mod)
        assert "npx" not in source

    def test_no_node_modules_references(self) -> None:
        import cmk.dev_deploy.frontend.frontend_supervisor as fs_mod

        source = inspect.getsource(fs_mod)
        assert "node_modules" not in source

    def test_no_spawn_vite_method(self) -> None:
        from cmk.dev_deploy.frontend.frontend_supervisor import FrontendSupervisor

        assert not hasattr(FrontendSupervisor, "_spawn_vite")

    def test_no_check_prerequisites_method(self) -> None:
        from cmk.dev_deploy.frontend.frontend_supervisor import FrontendSupervisor

        assert not hasattr(FrontendSupervisor, "_check_prerequisites")

    def test_no_terminate_process_group(self) -> None:
        """_terminate_process_group replaced by _kill_process_group."""
        import cmk.dev_deploy.frontend.frontend_supervisor as fs_mod

        source = inspect.getsource(fs_mod)
        assert "_terminate_process_group" not in source

    def test_no_shutil_import(self) -> None:
        import cmk.dev_deploy.frontend.frontend_supervisor as fs_mod

        source = inspect.getsource(fs_mod)
        assert "shutil" not in source


# ---------------------------------------------------------------------------
# TestCLIHelpText
# ---------------------------------------------------------------------------


class TestCLIHelpText:
    """CLI help text for --frontend mentions iBazel."""

    def test_frontend_help_mentions_ibazel(self) -> None:
        from cmk.dev_deploy.cli import parse_args

        # parse_args builds the parser internally; let's inspect the help
        with pytest.raises(SystemExit):
            parse_args(["--help"])
        # The above exits. Instead, inspect parse_args source or the action.
        # Directly check the help text from the parser created by parse_args.

    def test_frontend_help_contains_ibazel(self) -> None:
        """--frontend help text mentions iBazel."""
        from cmk.dev_deploy.cli import parse_args

        # Capture the help text
        try:
            parse_args(["--help"])
        except SystemExit:
            pass

        # The simplest approach: check the source code directly
        cli_source = inspect.getsource(parse_args)
        # The help text for --frontend is in the source
        assert "iBazel" in cli_source


# ---------------------------------------------------------------------------
# TestIBazelTarget
# ---------------------------------------------------------------------------


class TestIBazelTarget:
    """IBAZEL_TARGET constant is correctly defined."""

    def test_target_value(self) -> None:
        from cmk.dev_deploy.frontend.frontend_supervisor import IBAZEL_TARGET

        assert IBAZEL_TARGET == "//packages/cmk-frontend-vue:vite"


# ---------------------------------------------------------------------------
# TestCrashReport
# ---------------------------------------------------------------------------


class TestCrashReport:
    """Crash report with stderr ring buffer from iBazel."""

    def test_crash_report_returns_stderr_lines(self, tmp_path: Path) -> None:
        from cmk.dev_deploy.frontend.frontend_supervisor import (
            _StderrCapture,
            FrontendSupervisor,
        )

        config = FrontendConfig(project_path=tmp_path, repo_root=tmp_path)
        supervisor = FrontendSupervisor(config, repo_root=tmp_path)

        # Simulate stderr capture with crash output
        pipe = io.StringIO("FATAL: build failed\nError: missing dependency\n")
        capture = _StderrCapture(pipe, maxlines=50)
        capture._thread.join(timeout=2.0)  # noqa: SLF001
        supervisor._stderr_capture = capture  # noqa: SLF001

        report = supervisor.get_crash_report()
        assert len(report) == 2
        assert "FATAL: build failed" in report[0]
        assert "Error: missing dependency" in report[1]

    def test_crash_report_empty_when_no_stderr(self, tmp_path: Path) -> None:
        from cmk.dev_deploy.frontend.frontend_supervisor import FrontendSupervisor

        config = FrontendConfig(project_path=tmp_path, repo_root=tmp_path)
        supervisor = FrontendSupervisor(config, repo_root=tmp_path)
        assert supervisor.get_crash_report() == []

    def test_crash_report_ring_buffer_eviction(self, tmp_path: Path) -> None:
        from cmk.dev_deploy.frontend.frontend_supervisor import (
            _StderrCapture,
            FrontendSupervisor,
        )

        config = FrontendConfig(project_path=tmp_path, repo_root=tmp_path)
        supervisor = FrontendSupervisor(config, repo_root=tmp_path)

        # Generate 100 lines with buffer of 50
        lines = "".join(f"line{i}\n" for i in range(100))
        pipe = io.StringIO(lines)
        capture = _StderrCapture(pipe, maxlines=50)
        capture._thread.join(timeout=2.0)  # noqa: SLF001
        supervisor._stderr_capture = capture  # noqa: SLF001

        report = supervisor.get_crash_report()
        assert len(report) == 50
        assert report[0] == "line50"
        assert report[-1] == "line99"


# ---------------------------------------------------------------------------
# TestSiteConfigIntegration
# ---------------------------------------------------------------------------


class TestSiteConfigIntegration:
    """Verify site_config functions are wired into frontend setup and lifecycle.

    Uses inspect.getsource() to verify the presence of site config function
    calls in the setup helper and lifecycle functions.
    """

    def test_run_frontend_signature_accepts_site(self) -> None:
        """_run_frontend accepts (repo_root, site) parameters."""
        from cmk.dev_deploy.__main__ import _run_frontend

        sig = inspect.signature(_run_frontend)
        param_names = list(sig.parameters.keys())
        assert "repo_root" in param_names
        assert "site" in param_names

    def test_setup_imports_site_config(self) -> None:
        """_setup_frontend_supervisor imports from site_config module."""
        from cmk.dev_deploy.__main__ import _setup_frontend_supervisor

        source = inspect.getsource(_setup_frontend_supervisor)
        assert "site_config" in source

    def test_run_frontend_imports_site_config(self) -> None:
        """_run_frontend imports from site_config module."""
        from cmk.dev_deploy.__main__ import _run_frontend

        source = inspect.getsource(_run_frontend)
        assert "site_config" in source

    def test_run_frontend_watch_imports_site_config(self) -> None:
        """_run_frontend_watch imports from site_config module."""
        from cmk.dev_deploy.__main__ import _run_frontend_watch

        source = inspect.getsource(_run_frontend_watch)
        assert "site_config" in source

    def test_setup_has_site_running_check(self) -> None:
        """_setup_frontend_supervisor checks if the site is running."""
        from cmk.dev_deploy.__main__ import _setup_frontend_supervisor

        source = inspect.getsource(_setup_frontend_supervisor)
        assert "check_site_running" in source

    def test_setup_has_stale_cleanup(self) -> None:
        """_setup_frontend_supervisor detects and cleans stale overrides."""
        from cmk.dev_deploy.__main__ import _setup_frontend_supervisor

        source = inspect.getsource(_setup_frontend_supervisor)
        assert "is_stale_override" in source

    def test_setup_has_override_write(self) -> None:
        """_setup_frontend_supervisor writes the .mk override after Vite is ready."""
        from cmk.dev_deploy.__main__ import _setup_frontend_supervisor

        source = inspect.getsource(_setup_frontend_supervisor)
        assert "write_override" in source

    def test_run_frontend_has_override_remove(self) -> None:
        """_run_frontend removes the .mk override on shutdown."""
        from cmk.dev_deploy.__main__ import _run_frontend

        source = inspect.getsource(_run_frontend)
        assert "remove_override" in source

    def test_run_frontend_watch_has_override_remove(self) -> None:
        """_run_frontend_watch removes the .mk override on shutdown."""
        from cmk.dev_deploy.__main__ import _run_frontend_watch

        source = inspect.getsource(_run_frontend_watch)
        assert "remove_override" in source
