#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import sys
from pathlib import Path
from typing import IO

from cmk.ccc.log import CMKFormatter, log_to_watched_file

__all__ = [
    "logger",
    "setup_console_logging",
    "setup_logging_handler",
    "setup_watched_file_logging_handler",
]

logger = logging.getLogger("cmk")


def setup_console_logging() -> None:
    """This method enables all log messages to be written to the console
    without any additional information like date/time, logger-name. Just
    the log line is written.

    This can be used for existing command line applications which were
    using sys.stdout.write() or print() before.
    """
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(CMKFormatter(message_only=True))
    _set_handler(handler)


def setup_watched_file_logging_handler(logfile: str | Path) -> None:
    log_to_watched_file(logger, Path(logfile))


def setup_logging_handler(stream: IO[str]) -> None:
    """This method enables all log messages to be written to the given
    stream file object. The messages are formatted in Check_MK standard
    logging format.
    """
    handler = logging.StreamHandler(stream=stream)
    handler.setFormatter(CMKFormatter())
    _set_handler(handler)


def _set_handler(handler: logging.Handler) -> None:
    del logger.handlers[:]  # Remove all previously existing handlers
    logger.addHandler(handler)
