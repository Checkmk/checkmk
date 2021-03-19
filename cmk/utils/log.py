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
import logging as _logging
from logging.handlers import WatchedFileHandler
from typing import Any  # pylint: disable=unused-import

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

# Users should be able to set log levels without importing "logging"

CRITICAL = _logging.CRITICAL
ERROR = _logging.ERROR
WARNING = _logging.WARNING
INFO = _logging.INFO
DEBUG = _logging.DEBUG

# We need an additional log level between INFO and DEBUG to reflect the
# verbose() and vverbose() mechanisms of Check_MK.

VERBOSE = 15

_logger_class = _logging.getLoggerClass()  # type: Any


class CMKLogger(_logger_class):
    def __init__(self, name, level=_logging.NOTSET):
        super(CMKLogger, self).__init__(name, level)

        _logging.addLevelName(VERBOSE, "VERBOSE")

    def verbose(self, msg, *args, **kwargs):
        if self.is_verbose():
            self._log(VERBOSE, msg, args, **kwargs)

    def is_verbose(self):
        return self.isEnabledFor(VERBOSE)

    def is_very_verbose(self):
        return self.isEnabledFor(DEBUG)

    def set_format(self, fmt):
        handler = _logging.StreamHandler(stream=sys.stdout)
        handler.setFormatter(get_formatter(fmt))

        del self.handlers[:]  # Remove all previously existing handlers
        self.addHandler(handler)


_logging.setLoggerClass(CMKLogger)

# Set default logging handler to avoid "No handler found" warnings.
# Python 2.7+
logger = _logging.getLogger("cmk")
logger.addHandler(_logging.NullHandler())
logger.setLevel(INFO)


def get_logger(name):
    """This function provides the logging object for client code.

    It returns a child logger of the "cmk" main logger, identified
    by the given name. The name of the child logger will be prefixed
    with "cmk.", for example "cmk.mkeventd" in case of "mkeventd".
    """
    return logger.getChild(name)


def get_formatter(format_str="%(asctime)s [%(levelno)s] [%(name)s %(process)d] %(message)s"):
    """Returns a new message formater instance that uses the standard
    Check_MK log format by default. You can also set another format
    if you like."""
    return _logging.Formatter(format_str)


def setup_console_logging(stream=None, formatter=None):
    """This method enables all log messages to be written to the console
    without any additional information like date/time, logger-name. Just
    the log line is written.

    This can be used for existing command line applications which were
    using sys.stdout.write() or print() before.
    """
    if stream is None:
        stream = sys.stdout

    if formatter is None:
        formatter = get_formatter("%(message)s")

    setup_logging_handler(stream, formatter)


def open_log(log_file_path, fallback_to=None):
    """Open logfile and fall back to stderr if this is not successfull
    The opened file() object is returned.
    """
    if fallback_to is None:
        fallback_to = sys.stderr

    logfile = None
    try:
        logfile = file(log_file_path, "a")
        logfile.flush()
    except Exception as e:
        logger.exception("Cannot open log file '%s': %s", log_file_path, e)

        if fallback_to:
            logfile = fallback_to

    if logfile:
        setup_logging_handler(logfile)

    return logfile


def setup_watched_file_logging_handler(logfile, formatter=None):
    """Removes all previous logger handlers and set a logfile handler for the given logfile path
    This handler automatically reopens the logfile if it detects an inode change, e.g through logrotate
    """
    if formatter is None:
        formatter = get_default_formatter()

    handler = WatchedFileHandler(logfile)
    handler.setFormatter(formatter)
    del logger.handlers[:]  # Remove all previously existing handlers
    logger.addHandler(handler)


def setup_logging_handler(stream, formatter=None):
    """This method enables all log messages to be written to the given
    stream file object. The messages are formated in Check_MK standard
    logging format.
    """
    if formatter is None:
        formatter = get_default_formatter()

    handler = _logging.StreamHandler(stream=stream)
    handler.setFormatter(formatter)

    del logger.handlers[:]  # Remove all previously existing handlers
    logger.addHandler(handler)


def get_default_formatter():
    return get_formatter("%(asctime)s [%(levelno)s] [%(name)s] %(message)s")


def set_verbosity(verbosity):
    """Values for "verbosity":

      0: enables INFO and above
      1: enables VERBOSE and above
      2: enables DEBUG and above (ALL messages)
    """
    if verbosity == 0:
        logger.setLevel(INFO)

    elif verbosity == 1:
        logger.setLevel(VERBOSE)

    elif verbosity >= 2:
        logger.setLevel(DEBUG)


# TODO: Experiment. Not yet used.
class LogMixin(object):
    """Inherit from this class to provide logging support.

    Makes a logger available via "self.logger" for objects and
    "self.cls_logger" for the class.
    """
    __parent_logger = None
    __logger = None
    __cls_logger = None

    @property
    def _logger(self):
        if not self.__logger:
            parent = self.__parent_logger or logger
            self.__logger = parent.getChild('.'.join([self.__class__.__name__]))
        return self.__logger

    @classmethod
    def _cls_logger(cls):
        if not cls.__cls_logger:
            parent = cls.__parent_logger or logger
            cls.__cls_logger = parent.getChild('.'.join([cls.__name__]))
        return cls.__cls_logger
