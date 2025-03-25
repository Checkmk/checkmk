#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import sys
from typing import TextIO

from ._level import VERBOSE as VERBOSE

# NOTE: We abuse the log level of this logger as a global variable!
_console = logging.getLogger("cmk.base.console")


def error(text: str, *, file: TextIO | None = None) -> None:
    if file is None:
        file = sys.stdout
    if _console.isEnabledFor(logging.ERROR):
        file.write(text + "\n")
        file.flush()


def warning(text: str, *, file: TextIO | None = None) -> None:
    if file is None:
        file = sys.stdout
    if _console.isEnabledFor(logging.WARNING):
        file.write(text + "\n")
        file.flush()


def info(text: str, *, file: TextIO | None = None) -> None:
    if file is None:
        file = sys.stdout
    if _console.isEnabledFor(logging.INFO):
        file.write(text + "\n")
        file.flush()


# TODO: Figure out where this is used for a "real" console vs. some internal protocol.
# The latter should really be disentangled from this file here.
def verbose_no_lf(text: str, *, file: TextIO | None = None) -> None:
    if file is None:
        file = sys.stdout
    if _console.isEnabledFor(VERBOSE):
        file.write(text)
        file.flush()


def verbose(text: str, *, file: TextIO | None = None) -> None:
    if file is None:
        file = sys.stdout
    if _console.isEnabledFor(VERBOSE):
        file.write(text + "\n")
        file.flush()


def debug(text: str, *, file: TextIO | None = None) -> None:
    if file is None:
        file = sys.stdout
    if _console.isEnabledFor(logging.DEBUG):
        file.write(text + "\n")
        file.flush()
