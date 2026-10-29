# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""PowerShell on a test VM's serial console, in this terminal (README.md,
"Exploring the test VM").

shell() switches to the PowerShell session the saved VM brings along
(qemu_windows.console) and relays the terminal until that PowerShell
exits, or until Ctrl-] for one that hangs. The session's console host
lays out its screen for the terminal's size, which it asks for when the
session is switched to, so a resized terminal switches to it again.
"""

import os
import select
import signal
import socket
import sys
import termios
import time
import tty
from collections.abc import Callable
from pathlib import Path

from qemu_windows.console import attach, CLOSED, ConsoleError, Keys, SAC_SIZE, SizeQueries

ESCAPE = b"\x1d"  # Ctrl-]
# Clears the terminal and puts the cursor home: the console host's screen
# is drawn from there.
CLEAR = b"\x1b[2J\x1b[H"
# A window being dragged is resized many times: the screen is redrawn
# once it has kept its size this long.
_RESIZE_SETTLE = 0.3


def terminal_size(fd: int) -> tuple[int, int]:
    """The rows and columns of the terminal fd, or SAC's screen if it is
    none."""
    try:
        columns, rows = os.get_terminal_size(fd)
    except OSError:
        return SAC_SIZE
    return rows, columns


def relay(
    sock: socket.socket,
    stdin: int,
    stdout: int,
    queries: SizeQueries,
    resizes: int | None = None,
    redraw: Callable[[], None] = lambda: None,
) -> None:
    """Copies the console to stdout and stdin to the console until the
    session exits (CLOSED, not shown, nor SAC's screens after it), ESCAPE on
    stdin, or the end of stdin or of the console. The console's size
    queries are answered here, not by the terminal, and its cursor keys go
    as the control keys the session binds (Keys). Whenever resizes (a file
    descriptor) becomes readable, it is drained and redraw() follows once
    it has stayed quiet for _RESIZE_SETTLE s."""
    keys = Keys()
    # The end of what was shown, in case CLOSED arrives in two reads.
    tail = b""
    watched = [sock.fileno(), stdin, *([] if resizes is None else [resizes])]
    due: float | None = None
    while True:
        wait = None if due is None else max(due - time.monotonic(), 0)
        ready = select.select(watched, [], [], wait)[0]
        if resizes is not None and resizes in ready:
            os.read(resizes, 1024)
            due = time.monotonic() + _RESIZE_SETTLE
        if due is not None and time.monotonic() >= due:
            due = None
            redraw()
            continue
        if sock.fileno() in ready:
            if not (data := sock.recv(65536)):
                return
            shown, answers = queries.feed(data.replace(b"\0", b""))
            if answers:
                sock.sendall(answers)
            seen = tail + shown
            if (closed := seen.find(CLOSED)) >= 0:
                _write_all(stdout, shown[: max(closed - len(tail), 0)])
                return
            _write_all(stdout, shown)
            tail = seen[-(len(CLOSED) - 1) :]
        if stdin in ready:
            data = os.read(stdin, 1024)
            before, escape, _ = data.partition(ESCAPE)
            if before := keys.feed(before):
                sock.sendall(before)
            if escape or not data:
                return


def _write_all(fd: int, data: bytes) -> None:
    """All of data: a write that a signal (a resize) cuts short writes only
    part of it."""
    view = memoryview(data)
    while view:
        view = view[os.write(fd, view) :]


def shell(path: Path) -> None:
    """Relays this terminal to PowerShell on the console socket path until
    it exits, or until Ctrl-]."""
    sock = socket.socket(socket.AF_UNIX)
    try:
        sock.connect(str(path))
    except OSError as e:
        raise ConsoleError(f"the serial console {path}: {e}") from None
    with sock:
        sys.stderr.write("PowerShell on the serial console: exit ends it (Ctrl-] if it hangs)\n")
        stdin, stdout = sys.stdin.fileno(), sys.stdout.fileno()
        # The console host lays out its screen for this terminal.
        queries = SizeQueries(lambda: terminal_size(stdout))
        screen = attach(sock, queries)
        mode = termios.tcgetattr(stdin) if os.isatty(stdin) else None
        resizes, notify = os.pipe2(os.O_NONBLOCK | os.O_CLOEXEC)
        # The handler only has to exist: the wakeup fd carries the signal.
        old_handler = signal.signal(signal.SIGWINCH, lambda _signum, _frame: None)
        signal.set_wakeup_fd(notify, warn_on_full_buffer=False)

        def redraw() -> None:
            # Switching to the session again makes its console host ask
            # for the new size and draw its screen anew.
            _write_all(stdout, CLEAR + attach(sock, queries))

        try:
            if mode is not None:
                tty.setraw(stdin)
            _write_all(stdout, CLEAR + screen)
            relay(sock, stdin, stdout, queries, resizes, redraw)
        finally:
            signal.set_wakeup_fd(-1)
            signal.signal(signal.SIGWINCH, old_handler)
            os.close(resizes)
            os.close(notify)
            if mode is not None:
                termios.tcsetattr(stdin, termios.TCSADRAIN, mode)
            _write_all(stdout, b"\r\n")
