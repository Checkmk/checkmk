# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Guest through a fake guest agent on a Unix socket, which speaks the
protocol as qemu-ga 110.2.3 on Windows does."""

import base64
import json
import os
import shutil
import socket
import tempfile
import threading
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import pytest
from qemu_windows.errors import VmError
from qemu_windows.guest import Guest, GuestError
from qemu_windows.qga import Qga

Message = dict[str, object]
# Replies the guest may lose without a word (guest._READ_CHUNK); the fake
# always does.
_MAX_REPLY = 512 * 1024


@dataclass
class Program:
    """What a program the agent starts reports once it has exited, after
    `polls` status queries that find it still running."""

    exitcode: int = 0
    signal: int | None = None
    out: bytes = b""
    err: bytes = b""
    polls: int = 0


class FakeQga:
    """qemu-ga for one client at a time, any number of connections in turn.

    Each connection starts with `stale`, an earlier client's leftovers. A
    guest-exec runs programs(argv), None for a program that is not there.
    Commands in `unanswered` get no reply, those in `errors` that error.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self.programs: Callable[[list[str]], Program | None] = lambda _argv: Program()
        self.stale = b""
        self.unanswered: set[str] = set()
        self.errors: dict[str, str] = {}
        # Bytes per guest-file-write it writes (None: all).
        self.write_limit: int | None = None
        self.files: dict[str, bytes] = {}
        self.started: list[list[str]] = []
        self.clock: object = None
        self.powered_off = False
        self._processes: dict[int, Program] = {}
        self._handles: dict[int, tuple[str, int]] = {}
        self._listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._listener.bind(str(path))
        self._listener.listen(1)
        threading.Thread(target=self._serve, daemon=True).start()

    def _serve(self) -> None:
        while True:
            conn, _ = self._listener.accept()
            with conn:
                conn.sendall(self.stale)
                for request in self._requests(conn):
                    if (reply := self._answer(request)) is not None and len(reply) < _MAX_REPLY:
                        conn.sendall(reply)

    @staticmethod
    def _requests(conn: socket.socket) -> Iterator[Message | None]:
        """The requests; None for each 0xFF, which resets the parser: a
        request it cuts short is dropped."""
        decoder = json.JSONDecoder()
        buffer = b""
        while chunk := conn.recv(65536):
            buffer += chunk
            while buffer := buffer.lstrip():
                if buffer.startswith(b"\xff"):
                    buffer = buffer[1:]
                    yield None
                    continue
                end = buffer.find(b"\xff")
                text = (buffer if end < 0 else buffer[:end]).decode()
                try:
                    message, length = decoder.raw_decode(text)
                except json.JSONDecodeError:
                    if end < 0:
                        break
                    buffer = buffer[end:]
                    continue
                buffer = buffer[len(text[:length].encode()) :]
                yield message

    def _answer(self, request: Message | None) -> bytes | None:
        if request is None:
            error = {"class": "GenericError", "desc": "JSON parse error, stray '\\uFFFD'"}
            return json.dumps({"error": error}).encode() + b"\n"
        command = str(request["execute"])
        arguments = request.get("arguments", {})
        assert isinstance(arguments, dict)
        if command in self.unanswered:
            return None
        if command == "guest-sync-delimited":
            return b"\xff" + json.dumps({"return": arguments["id"]}).encode() + b"\n"
        if command == "guest-shutdown" and command not in self.errors:
            self.powered_off = True
            return None
        try:
            reply: Message = {"return": self._execute(command, arguments)}
        except LookupError as e:
            reply = {"error": {"class": "GenericError", "desc": str(e.args[0])}}
        if "id" in request:
            reply["id"] = request["id"]
        return json.dumps(reply).encode() + b"\n"

    def _execute(self, command: str, arguments: dict[str, object]) -> object:
        if command in self.errors:
            raise LookupError(self.errors[command])
        match command:
            case "guest-ping":
                return {}
            case "guest-exec":
                arg = arguments.get("arg", [])
                assert isinstance(arg, list)
                argv = [str(arguments["path"]), *map(str, arg)]
                self.started.append(argv)
                if (program := self.programs(argv)) is None:
                    raise LookupError("Failed to execute child process (No such file or directory)")
                pid = 1000 + len(self.started)
                self._processes[pid] = program
                return {"pid": pid}
            case "guest-exec-status":
                return self._status(self._processes[_int(arguments["pid"])])
            case "guest-file-open":
                path = str(arguments["path"])
                if arguments["mode"] == "wb":
                    self.files[path] = b""
                elif path not in self.files:
                    raise LookupError(
                        f"failed to open file '{path}' (mode: 'rb'):"
                        " The system cannot find the file specified."
                    )
                handle = 1000 + len(self._handles)
                self._handles[handle] = (path, 0)
                return handle
            case "guest-file-read":
                path, position = self._handles[handle := _int(arguments["handle"])]
                data = self.files[path][position : position + _int(arguments["count"])]
                self._handles[handle] = (path, position + len(data))
                return {
                    "count": len(data),
                    "buf-b64": base64.b64encode(data).decode(),
                    "eof": position + len(data) >= len(self.files[path]),
                }
            case "guest-file-write":
                path, _position = self._handles[_int(arguments["handle"])]
                data = base64.b64decode(str(arguments["buf-b64"]))[: self.write_limit]
                self.files[path] += data
                return {"count": len(data), "eof": False}
            case "guest-file-close":
                del self._handles[_int(arguments["handle"])]
                return {}
            case "guest-set-time":
                self.clock = arguments["time"]
                return {}
            case _:
                raise LookupError(f"The command {command} has not been found")

    @staticmethod
    def _status(program: Program) -> Message:
        if program.polls > 0:
            program.polls -= 1
            return {"exited": False}
        status: Message = {"exited": True}
        if program.signal is None:
            status["exitcode"] = program.exitcode
        else:
            status["signal"] = program.signal
        for stream, data in (("out", program.out), ("err", program.err)):
            if data:
                status[f"{stream}-data"] = base64.b64encode(data).decode()
                status[f"{stream}-truncated"] = False
        return status


def _int(value: object) -> int:
    assert isinstance(value, int)
    return value


class Connect(Protocol):
    def __call__(self, check: Callable[[], None] = ...) -> Guest: ...


@pytest.fixture(name="socket_path")
def fixture_socket_path() -> Iterator[Path]:
    # Not tmp_path: socket paths end at 108 bytes.
    directory = Path(tempfile.mkdtemp(dir="/tmp"))
    yield directory / "qga"
    shutil.rmtree(directory)


@pytest.fixture(name="agent")
def fixture_agent(socket_path: Path) -> FakeQga:
    return FakeQga(socket_path)


@pytest.fixture(name="connect")
def fixture_connect(agent: FakeQga) -> Iterator[Connect]:
    """Makes Guests on the fake agent, with the check() given; closed after
    the test."""
    made: list[Qga] = []

    def connect(check: Callable[[], None] = lambda: None) -> Guest:
        made.append(Qga(agent.path, lambda: True, reply_timeout=1.0))
        return Guest(made[-1], check)

    yield connect
    for qga in made:
        qga.close()


@pytest.fixture(name="guest")
def fixture_guest(connect: Connect) -> Guest:
    return connect()


def test_output_has_its_carriage_returns_removed(agent: FakeQga, guest: Guest) -> None:
    agent.programs = lambda _argv: Program(out=b"C:\\>\r\nok\r\n")

    assert guest.run(["cmd.exe", "/d", "/c", "ver"]).stdout == "C:\\>\nok\n"


def test_arguments_reach_the_agent_as_they_are(agent: FakeQga, guest: Guest) -> None:
    argv = [r"C:\Program Files\x.exe", "a b", 'say "hi"', "&|%", ""]

    guest.run(argv)

    assert agent.started == [argv]


def test_failing_command_raises_with_its_output(agent: FakeQga, guest: Guest) -> None:
    agent.programs = lambda _argv: Program(exitcode=5, err=b"Access is denied.\r\n")

    with pytest.raises(GuestError, match=r"(?s)'schtasks.exe /run' failed \(exit 5\).*denied"):
        guest.run(["schtasks.exe", "/run"])


def test_unchecked_command_returns_its_exit_code(agent: FakeQga, guest: Guest) -> None:
    agent.programs = lambda _argv: Program(exitcode=3010)

    assert guest.run(["setup.exe"], check=False).returncode == 3010


def test_crashed_program_fails_with_its_ntstatus(agent: FakeQga, guest: Guest) -> None:
    agent.programs = lambda _argv: Program(signal=-1073741819)

    with pytest.raises(GuestError, match=r"'watest.exe' crashed \(0xc0000005\)"):
        guest.run(["watest.exe"])


def test_missing_program_fails_to_start(agent: FakeQga, guest: Guest) -> None:
    agent.programs = lambda _argv: None

    with pytest.raises(GuestError, match="'nope.exe' did not start: .*No such file"):
        guest.run(["nope.exe"])


def test_command_that_outlasts_its_timeout_fails(agent: FakeQga, guest: Guest) -> None:
    agent.programs = lambda _argv: Program(polls=1000)

    with pytest.raises(GuestError, match="'hang.exe' did not finish within 0 s"):
        guest.run(["hang.exe"], timeout=0)


def test_output_too_long_for_a_reply_fails_saying_so(agent: FakeQga, guest: Guest) -> None:
    agent.programs = lambda _argv: Program(out=b"x" * 400 * 1024)

    with pytest.raises(GuestError, match="'ngen.exe': .*did not answer.*larger than 512 KiB"):
        guest.run(["ngen.exe"])


def test_a_dead_vm_ends_the_wait_for_a_command(agent: FakeQga, connect: Connect) -> None:
    def gone() -> None:
        raise VmError("QEMU has exited")

    agent.programs = lambda _argv: Program(polls=1000)

    with pytest.raises(VmError, match="QEMU has exited"):
        connect(gone).run(["setup.exe"])


def test_powershell_script_goes_encoded_as_utf16(agent: FakeQga, guest: Guest) -> None:
    guest.powershell("Write-Output 'ä \"x\"'")

    ((*options, encoded),) = agent.started
    script = base64.b64decode(encoded).decode("utf-16-le")
    assert (options[-1], script.splitlines()[-1]) == ("-EncodedCommand", "Write-Output 'ä \"x\"'")


def test_powershell_error_is_shown_as_text(agent: FakeQga, guest: Guest) -> None:
    agent.programs = lambda _argv: Program(
        exitcode=1,
        err=b'#< CLIXML\r\n<Objs Version="1.1.0.1" xmlns="http://schemas.microsoft.com/powershell/'
        b'2004/04"><S S="Error">boom &amp; more_x000D__x000A_</S><S S="Error">At line:3'
        b" char:1_x000D__x000A_</S></Objs>",
    )

    with pytest.raises(GuestError, match=r"(?s)throw 'boom'\n.*boom & more\nAt line:3 char:1\n$"):
        guest.powershell("throw 'boom'")


def test_copied_file_arrives_whole(agent: FakeQga, guest: Guest, tmp_path: Path) -> None:
    data = os.urandom(3 * 1024 * 1024 + 5)
    (tmp_path / "cu.exe").write_bytes(data)

    guest.put(tmp_path / "cu.exe", r"C:\setup\cu.exe")

    assert agent.files[r"C:\setup\cu.exe"] == data


def test_file_larger_than_a_reply_is_fetched_whole(
    agent: FakeQga, guest: Guest, tmp_path: Path
) -> None:
    agent.files[r"C:\setup\big.log"] = data = os.urandom(3 * 1024 * 1024 + 5)

    guest.get(r"C:\setup\big.log", tmp_path / "big.log")

    assert (tmp_path / "big.log").read_bytes() == data


def test_short_write_fails(agent: FakeQga, guest: Guest) -> None:
    agent.write_limit = 10

    with pytest.raises(GuestError, match="10 of 100 bytes written"):
        guest.write(r"C:\x.cmd", b"x" * 100)


def test_missing_file_cannot_be_read(guest: Guest) -> None:
    with pytest.raises(GuestError, match="cannot find the file"):
        guest.read(r"C:\setup\done.txt")


def test_stale_data_in_the_channel_is_skipped(agent: FakeQga, guest: Guest) -> None:
    # An earlier client's: a reply it never read, its own resync, and a
    # reply cut short.
    agent.stale = b'{"return": {}, "id": "old"}\n\xff{"return": 7}\n{"return": {"pi'
    agent.programs = lambda _argv: Program(out=b"fresh")

    assert guest.run(["cmd.exe"]).stdout == "fresh"


def test_call_that_timed_out_leaves_the_agent_usable(agent: FakeQga, guest: Guest) -> None:
    agent.unanswered = {"guest-set-time"}
    with pytest.raises(GuestError, match="did not answer guest-set-time in time"):
        guest.set_clock()
    agent.unanswered = set()

    assert guest.run(["cmd.exe"]).returncode == 0


def test_clock_is_set_to_the_hosts(agent: FakeQga, guest: Guest) -> None:
    guest.set_clock()

    assert isinstance(agent.clock, int) and abs(agent.clock - time.time_ns()) < 10**9


def test_shutdown_succeeds_without_a_reply(agent: FakeQga, guest: Guest) -> None:
    guest.shutdown()

    assert agent.powered_off


def test_shutdown_the_agent_refuses_fails(agent: FakeQga, guest: Guest) -> None:
    agent.errors["guest-shutdown"] = "failed to shutdown: Access is denied."

    with pytest.raises(GuestError, match="failed to shutdown"):
        guest.shutdown()


def test_wait_ready_returns_once_the_agent_answers(agent: FakeQga, guest: Guest) -> None:
    agent.unanswered = {"guest-sync-delimited"}
    threading.Timer(1.5, agent.unanswered.clear).start()

    guest.wait_ready(10, interval=0)

    assert not agent.unanswered


def test_wait_ready_timeout_says_the_agent_did_not_answer(agent: FakeQga, guest: Guest) -> None:
    agent.unanswered = {"guest-sync-delimited"}

    with pytest.raises(GuestError, match="no guest agent within 0 s: .*did not answer"):
        guest.wait_ready(0)


def test_wait_console_returns_once_the_console_session_is_active(
    agent: FakeQga, guest: Guest
) -> None:
    agent.programs = lambda _argv: Program(
        exitcode=1,
        out=b" USERNAME      SESSIONNAME  ID  STATE   IDLE TIME  LOGON TIME\r\n"
        b">administrator console       1  Active  none       10/23/2026 9:00 AM\r\n",
    )

    guest.wait_console(0)
