#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import sys
from logging.handlers import WatchedFileHandler
from os import PathLike
from typing import IO

from ._level import VERBOSE

__all__ = [
    "clear_console_logging",
    "get_formatter",
    "logger",
    "setup_console_logging",
    "setup_logging_handler",
    "setup_watched_file_logging_handler",
    "verbosity_to_log_level",
]

logger = logging.getLogger("cmk")


def get_formatter() -> logging.Formatter:
    """Returns a new message formater instance that uses the standard
    Check_MK log format by default."""
    return logging.Formatter("%(asctime)s [%(levelno)s] [%(name)s %(process)d] %(message)s")


def clear_console_logging() -> None:
    logger.handlers[:] = []
    logger.addHandler(logging.NullHandler())
    logger.setLevel(logging.INFO)


# Set default logging handler to avoid "No handler found" warnings.
# Python 2.7+
clear_console_logging()


def setup_console_logging() -> None:
    """This method enables all log messages to be written to the console
    without any additional information like date/time, logger-name. Just
    the log line is written.

    This can be used for existing command line applications which were
    using sys.stdout.write() or print() before.
    """
    setup_logging_handler(sys.stdout, logging.Formatter("%(message)s"))


def setup_watched_file_logging_handler(
    logfile: str | PathLike[str], formatter: logging.Formatter | None = None
) -> None:
    """Removes all previous logger handlers and set a logfile handler for the given logfile path
    This handler automatically reopens the logfile if it detects an inode change, e.g through logrotate
    """
    _set_handler(WatchedFileHandler(logfile), formatter)


def setup_logging_handler(stream: IO[str], formatter: logging.Formatter | None = None) -> None:
    """This method enables all log messages to be written to the given
    stream file object. The messages are formatted in Check_MK standard
    logging format.
    """
    _set_handler(logging.StreamHandler(stream=stream), formatter)


def _set_handler(handler: logging.Handler, formatter: logging.Formatter | None = None) -> None:
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelno)s] [%(name)s] %(message)s")
        if formatter is None
        else formatter
    )
    del logger.handlers[:]  # Remove all previously existing handlers
    logger.addHandler(handler)


def verbosity_to_log_level(verbosity: int) -> int:
    """Values for "verbosity":

    0: enables INFO and above
    1: enables VERBOSE and above
    2: enables DEBUG and above (ALL messages)
    """
    if verbosity == 0:
        return logging.INFO
    if verbosity == 1:
        return VERBOSE
    if verbosity >= 2:
        return logging.DEBUG
    raise NotImplementedError()
