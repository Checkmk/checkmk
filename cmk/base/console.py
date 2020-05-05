#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Utiliy module for holding generic methods that implement handling
of console input / output"""

import logging
import sys
from contextlib import contextmanager, suppress
from typing import Any, Generator, IO, Optional  # pylint: disable=unused-import

from cmk.utils.log import VERBOSE
import cmk.utils.tty as tty

#
# Generic / low level functions
#


# TODO: This should be obsoleted:
#   - either pick a log level
#   - or write to sys.stdout|err
def output(text, *args, stream=None):
    # type: (str, *Any, Optional[IO[str]]) -> None
    if args:
        text = text % args
    if stream is None:
        stream = sys.stdout
    with suppress(IOError):
        # Suppress broken pipe due to, e.g., | head.
        stream.write(text)
        stream.flush()


@contextmanager
def set_stream(logger, handler, stream):
    # type: (logging.Logger, logging.StreamHandler, IO[str]) -> Generator[None, None, None]
    # See `https://bugs.python.org/issue6333` for why this is necessary.
    old = handler.setStream(stream)
    logger.addHandler(handler)
    try:
        yield
    finally:
        logger.removeHandler(handler)
        handler.close()
        if old:
            handler.setStream(old)


_handler = logging.StreamHandler()
_handler.terminator = ""  # TODO: let the handler add '\n'
_console = logging.getLogger("cmk.base.console")
_console.propagate = False

isEnabledFor = _console.isEnabledFor


def log(level, text, *args, stream=None):
    # type: (int, str, *Any, Optional[IO[str]]) -> None
    if stream is None:
        stream = sys.stdout

    with set_stream(_console, _handler, stream):
        _console.log(level, text, *args)


def verbose(text, *args, stream=None):
    # type: (str, *Any, Optional[IO[str]]) -> None
    """Output text if opt_verbose is set (-v).

    Adds no linefeed.

    """
    log(VERBOSE, text, *args, stream=stream)


def vverbose(text, *args, stream=None):
    # type: (str, *Any, Optional[IO[str]]) -> None
    """Output text if, opt_verbose >= 2 (-vv)."""
    log(logging.DEBUG, text, *args, stream=stream)


#
# More top level wrappers
#


def warning(text, *args, stream=None):
    # type: (str, *Any, Optional[IO[str]]) -> None
    if stream is None:
        stream = sys.stderr
    log(logging.WARNING, _format_warning(text), *args, stream=stream)


# TODO: Inconsistent -> Adds newline and other functions don't
def _format_warning(text):
    # type (str) -> str
    stripped = text.lstrip()
    indent = text[:len(text) - len(stripped)]
    return "%s%s%sWARNING:%s %s\n" % (indent, tty.bold, tty.yellow, tty.normal, stripped)


def error(text, *args):
    # type: (str, *Any) -> None
    log(logging.ERROR, text, *args, stream=sys.stderr)


def section_begin(text):
    # type: (str) -> None
    verbose("%s%s%s:\n", tty.bold, text, tty.normal)


def section_success(text):
    # type: (str) -> None
    verbose("%sSUCCESS%s - %s\n", tty.green, tty.normal, text)


def section_error(text):
    # type: (str) -> None
    verbose("%sERROR%s - %s\n", tty.red, tty.normal, text)


def step(text):
    # type: (str) -> None
    verbose("%s+%s %s\n", tty.yellow, tty.normal, text.upper())
