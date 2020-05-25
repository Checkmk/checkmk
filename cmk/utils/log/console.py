#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import sys
from contextlib import contextmanager
from typing import Any, Generator, IO, Optional

import cmk.utils.tty as tty
from ._level import VERBOSE

if sys.version_info > (3, 7):
    # For StreamHandler.setStream()
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
else:

    @contextmanager
    def set_stream(logger, handler, stream):
        handler.close()
        old, handler.stream = handler.stream, stream
        logger.addHandler(handler)
        try:
            yield
        finally:
            logger.removeHandler(handler)
            handler.close()
            if old:
                handler.stream = old


_handler = logging.StreamHandler()
_handler.terminator = ""  # TODO: let the handler add '\n'
_console = logging.getLogger("cmk.base.console")
_console.propagate = False

isEnabledFor = _console.isEnabledFor


def log(level, text, *args, **kwargs):
    # type: (int, str, *Any, **Any) -> None
    stream = kwargs.pop("stream", sys.stdout)  # type: IO[str]
    assert not kwargs

    with set_stream(_console, _handler, stream):
        _console.log(level, text, *args)


def debug(text, *args, **kwargs):
    # type: (str, *Any, Optional[IO[str]]) -> None
    """Output text if, opt_verbose >= 2 (-vv)."""
    log(logging.DEBUG, text, *args, **kwargs)


vverbose = debug


def verbose(text, *args, **kwargs):
    # type: (str, *Any, Optional[IO[str]]) -> None
    """Output text if opt_verbose is set (-v).

    Adds no linefeed.

    """
    log(VERBOSE, text, *args, **kwargs)


def info(text, *args, **kwargs):
    # type: (str, *Any, Optional[IO[str]]) -> None
    """Output text if opt_verbose is set (-v).

    Adds no linefeed.

    """
    log(logging.INFO, text, *args, **kwargs)


#
# More top level wrappers
#


def warning(text, *args, **kwargs):
    # type: (str, *Any, **Any) -> None
    stream = kwargs.pop("stream", sys.stderr)  # type: IO[str]
    assert not kwargs
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
