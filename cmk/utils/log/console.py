#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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


def format_warning(text: str) -> str:
    stripped = text.lstrip()
    indent = text[: len(text) - len(stripped)]
    return f"{indent}{tty.bold}{tty.yellow}WARNING:{tty.normal} {stripped}"


def _log(level: int, text: str, *args: object, stream: TextIO | None = None) -> None:
    with set_stream(_console, _handler, sys.stdout if stream is None else stream):
        _console.log(level, text, *args)


def debug(text: str) -> None:
    _log(logging.DEBUG, text)


def verbose(text: str, stream: TextIO | None = None) -> None:
    _log(VERBOSE, text, stream=stream)


def info(text: str) -> None:
    _log(logging.INFO, text)


def warning(text: str, stream: TextIO | None = None) -> None:
    _log(logging.WARNING, text, stream=stream)


def error(text: str) -> None:
    _log(logging.ERROR, text, stream=sys.stderr)
