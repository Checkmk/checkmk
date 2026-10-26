# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import shutil
import socket
import tempfile
import threading
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Protocol

import pytest
from qemu_windows.qmp import Qmp, QmpError

_GREETING = {
    "QMP": {"version": {"qemu": {"micro": 1, "minor": 1, "major": 11}}, "capabilities": []}
}
# What a handler returns to make the server hang up instead of answering.
HANG_UP: dict[str, object] = {"hang up": True}

Message = dict[str, object]
Handler = Callable[[Message], list[Message] | None]


class FakeQmpServer:
    """A QMP server for one client: answers qmp_capabilities itself and every
    other command with the messages handler returns for it (None: no answer)."""

    def __init__(self, path: Path, handler: Handler) -> None:
        self._listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._listener.bind(str(path))
        self._listener.listen(1)
        self._handler = handler
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def _serve(self) -> None:
        conn, _ = self._listener.accept()
        with conn:
            conn.sendall(json.dumps(_GREETING).encode() + b"\n")
            for message in self._messages(conn):
                if message["execute"] == "qmp_capabilities":
                    replies: list[Message] | None = [{"return": {}}]
                else:
                    replies = self._handler(message)
                for reply in replies or []:
                    if reply is HANG_UP:
                        return
                    if "event" not in reply and "id" in message:
                        reply = {**reply, "id": message["id"]}
                    conn.sendall(json.dumps(reply).encode() + b"\n")

    @staticmethod
    def _messages(conn: socket.socket) -> Iterator[Message]:
        # A JSON stream, like QEMU reads it: clients need not end a message
        # with a newline.
        decoder = json.JSONDecoder()
        buffer = ""
        while chunk := conn.recv(4096):
            buffer += chunk.decode()
            while buffer.strip():
                try:
                    message, end = decoder.raw_decode(buffer.lstrip())
                except json.JSONDecodeError:
                    break
                buffer = buffer.lstrip()[end:]
                if not isinstance(message, dict):
                    raise RuntimeError(f"not a QMP message: {message!r}")
                yield message


@pytest.fixture(name="socket_path")
def fixture_socket_path() -> Iterator[Path]:
    # Not tmp_path: socket paths end at 108 bytes.
    directory = Path(tempfile.mkdtemp(dir="/tmp"))
    yield directory / "qmp"
    shutil.rmtree(directory)


class QmpTo(Protocol):
    def __call__(self, alive: Callable[[], bool] = ..., reply_timeout: float = ...) -> Qmp: ...


class Connect(Protocol):
    def __call__(self, handler: Handler, reply_timeout: float = ...) -> Qmp: ...


@pytest.fixture(name="qmp_to")
def fixture_qmp_to(socket_path: Path) -> Iterator[QmpTo]:
    """Makes Qmps to socket_path, closed after the test."""
    made: list[Qmp] = []

    def make(alive: Callable[[], bool] = lambda: True, reply_timeout: float = 5.0) -> Qmp:
        made.append(Qmp(socket_path, alive, reply_timeout))
        return made[-1]

    yield make
    for qmp in made:
        qmp.close()


@pytest.fixture(name="connected")
def fixture_connected(socket_path: Path, qmp_to: QmpTo) -> Connect:
    """A Qmp connected to a FakeQmpServer with the given handler."""

    def connect(handler: Handler, reply_timeout: float = 5.0) -> Qmp:
        FakeQmpServer(socket_path, handler)
        qmp = qmp_to(reply_timeout=reply_timeout)
        qmp.connect()
        return qmp

    return connect


def test_command_returns_its_qmp_return(connected: Connect) -> None:
    qmp = connected(lambda _message: [{"return": {"status": "running"}}])

    assert qmp.execute("query-status") == {"status": "running"}


def test_events_before_the_reply_are_skipped(connected: Connect) -> None:
    qmp = connected(lambda _message: [{"event": "STOP"}, {"return": {}}])

    assert qmp.execute("stop") == {}


def test_hmp_command_returns_its_output(connected: Connect) -> None:
    def handler(message: Message) -> list[Message]:
        arguments = message["arguments"]
        assert isinstance(arguments, dict)
        return [{"return": f"ran {arguments['command-line']}"}]

    qmp = connected(handler)

    assert qmp.hmp("info usernet") == "ran info usernet"


def test_error_reply_raises_with_the_qmp_error_class(connected: Connect) -> None:
    qmp = connected(
        lambda _message: [{"error": {"class": "CommandNotFound", "desc": "no such command"}}],
    )

    with pytest.raises(QmpError, match="nope: CommandNotFound: no such command"):
        qmp.execute("nope")


def test_unanswered_command_times_out(connected: Connect) -> None:
    qmp = connected(lambda _message: None, reply_timeout=0.2)

    with pytest.raises(QmpError, match="QEMU did not answer query-status in time"):
        qmp.execute("query-status")


def test_quit_succeeds_when_qemu_exits_before_it_answers(connected: Connect) -> None:
    qmp = connected(lambda _message: [HANG_UP])

    qmp.quit()


def test_lost_connection_fails_other_commands(connected: Connect) -> None:
    qmp = connected(lambda _message: [HANG_UP])

    with pytest.raises(QmpError, match="connection lost during query-status"):
        qmp.execute("query-status")


def test_connect_waits_for_a_socket_that_appears_later(socket_path: Path, qmp_to: QmpTo) -> None:
    threading.Timer(0.3, FakeQmpServer, (socket_path, lambda _m: [{"return": {}}])).start()
    qmp = qmp_to()

    qmp.connect(timeout=10)

    assert qmp.execute("cont") == {}


def test_connect_gives_up_at_once_when_qemu_has_exited(qmp_to: QmpTo) -> None:
    qmp = qmp_to(alive=lambda: False)
    start = time.monotonic()

    with pytest.raises(QmpError, match="QEMU has exited"):
        qmp.connect(timeout=60)

    assert time.monotonic() - start < 5
