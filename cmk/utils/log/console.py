#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import logging
import sys
from collections.abc import Generator
from contextlib import contextmanager
from typing import TextIO

import cmk.utils.tty as tty

from ._level import VERBOSE as VERBOSE


# For StreamHandler.setStream()
@contextmanager
def set_stream(
    logger: logging.Logger, handler: logging.StreamHandler[TextIO], stream: TextIO
) -> Generator[None, None, None]:
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


def log(level: int, text: str, *args: object, **kwargs: TextIO) -> None:
    stream = kwargs.pop("stream", sys.stdout)
    assert not kwargs

    with set_stream(_console, _handler, stream):
        _console.log(level, text, *args)


def debug(text: str, *args: object, **kwargs: TextIO) -> None:
    """Output text if, opt_verbose >= 2 (-vv)."""
    log(logging.DEBUG, text, *args, **kwargs)


vverbose = debug


def verbose(text: str, *args: object, **kwargs: TextIO) -> None:
    """Output text if opt_verbose is set (-v).

    Adds no linefeed.

    """
    log(VERBOSE, text, *args, **kwargs)


def info(text: str, *args: object, **kwargs: TextIO) -> None:
    """Output text if opt_verbose is set (-v).

    Adds no linefeed.

    """
    log(logging.INFO, text, *args, **kwargs)


#
# More top level wrappers
#


def warning(text: str, *args: object, **kwargs: TextIO) -> None:
    stream = kwargs.pop("stream", sys.stderr)
    assert not kwargs
    log(logging.WARNING, _format_warning(text), *args, stream=stream)


# TODO: Inconsistent -> Adds newline and other functions don't
def _format_warning(text: str) -> str:
    # type (str) -> str
    stripped = text.lstrip()
    indent = text[: len(text) - len(stripped)]
    return f"{indent}{tty.bold}{tty.yellow}WARNING:{tty.normal} {stripped}\n"


def error(text: str, *args: object) -> None:
    log(logging.ERROR, text, *args, stream=sys.stderr)
