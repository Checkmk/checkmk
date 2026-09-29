#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from datetime import datetime
from typing import override


class _CMKFormatter(logging.Formatter):
    """Reduced copy of `cmk.ccc.log.CMKFormatter`, which the plug-in APIs may not import

    `with_source` adds where the record was logged to the logger name.
    """

    def __init__(self, *, with_source: bool = False) -> None:
        super().__init__()
        self._with_source = with_source

    def _ident(self, record: logging.LogRecord) -> str:
        if self._with_source:
            return f"{record.name} {record.filename}:{record.lineno} {record.funcName}"
        return record.name

    @override
    def formatMessage(self, record: logging.LogRecord) -> str:
        timestamp = self.formatTime(record)
        return f"{timestamp} [{self._ident(record)}] [{record.levelname}] {record.message}"

    @override
    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        return (
            datetime.fromtimestamp(record.created)
            .astimezone()
            .isoformat(sep=" ", timespec="milliseconds")
        )


def configure_logging(level: int) -> None:
    """Write log records to stderr in the Checkmk log format

    Use it instead of `logging.basicConfig`. It replaces any logging configuration
    already in place. The records are written like this::

        2026-06-26 14:32:45.123+02:00 [cmk.plugins.myagent] [INFO] the message

    Below `logging.INFO`, the file, line and function the record was logged in follow
    the logger name::

        2026-06-26 14:32:45.123+02:00 [cmk.plugins.myagent agent.py:42 main] [DEBUG] the message

    Args:
        level: The lowest level written, for instance `logging.INFO`
    """
    handler = logging.StreamHandler()
    handler.setFormatter(_CMKFormatter(with_source=level < logging.INFO))
    logging.basicConfig(level=level, handlers=[handler], force=True)
