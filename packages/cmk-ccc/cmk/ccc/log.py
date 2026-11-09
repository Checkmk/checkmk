#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from datetime import datetime
from logging.handlers import WatchedFileHandler
from pathlib import Path
from typing import Final, override

__all__ = [
    "CMKFormatter",
    "log_to_watched_file",
    "VERBOSE",
    "verbosity_to_log_level",
]

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
# verbose() and vverbose() mechanisms of Checkmk.
VERBOSE: Final = 15
logging.addLevelName(VERBOSE, "VERBOSE")


def verbosity_to_log_level(verbosity: int) -> int:
    match verbosity:
        case 0:
            return logging.INFO
        case 1:
            return VERBOSE
        case _:
            return logging.DEBUG


class CMKFormatter(logging.Formatter):
    """Formats every Checkmk log line, so that all logs share one format.

    With ``with_process`` and ``with_thread`` both on::

        2026-06-26 14:32:45.123+02:00 [cmk.web cmk-worker(12345) worker-2] [INFO] the message

    The process renders as ``name(pid)`` because names may contain spaces.
    There is no numeric thread id:
    ``logging.LogRecord.thread`` is a pthread handle, not the OS thread id.

    ``legacy=True`` reproduces the historical format byte-for-byte, so that a
    log can move onto this formatter without its lines changing::

        2026-06-26 14:32:45,123 [20] [cmk.web 12345] the message

    The ``message_only=True`` mode renders just the bare message, with no
    timestamp, level or logger name. It is meant for interactive command line
    output, where the surrounding metadata would only be noise. Routing that
    case through this formatter too keeps every handler on a single formatter
    type. It takes precedence over the other flags.
    """

    def __init__(
        self,
        *,
        with_process: bool = False,
        with_thread: bool = False,
        legacy: bool = False,
        message_only: bool = False,
    ) -> None:
        super().__init__()
        self._with_process = with_process
        self._with_thread = with_thread
        self._legacy = legacy
        self._message_only = message_only

    def _ident(self, record: logging.LogRecord) -> str:
        fields = [record.name]
        if self._with_process:
            fields.append(
                f"{record.process}" if self._legacy else f"{record.processName}({record.process})"
            )
        if self._with_thread:
            fields.append(f"{record.threadName}")
        return " ".join(fields)

    @override
    def formatMessage(self, record: logging.LogRecord) -> str:
        if self._message_only:
            return record.message
        timestamp = self.formatTime(record)
        ident = self._ident(record)
        if self._legacy:
            return f"{timestamp} [{record.levelno}] [{ident}] {record.message}"
        return f"{timestamp} [{ident}] [{record.levelname}] {record.message}"

    @override
    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        if self._legacy:
            # The stdlib default rendering is exactly the historical Checkmk one.
            # e.g. "2026-06-26 14:32:45,123"
            return super().formatTime(record, datefmt)
        # ISO 8601 with milliseconds and the local timezone offset, using a
        # space instead of the literal "T" so date and time stay readable,
        # e.g. "2026-06-26 14:32:45.123+02:00".
        return (
            datetime.fromtimestamp(record.created)
            .astimezone()
            .isoformat(sep=" ", timespec="milliseconds")
        )


def log_to_watched_file(logger: logging.Logger, path: Path) -> None:
    handler = WatchedFileHandler(path)
    handler.setFormatter(CMKFormatter())
    del logger.handlers[:]
    logger.addHandler(handler)
