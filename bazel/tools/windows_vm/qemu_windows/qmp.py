# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import asyncio
import contextlib
import socket
import time
from collections.abc import Callable, Coroutine, Mapping
from pathlib import Path
from typing import Literal

from qemu.qmp import ExecInterruptedError, ExecuteError, QMPClient, QMPError
from qemu_windows.errors import VmError


class QmpError(VmError):
    """A QMP call that failed, or that QEMU did not answer."""


class QmpConnectionLost(QmpError):
    """The connection broke before QEMU answered: QEMU has most likely exited."""


# How a call failed: an error reply or another failure, a connection that
# broke, no reply in time.
type ErrorKind = Literal["failed", "lost", "timeout"]


class QmpChannel:
    """One connection to a server of QMP's wire protocol, for synchronous
    callers: QEMU's monitor (Qmp) and the guest agent (qga.Qga).

    qemu.qmp is asyncio only: an event loop of its own runs each call to
    completion, so a channel belongs to the thread that created it. Every
    reply must arrive within reply_timeout: the server serves one client at
    a time, and a stopped QEMU accepts but never answers. A late reply to a
    call that timed out is dropped.
    """

    # The protocol and the server, in error messages.
    protocol = "QMP"
    peer = "QEMU"

    def __init__(self, path: Path, alive: Callable[[], bool], reply_timeout: float = 30.0) -> None:
        self._path = path
        self._alive = alive
        self._reply_timeout = reply_timeout
        self._runner = asyncio.Runner()
        self._client = QMPClient()
        self._closed = False

    def close(self) -> None:
        """Disconnects; idempotent."""
        if self._closed:
            return
        self._closed = True
        self._disconnect()
        self._runner.close()

    def _socket(self, timeout: float) -> socket.socket:
        """The connected socket, retrying for up to timeout while alive(), so
        it may follow the QEMU start right away."""
        deadline = time.monotonic() + timeout
        while True:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            # Also bounds connect() itself: with QEMU's one-entry listen
            # backlog taken, it blocks rather than fails.
            sock.settimeout(self._reply_timeout)
            try:
                sock.connect(str(self._path))
                return sock
            except OSError as e:
                sock.close()
                if not self._alive():
                    raise self._error("QEMU has exited") from None
                if time.monotonic() > deadline:
                    raise self._error(f"cannot connect to {self._path}: {e}") from None
                time.sleep(0.2)

    def _disconnect(self) -> None:
        with contextlib.suppress(Exception):
            # Raises what ended the connection, e.g. QEMU exiting on a quit.
            self._runner.run(asyncio.wait_for(self._client.disconnect(), self._reply_timeout))

    def _call[T](
        self, call: Coroutine[object, object, T], context: str, timeout: float | None = None
    ) -> T:
        try:
            return self._runner.run(asyncio.wait_for(call, timeout or self._reply_timeout))
        except TimeoutError:
            raise self._error(f"{self.peer} did not answer {context} in time", "timeout") from None
        except ExecuteError as e:
            raise self._error(f"{context}: {e.error_class}: {e}") from None
        except ExecInterruptedError:
            message = f"{self.protocol} connection lost during {context}"
            raise self._error(message, "lost") from None
        except (QMPError, OSError, EOFError) as e:
            raise self._error(f"{context}: {e}") from None

    def _error(self, message: str, kind: ErrorKind = "failed") -> VmError:
        """What a call raises."""
        return QmpConnectionLost(message) if kind == "lost" else QmpError(message)


class Qmp(QmpChannel):
    """One QMP connection to one QEMU."""

    def __init__(self, path: Path, alive: Callable[[], bool], reply_timeout: float = 30.0) -> None:
        super().__init__(path, alive, reply_timeout)
        # Nobody reads the events, which the default listener would keep.
        self._client.events.event_filter = lambda _event: False

    def connect(self, timeout: float = 60.0) -> None:
        """Connects, retrying for up to timeout while alive(), so it may
        follow the QEMU start right away."""
        # The greeting and qmp_capabilities.
        self._call(self._client.connect(self._socket(timeout)), "the greeting")

    def execute(self, command: str, arguments: Mapping[str, object] | None = None) -> object:
        """The command's "return"; raises QmpError with QMP's error if it fails."""
        return self._call(self._client.execute(command, arguments), command)

    def hmp(self, command_line: str) -> str:
        """An HMP command's output. HMP reports its errors as ordinary output:
        prefer the QMP command where there is one."""
        return str(self.execute("human-monitor-command", {"command-line": command_line}))

    def quit(self) -> None:
        """Asks QEMU to exit, which it may do before it answers."""
        with contextlib.suppress(QmpConnectionLost):
            self._call(self._client.execute("quit"), "quit")
