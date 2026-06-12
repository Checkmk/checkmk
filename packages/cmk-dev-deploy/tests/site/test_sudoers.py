# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Unit tests for cmk.dev_deploy.site.sudoers.

The module shells out to ``sudo``/``visudo``; the tests run it against
shim executables placed at the front of ``$PATH``.  ``get_real_user`` is
stubbed by the conftest to return ``"testuser"``.
"""

from __future__ import annotations

import os
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from cmk.dev_deploy.errors import SudoersError
from cmk.dev_deploy.site import sudoers

# Fake sudo: handles -v (authenticate), strips options, executes the command.
# Logs every invocation's arguments so tests can assert command construction.
_FAKE_SUDO = """\
#!/bin/sh
printf '%s\\n' "$*" >> "$SUDO_LOG"
while [ $# -gt 0 ]; do
  case "$1" in
    -v) exit 0 ;;
    -n|--login|--) shift ;;
    -p|-u) shift 2 ;;
    *) break ;;
  esac
done
exec "$@"
"""

# Fake install: copies <src> <dst>, ignoring mode/owner options.
_FAKE_INSTALL = """\
#!/bin/sh
while [ $# -gt 0 ]; do
  case "$1" in
    -m|-o|-g) shift 2 ;;
    *) break ;;
  esac
done
cp "$1" "$2"
"""


@pytest.fixture
def shim_bin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Shim directory at the front of $PATH with a logging fake sudo."""
    bin_dir = tmp_path / "shim-bin"
    bin_dir.mkdir()
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("SUDO_LOG", str(tmp_path / "sudo.log"))
    _write_shim(bin_dir, "sudo", _FAKE_SUDO)
    return bin_dir


def _write_shim(bin_dir: Path, name: str, script: str) -> None:
    shim = bin_dir / name
    shim.write_text(script)
    shim.chmod(0o755)


def _sudo_log(tmp_path: Path) -> list[str]:
    log = tmp_path / "sudo.log"
    return log.read_text().splitlines() if log.is_file() else []


def _interactive(answer: str) -> tuple[AbstractContextManager[Any], AbstractContextManager[Any]]:
    """Patches for a TTY stdin and a canned consent answer."""
    stdin = MagicMock()
    stdin.isatty.return_value = True
    return (
        patch("sys.stdin", stdin),
        patch("builtins.input", return_value=answer),
    )


# ---------------------------------------------------------------------------
# Rule and path construction
# ---------------------------------------------------------------------------


class TestRuleConstruction:
    def test_rule_content(self) -> None:
        assert sudoers.rule_content("v260") == "testuser ALL=(v260) NOPASSWD: ALL\n"

    def test_drop_in_path(self) -> None:
        assert sudoers.drop_in_path("v260") == Path("/etc/sudoers.d/cmk-dev-deploy-testuser-v260")

    def test_drop_in_path_replaces_dots(self) -> None:
        """sudo skips sudoers.d files with dots in their name."""
        path = sudoers.drop_in_path("my.site")
        assert "." not in path.name
        assert path.name == "cmk-dev-deploy-testuser-my_site"

    def test_admin_setup_commands_contains_rule_and_validation(self) -> None:
        commands = sudoers.admin_setup_commands("v260")
        assert "testuser ALL=(v260) NOPASSWD: ALL" in commands
        assert "visudo -cf" in commands
        assert str(sudoers.DEV_VERSIONS_DIR) in commands


# ---------------------------------------------------------------------------
# probe / run_as_site_user
# ---------------------------------------------------------------------------


class TestProbe:
    @pytest.mark.usefixtures("shim_bin")
    def test_true_when_sudo_succeeds(self, tmp_path: Path) -> None:
        assert sudoers.probe("v260") is True
        assert _sudo_log(tmp_path) == ["-n -u v260 -- true"]

    def test_false_when_sudo_fails(self, shim_bin: Path) -> None:
        _write_shim(shim_bin, "sudo", "#!/bin/sh\nexit 1\n")
        assert sudoers.probe("v260") is False

    def test_false_when_sudo_missing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        empty = tmp_path / "empty-bin"
        empty.mkdir()
        monkeypatch.setenv("PATH", str(empty))
        assert sudoers.probe("v260") is False


class TestRunAsSiteUser:
    @pytest.mark.usefixtures("shim_bin")
    def test_command_construction_and_passthrough(self, tmp_path: Path) -> None:
        result = sudoers.run_as_site_user("v260", "echo hello")
        assert result.returncode == 0
        assert result.stdout.strip() == "hello"
        assert _sudo_log(tmp_path) == ["-n --login -u v260 -- bash -c echo hello"]

    @pytest.mark.usefixtures("shim_bin")
    def test_input_text(self) -> None:
        result = sudoers.run_as_site_user("v260", "cat", input_text="piped\n")
        assert result.stdout == "piped\n"


# ---------------------------------------------------------------------------
# bootstrap consent flow
# ---------------------------------------------------------------------------


class TestBootstrap:
    def test_no_tty_raises_with_admin_instructions(self) -> None:
        stdin = MagicMock()
        stdin.isatty.return_value = False
        with patch("sys.stdin", stdin), pytest.raises(SudoersError) as excinfo:
            sudoers.bootstrap("v260")
        assert "testuser ALL=(v260) NOPASSWD: ALL" in str(excinfo.value)

    def test_declined_raises_with_admin_instructions(self) -> None:
        tty, consent = _interactive("n")
        with tty, consent, pytest.raises(SudoersError) as excinfo:
            sudoers.bootstrap("v260")
        assert "declined" in str(excinfo.value)
        assert "visudo -cf" in str(excinfo.value)

    def test_consent_installs_validated_rule(
        self, shim_bin: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_shim(shim_bin, "visudo", "#!/bin/sh\nexit 0\n")
        _write_shim(shim_bin, "install", _FAKE_INSTALL)
        sudoers_dir = tmp_path / "sudoers.d"
        sudoers_dir.mkdir()
        dev_versions = tmp_path / "dev-versions"
        dev_versions.mkdir()  # already writable -> no extra sudo
        monkeypatch.setattr(sudoers, "SUDOERS_DIR", sudoers_dir)
        monkeypatch.setattr(sudoers, "DEV_VERSIONS_DIR", dev_versions)

        tty, consent = _interactive("y")
        with tty, consent:
            sudoers.bootstrap("v260")

        drop_in = sudoers_dir / "cmk-dev-deploy-testuser-v260"
        assert drop_in.read_text() == "testuser ALL=(v260) NOPASSWD: ALL\n"
        log = "\n".join(_sudo_log(tmp_path))
        assert "visudo -cf" in log

    def test_visudo_failure_aborts_install(
        self, shim_bin: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_shim(shim_bin, "visudo", "#!/bin/sh\necho 'syntax error' >&2\nexit 1\n")
        sudoers_dir = tmp_path / "sudoers.d"
        sudoers_dir.mkdir()
        monkeypatch.setattr(sudoers, "SUDOERS_DIR", sudoers_dir)

        tty, consent = _interactive("yes")
        with tty, consent, pytest.raises(SudoersError, match="visudo validation"):
            sudoers.bootstrap("v260")
        assert list(sudoers_dir.iterdir()) == []

    def test_failing_post_install_probe_raises(
        self, shim_bin: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # sudo shim that handles setup but rejects the final probe (-u …)
        _write_shim(
            shim_bin,
            "sudo",
            '#!/bin/sh\ncase "$*" in *" -u "*) exit 1 ;; esac\n' + _FAKE_SUDO.split("\n", 1)[1],
        )
        _write_shim(shim_bin, "visudo", "#!/bin/sh\nexit 0\n")
        _write_shim(shim_bin, "install", _FAKE_INSTALL)
        sudoers_dir = tmp_path / "sudoers.d"
        sudoers_dir.mkdir()
        dev_versions = tmp_path / "dev-versions"
        dev_versions.mkdir()
        monkeypatch.setattr(sudoers, "SUDOERS_DIR", sudoers_dir)
        monkeypatch.setattr(sudoers, "DEV_VERSIONS_DIR", dev_versions)

        tty, consent = _interactive("y")
        with tty, consent, pytest.raises(SudoersError, match="still fails"):
            sudoers.bootstrap("v260")


# ---------------------------------------------------------------------------
# ensure_dev_versions_dir
# ---------------------------------------------------------------------------


class TestEnsureDevVersionsDir:
    @pytest.mark.usefixtures("shim_bin")
    def test_noop_when_writable(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        dev_versions = tmp_path / "dev-versions"
        dev_versions.mkdir()
        monkeypatch.setattr(sudoers, "DEV_VERSIONS_DIR", dev_versions)
        sudoers.ensure_dev_versions_dir()  # must not invoke sudo
        assert not (tmp_path / "sudo.log").exists()

    def test_creates_via_sudo(
        self, shim_bin: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_shim(shim_bin, "chown", "#!/bin/sh\nexit 0\n")
        dev_versions = tmp_path / "dev-versions"
        monkeypatch.setattr(sudoers, "DEV_VERSIONS_DIR", dev_versions)
        sudoers.ensure_dev_versions_dir()
        assert dev_versions.is_dir()

    def test_failure_raises(
        self, shim_bin: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_shim(shim_bin, "sudo", "#!/bin/sh\ncase $1 in -v) exit 0 ;; esac\nexit 1\n")
        monkeypatch.setattr(sudoers, "DEV_VERSIONS_DIR", tmp_path / "dev-versions")
        with pytest.raises(SudoersError, match="Failed to prepare"):
            sudoers.ensure_dev_versions_dir()


# ---------------------------------------------------------------------------
# remove_setup
# ---------------------------------------------------------------------------


class TestRemoveSetup:
    def test_noop_when_nothing_installed(
        self, shim_bin: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_shim(shim_bin, "sudo", "#!/bin/sh\nexit 1\n")  # probe fails
        monkeypatch.setattr(sudoers, "SUDOERS_DIR", tmp_path / "sudoers.d")
        sudoers.remove_setup("v260")  # must not raise

    @pytest.mark.usefixtures("shim_bin")
    def test_removes_drop_in(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        sudoers_dir = tmp_path / "sudoers.d"
        sudoers_dir.mkdir()
        drop_in = sudoers_dir / "cmk-dev-deploy-testuser-v260"
        drop_in.write_text("testuser ALL=(v260) NOPASSWD: ALL\n")
        monkeypatch.setattr(sudoers, "SUDOERS_DIR", sudoers_dir)
        sudoers.remove_setup("v260")
        assert not drop_in.exists()
