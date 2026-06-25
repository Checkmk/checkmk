#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Control the Checkmk Maps backend (a gunicorn daemon).

Invoked by etc/init.d/maps as `cmk-maps-server {start|stop|...}`. Keeping the
process management in Python (rather than the init script) makes it lintable,
type-checked and unit-testable — OMD's init.d tooling around bash is weak.
"""

import argparse
import os
import signal
import subprocess
import sys
import time
from collections.abc import Sequence
from contextlib import suppress
from pathlib import Path

_APPLICATION = "cmk.maps.backend.main:app"

_START_TIMEOUT = 10.0
# Must exceed gunicorn's graceful_timeout (30s in etc/maps/gunicorn.conf.py) so the
# master can finish shutting its workers down gracefully before we escalate to
# SIGKILL.
_GRACEFUL_TIMEOUT = 35.0
_KILL_TIMEOUT = 5.0


def _show(message: str, end: str = "\n") -> None:
    sys.stdout.write(message + end)
    sys.stdout.flush()


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _wait_gone(pid: int, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    iterations = 0
    while _alive(pid):
        if time.monotonic() >= deadline:
            return False
        if iterations % 10 == 0:
            _show(".", end="")
        time.sleep(0.1)
        iterations += 1
    return True


def _send(pid: int, sig: signal.Signals) -> None:
    with suppress(ProcessLookupError):
        os.kill(pid, sig)


def _signal(pid: int | None, sig: signal.Signals) -> int:
    if pid is None or not _alive(pid):
        _show("not running.")
        return 1

    _send(pid, sig)
    _show("OK")
    return 0


class MapsServer:
    def __init__(self, omd_root: Path) -> None:
        self.gunicorn = omd_root / "bin" / "gunicorn"
        self.config = omd_root / "etc" / "maps" / "gunicorn.conf.py"
        self.run_dir = omd_root / "tmp" / "run"
        self.pid_file = self.run_dir / "maps.pid"
        self.socket = self.run_dir / "maps.sock"

    def _pid(self) -> int | None:
        try:
            return int(self.pid_file.read_text())
        except OSError, ValueError:
            return None

    def start(self) -> int:
        _show("Starting maps...", end="")
        pid = self._pid()
        if pid is not None and _alive(pid):
            _show("already running.")
            return 0

        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.socket.unlink(missing_ok=True)

        result = subprocess.run(
            [
                str(self.gunicorn),
                "-D",
                "-p",
                str(self.pid_file),
                "-c",
                str(self.config),
                _APPLICATION,
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            _show(f"failed\n{result.stderr}")
            return 1

        # gunicorn -D returns as soon as the master has forked. Wait until the
        # master is alive AND the worker has bound the socket, so callers (and
        # tests) never race a process that exists but isn't listening yet.
        deadline = time.monotonic() + _START_TIMEOUT
        iterations = 0
        while time.monotonic() < deadline:
            pid = self._pid()
            if pid is not None and _alive(pid) and self.socket.exists():
                _show("OK")
                return 0

            if iterations % 10 == 0:
                _show(".", end="")
            time.sleep(0.1)
            iterations += 1

        _show("failed")
        return 1

    def stop(self) -> int:
        _show("Stopping maps...", end="")
        pid = self._pid()

        if pid is None:
            _show("not running.")
            return 0

        if not _alive(pid):
            self.pid_file.unlink(missing_ok=True)
            _show("not running (PID file orphaned)")
            return 0

        _show(f"killing {pid}.", end="")
        _send(pid, signal.SIGTERM)

        if _wait_gone(pid, _GRACEFUL_TIMEOUT):
            _show("OK")
            return 0

        _show("sending SIGKILL.", end="")
        with suppress(ProcessLookupError):
            os.killpg(os.getpgid(pid), signal.SIGKILL)

        if _wait_gone(pid, _KILL_TIMEOUT):
            _show("OK")
            return 0

        _show("failed")
        return 1

    def restart(self) -> int:
        _show("Restarting maps...")
        if self.stop() != 0:
            return 1
        return self.start()

    def reload(self) -> int:
        # SIGHUP = gunicorn graceful reload: the master stays up and brings new
        # workers in before draining the old one, so there is no window without a
        # listening socket and reconnecting SSE clients hit the new worker at once.
        _show("Reloading maps...", end="")
        pid = self._pid()
        if pid is None or not _alive(pid):
            return self.start()
        _send(pid, signal.SIGHUP)
        _show("OK")
        return 0

    def logrotate(self) -> int:
        # SIGUSR1 makes gunicorn reopen its log files; invoked by the logrotate
        # postrotate hook (see etc/logrotate.d/maps).
        _show("Rotating logs of maps...", end="")
        return _signal(self._pid(), signal.SIGUSR1)

    def status(self) -> int:
        _show("Checking status of maps...", end="")
        pid = self._pid()
        if pid is None:
            _show("not running (PID file missing)")
            return 1
        if not _alive(pid):
            _show("not running (PID file orphaned)")
            return 1

        _show(f"running (PID {pid})")
        return 0


COMMANDS = ("start", "stop", "restart", "reload", "logrotate", "status")


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(prog="cmk-maps-server", description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in COMMANDS:
        subparsers.add_parser(command)

    args = parser.parse_args(argv)
    server = MapsServer(Path(os.environ["OMD_ROOT"]))

    match args.command:
        case "start":
            return server.start()
        case "stop":
            return server.stop()
        case "restart":
            return server.restart()
        case "reload":
            return server.reload()
        case "logrotate":
            return server.logrotate()
        case "status":
            return server.status()
        case _:
            raise NotImplementedError


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
