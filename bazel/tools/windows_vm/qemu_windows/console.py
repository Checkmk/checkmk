# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Windows' Special Administration Console (SAC) on a test VM's serial
console (machine.py's console socket): logging into a PowerShell there.

SAC is reached in a few seconds, and unlike the guest agent it is fast
enough for large output. login() opens a new cmd channel in SAC, logs in
as the image's Administrator and runs PowerShell in C:\\ there; its exit
ends the session and closes the channel (CLOSED). save_state.py logs in
once before it saves the VM, in the first channel (SESSION), so that
every resumed VM has that session: attach() switches to it. The console
serves one client at a time.
"""

import re
import select
import socket
import time
from collections.abc import Callable

from qemu_windows.errors import VmError
from qemu_windows.guest import PASSWORD, USER

# The channel save_state.py logs into: the first one SAC opens after a boot.
SESSION = b"Cmd0001"
# What cmd prints when the session's PowerShell has exited and cmd with it,
# right before SAC closes the channel and switches back to itself.
CLOSED = b"The Command Console session is exiting."

# What SAC and cmd print. SAC sends NULs between some of it, which are
# dropped before matching.
_ANY_KEY = re.compile(rb"Use any other key to view this channel")
# The end of SAC's screen: its last row, then the cursor at the prompt.
_SAC_SCREEN = re.compile(rb"\x1b\[24;1H[\s\S]*?\x1b\[\d+;\d+H")
_CHANNEL = re.compile(rb"Channel: (Cmd\d{4})")
_SWITCHED = re.compile(
    # The whole line: its end must not show as the start of the screen.
    rb"(?P<switched>Use any other key to view this channel\.\r\n)"
    rb"|(?P<missing>Could not find a channel with that name)"
)
_USERNAME = re.compile(rb"Username:")
_DOMAIN = re.compile(rb"Domain *:")
_PASSWORD = re.compile(rb"Password:")
# Escape sequences the console host puts between characters (also window
# titles), and how it moves on to the next line.
_ESCAPES = rb"(?:\x1b\[[0-9;?]*[A-Za-z]|\x1b\][^\x07]*\x07)*"
_NEXT_LINE = rb"(?:\r\n|\x1b\[\d+;1H)"
# At the start of a line.
_CMD_PROMPT = re.compile(rb"(?:\n|\x1b\[\d+;1H)" + _ESCAPES + rb"[A-Z]:\\[^>\x1b\r\n]*>")
_PS_PROMPT = re.compile(rb"PS [A-Z]:\\[^>\x1b\r\n]*>")
_ANY_PROMPT = re.compile(rb"(?:PS )?[A-Z]:\\[^>\x1b\r\n]*>")
# The end of a console host's screen: the cursor placed and shown.
_SCREEN = re.compile(rb"\x1b\[\d+;\d+H\x1b\[\?25h")
# SAC takes ESC for its own commands (ESC Tab switches channels) and drops
# it otherwise, so a terminal's cursor keys reach a session without their
# ESC. Keys.feed() turns them into control keys, which the session's
# PowerShell binds to what the keys do (Windows' PSReadLine mode, whose
# Tab cycles through completions, has none of these control keys bound).
KEY_BINDINGS = (
    ((b"\x1b[A", b"\x1bOA"), "Ctrl+p", "PreviousHistory"),
    ((b"\x1b[B", b"\x1bOB"), "Ctrl+n", "NextHistory"),
    ((b"\x1b[C", b"\x1bOC"), "Ctrl+f", "ForwardChar"),
    ((b"\x1b[D", b"\x1bOD"), "Ctrl+b", "BackwardChar"),
    ((b"\x1b[H", b"\x1bOH", b"\x1b[1~"), "Ctrl+a", "BeginningOfLine"),
    ((b"\x1b[F", b"\x1bOF", b"\x1b[4~"), "Ctrl+e", "EndOfLine"),
    ((b"\x1b[3~",), "Ctrl+d", "DeleteChar"),
)
_KEYS = {
    sequence: bytes([ord(chord[-1]) - ord("a") + 1])
    for sequences, chord, _function in KEY_BINDINGS
    for sequence in sequences
}
_BIND_KEYS = "; ".join(
    f"Set-PSReadLineKeyHandler -Chord {chord} -Function {function}"
    for _sequences, chord, function in KEY_BINDINGS
)
# The channel's PowerShell, in C:\ on a cleared screen with the keys bound.
# cmd exits with it, which closes the channel: exit ends the session.
_SESSION_COMMAND = (
    f'cd /d C:\\ & cls & powershell -NoLogo -NoExit -Command "{_BIND_KEYS}" & exit'.encode()
)


class ConsoleError(VmError):
    pass


# Rows and columns: SAC's screen, the size of a console without a terminal.
SAC_SIZE = (24, 80)


class SizeQueries:
    """Answers for the console: its console host asks the terminal for its
    size (xterm's "report the text area size") and lays out its screen for
    the answer. Unanswered, it waits 3 s per query and then redraws its
    screen, losing what was typed meanwhile. A terminal that answers itself
    would type its answer into the session.

    size: the rows and columns to report, asked at each query (default:
    SAC_SIZE).
    """

    QUERY = b"\x1b[18t"

    def __init__(self, size: Callable[[], tuple[int, int]] = lambda: SAC_SIZE) -> None:
        self._size = size
        # The start of a query that the last read ended in.
        self._held = b""

    def feed(self, data: bytes) -> tuple[bytes, bytes]:
        """The console's next output: what to show of it, without its size
        queries, and the answers to send back."""
        data = self._held + data
        answers = b"\x1b[8;%d;%dt" % self._size() * data.count(self.QUERY)
        data = data.replace(self.QUERY, b"")
        self._held = b""
        for n in range(len(self.QUERY) - 1, 0, -1):
            if data.endswith(self.QUERY[:n]):
                data, self._held = data[:-n], data[-n:]
                break
        return data, answers


class Keys:
    """The terminal's input for the session: cursor keys as the control
    keys KEY_BINDINGS binds."""

    _LONGEST = max(len(sequence) for sequence in _KEYS)

    def __init__(self) -> None:
        # The start of a key that the last read ended in.
        self._held = b""

    def feed(self, data: bytes) -> bytes:
        data, self._held = self._held + data, b""
        for sequence, control in _KEYS.items():
            data = data.replace(sequence, control)
        for n in range(min(self._LONGEST - 1, len(data)), 0, -1):
            tail = data[-n:]
            if tail.startswith(b"\x1b") and any(s.startswith(tail) for s in _KEYS):
                data, self._held = data[:-n], tail
                break
        return data


class _Console:
    """The console's output, consumed up to what each step waits for."""

    def __init__(self, sock: socket.socket, queries: SizeQueries) -> None:
        self._sock = sock
        self._unread = b""
        self._queries = queries

    def send(self, data: bytes) -> None:
        self._sock.sendall(data)

    def expect(self, pattern: re.Pattern[bytes], timeout: float, what: str) -> re.Match[bytes]:
        deadline = time.monotonic() + timeout
        while not (match := pattern.search(self._unread)):
            if (left := deadline - time.monotonic()) <= 0:
                raise ConsoleError(f"{what}: no answer within {timeout:g} s")
            self._read(left)
        self._unread = self._unread[match.end() :]
        return match

    def take(self) -> bytes:
        unread, self._unread = self._unread, b""
        return unread

    def _read(self, timeout: float) -> bool:
        if not select.select([self._sock], [], [], timeout)[0]:
            return False
        if not (data := self._sock.recv(65536)):
            raise ConsoleError("the console closed: the VM is gone")
        shown, answers = self._queries.feed(data.replace(b"\0", b""))
        if answers:
            self._sock.sendall(answers)
        self._unread += shown
        return True


def login(
    sock: socket.socket,
    user: str = USER,
    password: str = PASSWORD,
    *,
    timeout: float = 60.0,
    retry: float = 5.0,
) -> bytes:
    """Opens a cmd channel in SAC, logs in and starts PowerShell in C:\\
    there (_SESSION_COMMAND), laid out for SAC's screen. Returns the
    channel's name."""
    console = _Console(sock, SizeQueries())
    _to_sac(console, timeout)
    channel = _open_cmd_channel(console, timeout, retry)
    console.send(b"ch -sn " + channel + b"\r")
    console.expect(_ANY_KEY, timeout, f"switching to {channel.decode()}")
    console.send(b"\r")
    console.expect(_USERNAME, timeout, "the login")
    console.send(user.encode() + b"\r")
    console.expect(_DOMAIN, timeout, "the login")
    console.send(b"\r")
    console.expect(_PASSWORD, timeout, "the login")
    console.send(password.encode() + b"\r")
    console.expect(_CMD_PROMPT, timeout, "the command prompt after the login (wrong password?)")
    _sync(console, timeout)
    console.send(_SESSION_COMMAND + b"\r")
    console.expect(_PS_PROMPT, timeout, "PowerShell")
    return channel


def attach(
    sock: socket.socket,
    queries: SizeQueries,
    channel: bytes = SESSION,
    *,
    timeout: float = 10.0,
    redraw: float = 1.0,
    tries: int = 3,
) -> bytes:
    """Switches to channel, a session logged in before, laid out for the
    size queries answers. Returns the screen to show before relaying.
    Nothing reaches the session that could run what was typed there."""
    console = _Console(sock, queries)
    for _ in range(tries):
        _to_sac(console, timeout)
        console.send(b"ch -sn " + channel + b"\r")
        if console.expect(_SWITCHED, timeout, f"switching to {channel.decode()}")["missing"]:
            raise ConsoleError(
                f"SAC has no channel {channel.decode()}, the saved PowerShell session"
            )
        # The rest of SAC's switch screen.
        console.take()
        # Any key shows the channel. SAC keeps it.
        console.send(b"\r")
        try:
            # The console host redraws its screen for the terminal, asking
            # for its size, after some switches only.
            match = console.expect(_SCREEN, redraw, f"the screen of {channel.decode()}")
            return match.string[: match.end()] + console.take()
        except ConsoleError:
            pass
    # PSReadLine's ClearScreen: the prompt and the line typed so far, on a
    # cleared screen, laid out for the size the console host knows.
    console.take()
    console.send(b"\x0c")
    match = console.expect(_ANY_PROMPT, timeout, f"a prompt in {channel.decode()}")
    return match.string[: match.end()] + console.take()


def _to_sac(console: _Console, timeout: float) -> None:
    """Back to SAC from whatever channel the last client left it in."""
    console.send(b"\x1b\t0")
    console.expect(_ANY_KEY, timeout, "SAC")
    console.send(b"\r")
    console.expect(_SAC_SCREEN, timeout, "SAC")
    # SAC's screen shows its history, with the channels of earlier logins.
    console.take()


def _open_cmd_channel(console: _Console, timeout: float, retry: float) -> bytes:
    """The name of a new cmd channel. Right after a resume SAC's cmd is not
    available yet, and SAC drops the command: it is sent again."""
    deadline = time.monotonic() + timeout
    while True:
        console.send(b"cmd\r")
        try:
            return console.expect(_CHANNEL, min(retry, timeout), "SAC's cmd").group(1)
        except ConsoleError:
            if time.monotonic() >= deadline:
                raise ConsoleError(
                    f"SAC's cmd channel is not available after {timeout:g} s: the guest may"
                    " still be starting its sacsvr service, try again in a minute"
                ) from None


def _sync(console: _Console, timeout: float, retry: float = 0.5) -> None:
    """Until cmd has taken a whole line. The answer to the last size query
    can redraw the screen after the prompt, dropping what was typed
    meanwhile: a comment line is sent until its echo arrives whole."""
    deadline = time.monotonic() + timeout
    attempt = 0
    while True:
        attempt += 1
        line = b"rem sync %d" % attempt
        console.send(line + b"\r")
        echo = re.compile(
            _ESCAPES.join(re.escape(bytes([c])) for c in line) + _ESCAPES + _NEXT_LINE
        )
        try:
            console.expect(echo, min(retry, timeout), "cmd's echo")
            return
        except ConsoleError:
            if time.monotonic() >= deadline:
                raise ConsoleError(f"cmd took no input within {timeout:g} s") from None
