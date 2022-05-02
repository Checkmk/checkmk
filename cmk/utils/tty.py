#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module contains constants and functions for neat output formating
on ttys while being compatible when the command is not attached to a TTY"""

import errno
import fcntl
import io
import itertools
import struct
import sys
import termios
from typing import Dict, Iterable, List, Tuple

# TODO: Implementing the colors below as simple global variables is a bad idea,
# because their actual values depend on sys.stdout at *import* time! sys.stdout
# can be something different when the colors are used, and a scenario where
# this actually goes wrong is during a pytest run: At the time when the
# conftest.py modules are imported, sys.stdout has not been changed yet, so it
# might be a TTY. Later during test execution, sys.stdout has been changed to
# an internal stream, which is not a TTY, see the capsys fixture.
#
# In a nutshell: The colors below should probably be functions, not simple
# variables, but this involves fixing all call sites.

black = ""
red = ""
green = ""
yellow = ""
blue = ""
magenta = ""
cyan = ""
white = ""
bgblue = ""
bgmagenta = ""
bgwhite = ""
bgyellow = ""
bgred = ""
bgcyan = ""
bold = ""
underline = ""
normal = ""
ok = ""
warn = ""
error = ""
states: Dict[int, str] = {}


def reinit():
    global black, red, green, yellow, blue, magenta, cyan, white
    global bgblue, bgmagenta, bgwhite, bgyellow, bgred, bgcyan
    global bold, underline, normal, ok, warn, error, states
    if sys.stdout.isatty():
        black = "\033[30m"
        red = "\033[31m"
        green = "\033[32m"
        yellow = "\033[33m"
        blue = "\033[34m"
        magenta = "\033[35m"
        cyan = "\033[36m"
        white = "\033[37m"
        bgblue = "\033[44m"
        bgmagenta = "\033[45m"
        bgwhite = "\033[47m"
        bgyellow = "\033[43m"
        bgred = "\033[41m"
        bgcyan = "\033[46m"
        bold = "\033[1m"
        underline = "\033[4m"
        normal = "\033[0m"
    else:
        black = ""
        red = ""
        green = ""
        yellow = ""
        blue = ""
        magenta = ""
        cyan = ""
        white = ""
        bgblue = ""
        bgmagenta = ""
        bgwhite = ""
        bgyellow = ""
        bgred = ""
        bgcyan = ""
        bold = ""
        underline = ""
        normal = ""
    ok = green + bold + "OK" + normal
    warn = yellow + bold + "WARNING" + normal
    error = red + bold + "ERROR" + normal
    states = {0: green, 1: yellow, 2: red, 3: magenta}


reinit()

TableRow = List[str]
TableColors = TableRow


def colorset(fg: int = -1, bg: int = -1, attr: int = -1) -> str:
    if not sys.stdout.isatty():
        return ""
    if attr >= 0:
        return "\033[3%d;4%d;%dm" % (fg, bg, attr)
    if bg >= 0:
        return "\033[3%d;4%dm" % (fg, bg)
    if fg >= 0:
        return "\033[3%dm" % fg
    return normal


def get_size() -> Tuple[int, int]:
    try:
        ws = struct.pack("HHHH", 0, 0, 0, 0)
        # TODO: Use the following instead?
        # array.array(b'h' if six.PY2 else u'h', [0, 0, 0, 0])
        ws = fcntl.ioctl(sys.stdout.fileno(), termios.TIOCGWINSZ, ws)
        lines, columns = struct.unpack("HHHH", ws)[:2]
        if lines > 0 and columns > 0:
            return lines, columns
    except io.UnsupportedOperation:
        pass  # When sys.stdout is StringIO() or similar, then .fileno() is not available
    except IOError as e:
        if e.errno == errno.ENOTTY:
            # Inappropriate ioctl for device: Occurs when redirecting output
            pass
        elif e.errno == errno.EINVAL:
            # Invalid argument: Occurs e.g. when executing from cron
            pass
        else:
            raise

    return (24, 80)


def print_table(
    headers: TableRow, colors: TableColors, rows: Iterable[TableRow], indent: str = ""
) -> None:
    num_columns = len(headers)
    lengths = _column_lengths(headers, rows, num_columns)
    dashes = ["-" * l for l in lengths]
    fmt = _row_template(lengths, colors, indent)
    for row in itertools.chain([headers, dashes], rows):
        sys.stdout.write(fmt % tuple(row[:num_columns]))


def _column_lengths(headers: TableRow, rows: Iterable[TableRow], num_columns: int) -> List[int]:
    lengths = [len(h) for h in headers]
    for row in rows:
        for index, column in enumerate(row[:num_columns]):
            lengths[index] = max(len(column), lengths[index])
    return lengths


def _row_template(lengths: List[int], colors: TableColors, indent: str) -> str:
    fmt = indent
    sep = ""
    for l, c in zip(lengths, colors):
        fmt += c + sep + "%-" + str(l) + "s" + normal
        sep = " "
    fmt += "\n"
    return fmt
