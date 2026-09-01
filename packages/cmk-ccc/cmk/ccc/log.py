#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from datetime import datetime
from typing import override

__all__ = [
    "CMKFormatter",
]


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
    """

    def __init__(
        self,
        *,
        with_process: bool = False,
        with_thread: bool = False,
        legacy: bool = False,
    ) -> None:
        super().__init__()
        self._with_process = with_process
        self._with_thread = with_thread
        self._legacy = legacy

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
