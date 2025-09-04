#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import fcntl
import struct
import sys
import termios
import tty
from typing import NoReturn


# colored output, if stdout is a tty
if sys.stdout.isatty():
    TTY_RED = "\033[31m"
    TTY_GREEN = "\033[32m"
    TTY_YELLOW = "\033[33m"
    TTY_BLUE = "\033[34m"
    TTY_MAGENTA = "\033[35m"
    TTY_CYAN = "\033[36m"
    TTY_WHITE = "\033[37m"
    TTY_BG_RED = "\033[41m"
    TTY_BG_GREEN = "\033[42m"
    TTY_BG_YELLOW = "\033[43m"
    TTY_BG_BLUE = "\033[44m"
    TTY_BG_MAGENTA = "\033[45m"
    TTY_BG_CYAN = "\033[46m"
    TTY_BG_WHITE = "\033[47m"
    TTY_BOLD = "\033[1m"
    TTY_UNDERLINE = "\033[4m"
    TTY_GREY = "\033[90m"
    TTY_NORMAL = "\033[0m"


else:
    TTY_RED = ""
    TTY_GREEN = ""
    TTY_YELLOW = ""
    TTY_BLUE = ""
    TTY_MAGENTA = ""
    TTY_CYAN = ""
    TTY_WHITE = ""
    TTY_BG_RED = ""
    TTY_BG_GREEN = ""
    TTY_BG_BLUE = ""
    TTY_BG_MAGENTA = ""
    TTY_BG_CYAN = ""
    TTY_BG_WHITE = ""
    TTY_BOLD = ""
    TTY_UNDERLINE = ""
    TTY_GREY = ""
    TTY_NORMAL = ""


grep_colors = [
    TTY_BOLD + TTY_MAGENTA,
    TTY_BOLD + TTY_CYAN,
    TTY_BOLD + TTY_GREEN,
]


def get_input(what: str, default: str = "") -> str:
    sys.stdout.write(f"{what}: ")
    sys.stdout.flush()
    value = sys.stdin.readline().strip()
    if value == "":
        return default
    return value


def getch() -> str:
    # allow piping in the answers:
    if not sys.stdin.isatty():
        value = sys.stdin.readline().strip()
        if not value:
            raise RuntimeError("could not read character from stdin")
        return value
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    if ord(ch) == 3:
        raise KeyboardInterrupt()
    return ch


def input_choice(
    what: str, choices: list[str] | list[tuple[str, str]] | list[tuple[str, str, str]]
) -> str:
    next_index = 0
    ctc = {}
    texts = []
    for choice in choices:
        if isinstance(choice, tuple):
            choice = choice[0]

        added = False

        # Find an identifying character for the input choice. In case all possible
        # characters are already used start using unique numbers
        for c in str(choice):
            if c not in ".-_/" and c not in ctc:
                ctc[c] = choice
                texts.append(str(choice).replace(c, TTY_BOLD + c + TTY_NORMAL, 1))
                added = True
                break

        if not added:
            ctc[str(next_index)] = choice
            texts.append(f"{TTY_BOLD}{next_index}{TTY_NORMAL}:{choice}")
            next_index += 1

    while True:
        sys.stdout.write(f"{what} ({', '.join(texts)}): ")
        sys.stdout.flush()
        c = getch()
        if c in ctc:
            sys.stdout.write(f" {TTY_BOLD}{ctc[c]}{TTY_NORMAL}\n")
            return ctc[c]

        sys.stdout.write("\n")


def get_tty_size() -> tuple[int, int]:
    try:
        ws = bytearray(8)
        fcntl.ioctl(sys.stdout.fileno(), termios.TIOCGWINSZ, ws)
        lines, columns, _x, _y = struct.unpack("HHHH", ws)
        if lines > 0 and columns > 0:
            return lines, columns
    except OSError:
        pass
    return (24, 99999)


def bail_out(text: str, exit_code: int = 1) -> NoReturn:
    sys.stderr.write(text + "\n")
    sys.exit(exit_code)
