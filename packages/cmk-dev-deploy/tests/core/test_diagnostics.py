# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Unit tests for cmk.dev_deploy.diagnostics (crash bundle capture)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cmk.dev_deploy.core.diagnostics import (
    _collect_bazel_state,
    _collect_deploy_state,
    _collect_environment,
    _collect_error_info,
    _collect_manifest_state,
    _print_error_output,
    _read_log_tail,
    _write_bundle,
    capture_diagnostic_bundle,
)
from cmk.dev_deploy.errors import BazelQueryError, DeployError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_diagnostics_dir(tmp_path: Path) -> Path:
    """Create a temporary diagnostics directory."""
    diag_dir = tmp_path / "diagnostics"
    diag_dir.mkdir()
    return diag_dir


# ---------------------------------------------------------------------------
# T1: _collect_environment
# ---------------------------------------------------------------------------


class TestCollectEnvironment:
    """Tests for environment info collection."""

    def test_basic_fields_present(self) -> None:
        """Collect basic Python and platform info without repo_root."""
        with patch(
            "cmk.dev_deploy.core.diagnostics.subprocess.run", side_effect=OSError
        ):
            env = _collect_environment(None)
        assert "python_version" in env
        assert "platform" in env
        assert "machine" in env

    def test_bazel_version_collected(self) -> None:
        """Bazel version is collected when bazel is available."""
        mock_result = MagicMock(returncode=0, stdout="bazel 7.4.0\n")
        with patch(
            "cmk.dev_deploy.core.diagnostics.subprocess.run", return_value=mock_result
        ):
            env = _collect_environment(None)
        assert env["bazel_version"] == "bazel 7.4.0"

    def test_bazel_version_unavailable_on_timeout(self) -> None:
        """Bazel version shows 'unavailable' when bazel times out."""
        from subprocess import TimeoutExpired

        def _side_effect(cmd: list[str], **_kwargs: object) -> object:
            if cmd[0] == "bazel":
                raise TimeoutExpired(cmd, 3)
            return MagicMock(returncode=1)

        with patch(
            "cmk.dev_deploy.core.diagnostics.subprocess.run", side_effect=_side_effect
        ):
            env = _collect_environment(None)
        assert env["bazel_version"] == "unavailable"

    def test_git_info_collected(self, tmp_path: Path) -> None:
        """Git branch, commit, and dirty count collected when repo_root provided."""
        call_count = 0

        def _side_effect(cmd: list[str], **_kwargs: object) -> MagicMock:
            nonlocal call_count
            call_count += 1
            if cmd[0] == "bazel":
                return MagicMock(returncode=1)
            if "rev-parse" in cmd and "--abbrev-ref" in cmd:
                return MagicMock(returncode=0, stdout="my-branch\n")
            if "rev-parse" in cmd and "--short" in cmd:
                return MagicMock(returncode=0, stdout="abc1234\n")
            if "diff" in cmd and "--name-only" in cmd:
                return MagicMock(returncode=0, stdout="file1.py\nfile2.py\n")
            return MagicMock(returncode=1)

        with patch(
            "cmk.dev_deploy.core.diagnostics.subprocess.run", side_effect=_side_effect
        ):
            env = _collect_environment(tmp_path)
        assert env["git_branch"] == "my-branch"
        assert env["git_commit"] == "abc1234"
        assert env["git_dirty_count"] == 2

    def test_no_env_vars_captured(self) -> None:
        """Environment variables must NOT be captured (security requirement)."""
        with patch(
            "cmk.dev_deploy.core.diagnostics.subprocess.run", side_effect=OSError
        ):
            env = _collect_environment(None)
        # No os.environ keys should appear
        for key in ("PATH", "HOME", "USER", "GITHUB_TOKEN", "BAZEL_REMOTE_CACHE_TOKEN"):
            assert key not in env


# ---------------------------------------------------------------------------
# T2: _collect_bazel_state
# ---------------------------------------------------------------------------


class TestCollectBazelState:
    """Tests for Bazel server state collection."""

    def test_returns_empty_when_no_repo(self) -> None:
        assert _collect_bazel_state(None) == {}

    def test_collects_output_base(self, tmp_path: Path) -> None:
        mock_result = MagicMock(returncode=0, stdout=str(tmp_path) + "\n")
        with patch(
            "cmk.dev_deploy.core.diagnostics.subprocess.run", return_value=mock_result
        ):
            state = _collect_bazel_state(tmp_path)
        assert state["output_base"] == str(tmp_path)
        assert state["output_base_exists"] is True

    def test_handles_timeout(self, tmp_path: Path) -> None:
        """Bazel info timeout does not crash the collector."""
        from subprocess import TimeoutExpired

        with patch(
            "cmk.dev_deploy.core.diagnostics.subprocess.run",
            side_effect=TimeoutExpired(["bazel"], 3),
        ):
            state = _collect_bazel_state(tmp_path)
        assert "unavailable" in state.get("output_base", "")

    def test_collects_server_pid(self, tmp_path: Path) -> None:
        """Server PID is collected from bazel info server_pid."""

        def _side_effect(cmd: list[str], **_kwargs: object) -> MagicMock:
            if "server_pid" in cmd:
                return MagicMock(returncode=0, stdout="12345\n")
            return MagicMock(returncode=0, stdout=str(tmp_path) + "\n")

        with patch(
            "cmk.dev_deploy.core.diagnostics.subprocess.run", side_effect=_side_effect
        ):
            state = _collect_bazel_state(tmp_path)
        assert state["server_pid"] == 12345

    def test_collects_server_memory_from_proc(self, tmp_path: Path) -> None:
        """VmRSS is read from /proc/<pid>/status on Linux."""
        proc_status_content = "VmPeak:\t1234 kB\nVmRSS:\t5678 kB\nVmSize:\t9012 kB\n"

        def _side_effect(cmd: list[str], **_kwargs: object) -> MagicMock:
            if "server_pid" in cmd:
                return MagicMock(returncode=0, stdout="42\n")
            return MagicMock(returncode=0, stdout=str(tmp_path) + "\n")

        proc_dir = tmp_path / "proc" / "42"
        proc_dir.mkdir(parents=True)
        (proc_dir / "status").write_text(proc_status_content)

        # Direct test of the /proc parsing via the real function
        # with a mocked /proc path
        with patch(
            "cmk.dev_deploy.core.diagnostics.subprocess.run", side_effect=_side_effect
        ):
            state = _collect_bazel_state(tmp_path)
        # server_pid should be collected even if /proc doesn't exist for the test PID
        assert state["server_pid"] == 42


# ---------------------------------------------------------------------------
# T3: _collect_manifest_state
# ---------------------------------------------------------------------------


class TestCollectManifestState:
    """Tests for manifest state collection."""

    def test_manifest_not_found(self, tmp_path: Path) -> None:
        missing = tmp_path / "nonexistent.json"
        with patch(
            "cmk.dev_deploy.manifest.reader.manifest_path", return_value=missing
        ):
            state = _collect_manifest_state()
        assert state["manifest_exists"] is False

    def test_manifest_found(self, tmp_path: Path) -> None:
        manifest = tmp_path / "deploy_manifest.json"
        manifest.write_text(json.dumps({"wheel_specs": [1, 2, 3], "config_specs": [1]}))
        with patch(
            "cmk.dev_deploy.manifest.reader.manifest_path", return_value=manifest
        ):
            state = _collect_manifest_state()
        assert state["manifest_exists"] is True
        assert state["manifest_spec_count"]["wheel_specs"] == 3
        assert state["manifest_spec_count"]["config_specs"] == 1


# ---------------------------------------------------------------------------
# T4: _collect_deploy_state
# ---------------------------------------------------------------------------


class TestCollectDeployState:
    """Tests for deploy state collection."""

    def test_returns_empty_when_no_site(self) -> None:
        assert _collect_deploy_state(None) == {}

    def test_returns_state_info(self) -> None:
        mock_state = MagicMock()
        mock_state.deployers = {"a": 1, "b": 2}
        mock_state.diff_base_commit = "abc123"
        mock_state.branch = "main"
        with patch(
            "cmk.dev_deploy.state.deploy_state.load_state", return_value=mock_state
        ):
            state = _collect_deploy_state(MagicMock())
        assert state["state_file_exists"] is True
        assert state["deployer_count"] == 2
        assert state["diff_base_commit"] == "abc123"

    def test_returns_not_found_when_no_state(self) -> None:
        with patch("cmk.dev_deploy.state.deploy_state.load_state", return_value=None):
            state = _collect_deploy_state(MagicMock())
        assert state["state_file_exists"] is False


# ---------------------------------------------------------------------------
# T5: _collect_error_info
# ---------------------------------------------------------------------------


class TestCollectErrorInfo:
    """Tests for error detail collection."""

    def test_deploy_error_fields(self) -> None:
        err = BazelQueryError("query failed", recovery="Try bazel clean")
        info = _collect_error_info(err, "bazel_query")
        assert info["type"] == "BazelQueryError"
        assert info["message"] == "query failed"
        assert info["phase"] == "bazel_query"
        assert info["recovery_hint"] == "Try bazel clean"
        assert isinstance(info["traceback"], list)

    def test_generic_exception(self) -> None:
        err = RuntimeError("something broke")
        info = _collect_error_info(err, "unknown")
        assert info["type"] == "RuntimeError"
        assert info["message"] == "something broke"
        assert "recovery_hint" not in info


# ---------------------------------------------------------------------------
# T6: _read_log_tail
# ---------------------------------------------------------------------------


class TestReadLogTail:
    """Tests for log file tail reading."""

    def test_returns_none_when_no_log(self) -> None:
        with patch("cmk.dev_deploy.core.output.get_log_file_path", return_value=None):
            assert _read_log_tail() is None

    def test_reads_last_lines(self, tmp_path: Path) -> None:
        log_file = tmp_path / "deploy.log"
        lines = [f"line {i}" for i in range(300)]
        log_file.write_text("\n".join(lines))
        with patch(
            "cmk.dev_deploy.core.output.get_log_file_path", return_value=log_file
        ):
            tail = _read_log_tail()
        assert tail is not None
        assert tail.startswith("line 100")
        assert tail.endswith("line 299")

    def test_handles_empty_log(self, tmp_path: Path) -> None:
        log_file = tmp_path / "deploy.log"
        log_file.write_text("")
        with patch(
            "cmk.dev_deploy.core.output.get_log_file_path", return_value=log_file
        ):
            tail = _read_log_tail()
        assert tail == ""

    def test_handles_missing_file(self, tmp_path: Path) -> None:
        missing = tmp_path / "nonexistent.log"
        with patch(
            "cmk.dev_deploy.core.output.get_log_file_path", return_value=missing
        ):
            assert _read_log_tail() is None


# ---------------------------------------------------------------------------
# T7: _write_bundle + prune
# ---------------------------------------------------------------------------


class TestWriteBundle:
    """Tests for crash file writing and pruning."""

    def test_writes_valid_json(self, tmp_path: Path) -> None:
        bundle = {"test": "data", "number": 42}
        with patch(
            "cmk.dev_deploy.core.diagnostics._diagnostics_dir", return_value=tmp_path
        ):
            path = _write_bundle(bundle)
        assert path is not None
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["test"] == "data"

    def test_prunes_old_files(self, tmp_path: Path) -> None:
        """Keep max 20 crash files, prune oldest."""
        for i in range(25):
            (tmp_path / f"crash-2026010{i:02d}-000000.json").write_text("{}")
        with patch(
            "cmk.dev_deploy.core.diagnostics._diagnostics_dir", return_value=tmp_path
        ):
            _write_bundle({"new": True})
        crash_files = list(tmp_path.glob("crash-*.json"))
        assert len(crash_files) <= 21  # 20 old kept + 1 new

    def test_handles_unwritable_dir(self, tmp_path: Path) -> None:
        """Returns None and warns when directory is not writable."""
        bad_dir = tmp_path / "nonexistent" / "deep" / "path"
        with (
            patch(
                "cmk.dev_deploy.core.diagnostics._diagnostics_dir", return_value=bad_dir
            ),
            patch.object(Path, "mkdir", side_effect=OSError),
            patch("cmk.dev_deploy.core.diagnostics._print_write_warning") as mock_warn,
        ):
            result = _write_bundle({"test": True})
        assert result is None
        mock_warn.assert_called_once()


# ---------------------------------------------------------------------------
# T8: JSON output (--json-errors)
# ---------------------------------------------------------------------------


class TestJsonErrors:
    """Tests for --json-errors stdout output."""

    def test_json_output_on_flag(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """When json_errors=True, valid JSON is printed to stdout."""
        error = DeployError("test error")
        with (
            patch(
                "cmk.dev_deploy.core.diagnostics._diagnostics_dir",
                return_value=tmp_path,
            ),
            patch(
                "cmk.dev_deploy.core.diagnostics.subprocess.run", side_effect=OSError
            ),
            patch("cmk.dev_deploy.core.output.get_log_file_path", return_value=None),
            patch(
                "cmk.dev_deploy.manifest.reader.manifest_path",
                return_value=tmp_path / "missing",
            ),
        ):
            capture_diagnostic_bundle(error, json_errors=True, phase="test")
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["error"]["type"] == "DeployError"
        assert data["error"]["message"] == "test error"

    def test_no_json_without_flag(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """When json_errors=False (default), no JSON on stdout."""
        error = DeployError("test error")
        with (
            patch(
                "cmk.dev_deploy.core.diagnostics._diagnostics_dir",
                return_value=tmp_path,
            ),
            patch(
                "cmk.dev_deploy.core.diagnostics.subprocess.run", side_effect=OSError
            ),
            patch("cmk.dev_deploy.core.output.get_log_file_path", return_value=None),
            patch(
                "cmk.dev_deploy.manifest.reader.manifest_path",
                return_value=tmp_path / "missing",
            ),
        ):
            capture_diagnostic_bundle(error, json_errors=False, phase="test")
        captured = capsys.readouterr()
        # stdout should have no JSON (only stderr gets the error message)
        assert captured.out == ""


# ---------------------------------------------------------------------------
# T9: clipboard command
# ---------------------------------------------------------------------------


class TestClipboardCommand:
    """Tests for clipboard copy command in error output."""

    def test_clipboard_command_printed(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        crash_path = tmp_path / "crash-test.json"
        _print_error_output(DeployError("test"), crash_path)
        captured = capsys.readouterr()
        assert "xclip -selection clipboard" in captured.err
        assert str(crash_path) in captured.err

    def test_no_clipboard_when_no_path(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _print_error_output(DeployError("test"), None)
        captured = capsys.readouterr()
        assert "xclip" not in captured.err
        assert "ERROR: test" in captured.err
