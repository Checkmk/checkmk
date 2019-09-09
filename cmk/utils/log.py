#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2016             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import sys
import logging
from typing import IO, Any  # pylint: disable=unused-import

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

# Set default logging handler to avoid "No handler found" warnings.
# Python 2.7+
logger = logging.getLogger("cmk")
logger.addHandler(logging.NullHandler())
logger.setLevel(logging.INFO)


def get_formatter(format_str="%(asctime)s [%(levelno)s] [%(name)s %(process)d] %(message)s"):
    # type: (str) -> logging.Formatter
    """Returns a new message formater instance that uses the standard
    Check_MK log format by default. You can also set another format
    if you like."""
    return logging.Formatter(format_str)


def setup_console_logging():
    # type: () -> None
    """This method enables all log messages to be written to the console
    without any additional information like date/time, logger-name. Just
    the log line is written.

    This can be used for existing command line applications which were
    using sys.stdout.write() or print() before.
    """
    setup_logging_handler(sys.stdout, get_formatter("%(message)s"))


# TODO: Cleanup IO[Any] to IO[Text]
def open_log(log_file_path):
    # type: (str) -> IO[Any]
    """Open logfile and fall back to stderr if this is not successfull
    The opened file-like object is returned.
    """
    try:
        logfile = open(log_file_path, "a")  # type: IO[Any]
        logfile.flush()
    except Exception as e:
        logger.exception("Cannot open log file '%s': %s", log_file_path, e)
        logfile = sys.stderr
    setup_logging_handler(logfile)
    return logfile


def setup_logging_handler(stream, formatter=None):
    # type: (IO[Any], logging.Formatter) -> None
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
