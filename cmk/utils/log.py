#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
import logging
from typing import AnyStr, Text, Union, IO  # pylint: disable=unused-import

# Explicitly check for Python 3 (which is understood by mypy)
if sys.version_info[0] >= 3:
    from pathlib import Path  # pylint: disable=import-error
else:
    from pathlib2 import Path

if sys.version_info[0] >= 3:
    IOLog = IO[Text]
else:
    IOLog = IO[AnyStr]

# Just for reference, the predefined logging levels:
#
# syslog/CMC    Python         added to Python
# --------------------------------------------
# emerg  0
# alert  1
# crit   2      CRITICAL 50
# err    3      ERROR    40
# warn   4      WARNING  30                 <= default level in Python
# notice 5                                  <= default level in CMC
# info   6      INFO     20
#                              VERBOSE  15
# debug  7      DEBUG    10
#
# NOTE: VERBOSE is a bit confusing and suffers from the not-invented-here
# syndrome. If we really insist on 3 verbosity levels (normal, verbose, very
# verbose), we should probably do the following:
#
#    * Nuke VERBOSE.
#    * Introduce NOTICE (25).
#    * Make NOTICE the default level.
#    * Optionally introduce EMERGENCY (70) and ALERT (60) for consistency.
#
# This would make our whole logging story much more consistent internally
# (code) and externally (GUI always offers the same levels). Nevertheless, we
# should keep in mind that the Python documentation strongly discourages
# introducing new log levels, at least for libraries. OTOH, with 3 verbosity
# levels, this would force us to log normal stuff with a WARNING level, which
# looks wrong.

# We need an additional log level between INFO and DEBUG to reflect the
# verbose() and vverbose() mechanisms of Check_MK.
VERBOSE = 15
logging.addLevelName(VERBOSE, "VERBOSE")

logger = logging.getLogger("cmk")


def get_formatter(format_str="%(asctime)s [%(levelno)s] [%(name)s %(process)d] %(message)s"):
    # type: (str) -> logging.Formatter
    """Returns a new message formater instance that uses the standard
    Check_MK log format by default. You can also set another format
    if you like."""
    return logging.Formatter(format_str)


def clear_console_logging():
    # type: () -> None
    logger.handlers[:] = []
    logger.addHandler(logging.NullHandler())
    logger.setLevel(logging.INFO)


# Set default logging handler to avoid "No handler found" warnings.
# Python 2.7+
clear_console_logging()


def setup_console_logging():
    # type: () -> None
    """This method enables all log messages to be written to the console
    without any additional information like date/time, logger-name. Just
    the log line is written.

    This can be used for existing command line applications which were
    using sys.stdout.write() or print() before.
    """
    setup_logging_handler(sys.stdout, get_formatter("%(message)s"))


def open_log(log_file_path):
    # type: (Union[str, Path]) -> IOLog
    """Open logfile and fall back to stderr if this is not successfull
    The opened file-like object is returned.
    """
    if not isinstance(log_file_path, Path):
        log_file_path = Path(log_file_path)

    try:
        if sys.version_info[0] >= 3:
            logfile = log_file_path.open("a", encoding="utf-8")  # type: IOLog
        else:
            logfile = log_file_path.open("ab")  # type: IOLog
        logfile.flush()
    except Exception as e:
        logger.exception("Cannot open log file '%s': %s", log_file_path, e)
        logfile = sys.stderr
    setup_logging_handler(logfile)
    return logfile


def setup_logging_handler(stream, formatter=None):
    # type: (IOLog, logging.Formatter) -> None
    """This method enables all log messages to be written to the given
    stream file object. The messages are formated in Check_MK standard
    logging format.
    """
    if formatter is None:
        formatter = get_formatter("%(asctime)s [%(levelno)s] [%(name)s] %(message)s")

    handler = logging.StreamHandler(stream=stream)
    handler.setFormatter(formatter)

    del logger.handlers[:]  # Remove all previously existing handlers
    logger.addHandler(handler)


def verbosity_to_log_level(verbosity):
    # type: (int) -> int
    """Values for "verbosity":

      0: enables INFO and above
      1: enables VERBOSE and above
      2: enables DEBUG and above (ALL messages)
    """
    if verbosity == 0:
        return logging.INFO
    if verbosity == 1:
        return VERBOSE
    if verbosity == 2:
        return logging.DEBUG
    raise ValueError()
