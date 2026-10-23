# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import signal
import subprocess
from pathlib import Path

import pytest

from cmk.maps.backend.server import main as srv


@pytest.fixture(name="server")
def _server(tmp_path: Path) -> srv.MapsServer:
    (tmp_path / "tmp" / "run").mkdir(parents=True)
    return srv.MapsServer(tmp_path)


def _write_pid(server: srv.MapsServer, pid: int) -> None:
    server.pid_file.write_text(str(pid))


def test_pid_ignores_garbage(server: srv.MapsServer) -> None:
    server.pid_file.write_text("not-a-pid")
    assert server._pid() is None  # noqa: SLF001


def test_status_no_pidfile(server: srv.MapsServer, capsys: pytest.CaptureFixture[str]) -> None:
    assert server.status() == 1
    assert "not running (PID file missing)" in capsys.readouterr().out


def test_status_orphaned(server: srv.MapsServer, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_pid(server, 4242)
    monkeypatch.setattr(srv, "_alive", lambda _pid: False)
    assert server.status() == 1


def test_status_running(
    server: srv.MapsServer,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_pid(server, 4242)
    monkeypatch.setattr(srv, "_alive", lambda _pid: True)
    assert server.status() == 0
    assert "running (PID 4242)" in capsys.readouterr().out


def test_stop_not_running(server: srv.MapsServer) -> None:
    assert server.stop() == 0


def test_stop_orphaned_removes_pidfile(
    server: srv.MapsServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_pid(server, 4242)
    monkeypatch.setattr(srv, "_alive", lambda _pid: False)
    assert server.stop() == 0
    assert not server.pid_file.exists()


def test_stop_graceful_sends_sigterm(
    server: srv.MapsServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_pid(server, 4242)
    monkeypatch.setattr(srv, "_alive", lambda _pid: True)
    monkeypatch.setattr(srv, "_wait_gone", lambda _pid, _timeout: True)
    sent: list[tuple[int, signal.Signals]] = []
    monkeypatch.setattr(srv, "_send", lambda pid, sig: sent.append((pid, sig)))
    assert server.stop() == 0
    assert sent == [(4242, signal.SIGTERM)]


def test_reload_falls_back_to_start_when_down(
    server: srv.MapsServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(srv, "_alive", lambda _pid: False)
    calls: list[str] = []

    def _fake_start() -> int:
        calls.append("start")
        return 0

    monkeypatch.setattr(server, "start", _fake_start)
    assert server.reload() == 0
    assert calls == ["start"]


def test_reload_sends_sighup(server: srv.MapsServer, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_pid(server, 4242)
    monkeypatch.setattr(srv, "_alive", lambda _pid: True)
    sent: list[tuple[int, signal.Signals]] = []
    monkeypatch.setattr(srv, "_send", lambda pid, sig: sent.append((pid, sig)))
    assert server.reload() == 0
    assert sent == [(4242, signal.SIGHUP)]


def test_logrotate_sends_sigusr1(server: srv.MapsServer, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_pid(server, 4242)
    monkeypatch.setattr(srv, "_alive", lambda _pid: True)
    sent: list[tuple[int, signal.Signals]] = []
    monkeypatch.setattr(srv, "_send", lambda pid, sig: sent.append((pid, sig)))
    assert server.logrotate() == 0
    assert sent == [(4242, signal.SIGUSR1)]


def test_logrotate_not_running(server: srv.MapsServer, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(srv, "_alive", lambda _pid: False)
    assert server.logrotate() == 1


def test_start_already_running(
    server: srv.MapsServer,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_pid(server, 4242)
    monkeypatch.setattr(srv, "_alive", lambda _pid: True)
    assert server.start() == 0
    assert "already running." in capsys.readouterr().out


def test_start_waits_for_socket(server: srv.MapsServer, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(srv, "_alive", lambda _pid: True)

    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:  # noqa: ARG001
        server.pid_file.write_text("4242")
        server.socket.touch()
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert server.start() == 0


def test_start_fails_when_socket_never_binds(
    server: srv.MapsServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(srv, "_alive", lambda _pid: True)
    monkeypatch.setattr(srv, "_START_TIMEOUT", 0.3)

    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:  # noqa: ARG001
        server.pid_file.write_text("4242")  # process up, but socket never appears
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert server.start() == 1


def test_start_reports_gunicorn_failure(
    server: srv.MapsServer,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:  # noqa: ARG001
        return subprocess.CompletedProcess(cmd, 1, "", "boom")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert server.start() == 1
    assert "failed" in capsys.readouterr().out


def test_main_requires_a_command(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("OMD_ROOT", str(tmp_path))
    with pytest.raises(SystemExit):
        srv.main([])


def test_main_dispatches_to_status(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("OMD_ROOT", str(tmp_path))
    assert srv.main(["status"]) == 1  # nothing running under a fresh OMD_ROOT
