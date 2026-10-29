# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import fcntl
import os
import pty
import socket
import struct
import termios
import threading

from qemu_windows.console import CLOSED, SAC_SIZE, SizeQueries
from vm_console import relay, terminal_size


def test_relay_sends_input_up_to_ctrl_bracket() -> None:
    ours, theirs = socket.socketpair()
    stdin_read, stdin_write = os.pipe()
    stdout_read, stdout_write = os.pipe()
    os.write(stdin_write, b"ls\r\x1dexit\r")

    relay(ours, stdin_read, stdout_write, SizeQueries())

    ours.close()
    assert theirs.recv(4096) == b"ls\r"
    for fd in (stdin_read, stdin_write, stdout_read, stdout_write):
        os.close(fd)
    theirs.close()


def test_relay_shows_the_console_without_its_nuls() -> None:
    ours, theirs = socket.socketpair()
    stdin_read, stdin_write = os.pipe()
    stdout_read, stdout_write = os.pipe()
    theirs.sendall(b"PS C:\\>\x00 ")
    theirs.close()

    relay(ours, stdin_read, stdout_write, SizeQueries())

    assert os.read(stdout_read, 4096) == b"PS C:\\> "
    ours.close()
    for fd in (stdin_read, stdin_write, stdout_read, stdout_write):
        os.close(fd)


# What follows when the session's PowerShell exits: cmd's last line, then SAC
# switching back to itself (shortened).
SESSION_END = CLOSED + b'\r\n\x1b[2J\x1b[1;1H<?xml version="1.0"?>\r\n<channel-switch>'


def test_relay_ends_with_the_session_without_showing_sacs_screens() -> None:
    ours, theirs = socket.socketpair()
    stdin_read, stdin_write = os.pipe()
    stdout_read, stdout_write = os.pipe()
    theirs.sendall(b"PS C:\\> exit\r\n" + SESSION_END)
    relay(ours, stdin_read, stdout_write, SizeQueries())
    assert os.read(stdout_read, 4096) == b"PS C:\\> exit\r\n"
    ours.close()
    theirs.close()
    for fd in (stdin_read, stdin_write, stdout_read, stdout_write):
        os.close(fd)


def test_relay_ends_with_the_session_whose_last_line_comes_in_two_reads() -> None:
    ours, theirs = socket.socketpair()
    stdin_read, stdin_write = os.pipe()
    stdout_read, stdout_write = os.pipe()
    theirs.sendall(SESSION_END[:10])
    threading.Timer(0.2, theirs.sendall, (SESSION_END[10:],)).start()
    relay(ours, stdin_read, stdout_write, SizeQueries())
    assert b"channel-switch" not in os.read(stdout_read, 4096)
    ours.close()
    theirs.close()
    for fd in (stdin_read, stdin_write, stdout_read, stdout_write):
        os.close(fd)


def test_relay_answers_size_queries_instead_of_the_terminal() -> None:
    ours, theirs = socket.socketpair()
    stdin_read, stdin_write = os.pipe()
    stdout_read, stdout_write = os.pipe()
    theirs.sendall(b"PS C:\\>\x1b[18t ")
    theirs.shutdown(socket.SHUT_WR)

    relay(ours, stdin_read, stdout_write, SizeQueries(lambda: (40, 146)))

    assert (os.read(stdout_read, 4096), theirs.recv(4096)) == (b"PS C:\\> ", b"\x1b[8;40;146t")
    ours.close()
    theirs.close()
    for fd in (stdin_read, stdin_write, stdout_read, stdout_write):
        os.close(fd)


def test_relay_redraws_once_after_several_resizes() -> None:
    ours, theirs = socket.socketpair()
    stdin_read, stdin_write = os.pipe()
    stdout_read, stdout_write = os.pipe()
    resizes_read, resizes_write = os.pipe()
    os.write(resizes_write, b"\x1c\x1c\x1c")
    redraws: list[int] = []
    # Leaves once the redraw is due and done.
    threading.Timer(1.0, os.write, (stdin_write, b"\x1d")).start()

    relay(ours, stdin_read, stdout_write, SizeQueries(), resizes_read, lambda: redraws.append(1))

    assert redraws == [1]
    ours.close()
    theirs.close()
    for fd in (stdin_read, stdin_write, stdout_read, stdout_write, resizes_read, resizes_write):
        os.close(fd)


def test_terminal_size_is_the_terminals_rows_and_columns() -> None:
    controller, terminal = pty.openpty()
    fcntl.ioctl(controller, termios.TIOCSWINSZ, struct.pack("HHHH", 40, 146, 0, 0))

    assert terminal_size(terminal) == (40, 146)
    os.close(controller)
    os.close(terminal)


def test_terminal_size_without_a_terminal_is_sacs_screen() -> None:
    read, write = os.pipe()

    assert terminal_size(write) == SAC_SIZE
    os.close(read)
    os.close(write)
