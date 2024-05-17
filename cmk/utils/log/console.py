#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from typing import TextIO

from ._level import VERBOSE as VERBOSE

# NOTE: We abuse the log level of this logger as a global variable!
_console = logging.getLogger("cmk.base.console")


def error(text: str, *, file: TextIO | None = None) -> None:
    if _console.isEnabledFor(logging.ERROR):
        print(text, file=file, flush=True)


def warning(text: str, *, file: TextIO | None = None) -> None:
    if _console.isEnabledFor(logging.WARNING):
        print(text, file=file, flush=True)


def info(text: str, *, file: TextIO | None = None) -> None:
    if _console.isEnabledFor(logging.INFO):
        print(text, file=file, flush=True)


def verbose(text: str, *, file: TextIO | None = None) -> None:
    if _console.isEnabledFor(VERBOSE):
        print(text, end="", file=file, flush=True)


def debug(text: str, *, file: TextIO | None = None) -> None:
    if _console.isEnabledFor(logging.DEBUG):
        print(text, end="", file=file, flush=True)
