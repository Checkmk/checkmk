# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import random
import socket
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import override

from qemu_windows.errors import VmError
from qemu_windows.qmp import ErrorKind, QmpChannel

# guest-sync-delimited: the byte that ends whatever qemu-ga had of a request
# and that comes before its reply.
_DELIMITER = b"\xff"


class QgaError(VmError):
    """A guest agent call that failed, or that the guest did not answer."""


class QgaConnectionLost(QgaError):
    """The connection broke before the guest agent answered."""


class QgaTimeout(QgaError):
    """The guest agent did not answer in time."""


class Qga(QmpChannel):
    """The guest agent (qemu-ga) of one VM, through the socket of its
    virtio-serial port.

    QEMU accepts connections whether the guest runs qemu-ga or not, and the
    channel keeps whatever an earlier client left in it: a request half
    sent, replies nobody read. So every connection starts with a resync, and
    a call that fails or times out drops the connection: the next call
    connects again. qemu-ga has no greeting and no capabilities to
    negotiate.
    """

    protocol = "guest agent"
    peer = "the guest agent"

    def __init__(self, path: Path, alive: Callable[[], bool], reply_timeout: float = 30.0) -> None:
        super().__init__(path, alive, reply_timeout)
        self._client.await_greeting = False
        self._client.negotiate = False
        self._connected = False

    def execute(
        self,
        command: str,
        arguments: Mapping[str, object] | None = None,
        *,
        timeout: float | None = None,
    ) -> object:
        """The command's "return"; raises QgaError with qemu-ga's error if it
        fails. timeout bounds the connect and resync, too."""
        try:
            if not self._connected:
                self._connect(timeout or self._reply_timeout)
            return self._call(self._client.execute(command, arguments), command, timeout)
        except QgaError:
            self._disconnect()
            raise

    def _connect(self, timeout: float) -> None:
        sock = self._socket(timeout)
        try:
            _resync(sock, timeout)
        except OSError as e:
            sock.close()
            if isinstance(e, TimeoutError):
                raise QgaTimeout(f"{self.peer} did not answer the resync in time") from None
            raise QgaError(f"resync: {e}") from None
        self._call(self._client.connect(sock), "the connection", timeout)
        self._connected = True

    @override
    def _disconnect(self) -> None:
        self._connected = False
        super()._disconnect()

    @override
    def _error(self, message: str, kind: ErrorKind = "failed") -> VmError:
        if kind == "lost":
            return QgaConnectionLost(message)
        if kind == "timeout":
            return QgaTimeout(message)
        return QgaError(message)


def _resync(sock: socket.socket, timeout: float) -> None:
    """guest-sync-delimited on the raw socket, before qemu.qmp takes it:
    qemu.qmp would fail on the delimiter, and on the reply without an id
    that qemu-ga sends for it (a JSON parse error). Everything up to the
    delimited reply with this id is stale."""
    sync_id = random.randrange(1, 2**31)
    request = {"execute": "guest-sync-delimited", "arguments": {"id": sync_id}}
    sock.sendall(_DELIMITER + json.dumps(request).encode())
    deadline = time.monotonic() + timeout
    received = b""
    delimited = False
    while True:
        # The reply is the last thing the agent sends: only what follows the
        # last delimiter can be it.
        if _DELIMITER in received:
            received = received.rpartition(_DELIMITER)[2]
            delimited = True
        if delimited and received.endswith(b"\n"):
            try:
                if json.loads(received) == {"return": sync_id}:
                    return
            except ValueError:
                pass
        sock.settimeout(max(deadline - time.monotonic(), 0.001))
        if not (chunk := sock.recv(65536)):
            raise ConnectionResetError("the connection was closed")
        received += chunk
