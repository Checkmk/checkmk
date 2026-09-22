#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from datetime import datetime
from pathlib import Path
from typing import override

_LOGGER_NAME = "cmk.werks.ids"


class _WerkIdFormatter(logging.Formatter):
    def __init__(self) -> None:
        super().__init__("%(asctime)s [%(name)s] [%(levelname)s] %(message)s")

    @override
    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        return (
            datetime.fromtimestamp(record.created)
            .astimezone()
            .isoformat(sep=" ", timespec="milliseconds")
        )


def get_werk_id_logger(path: Path) -> logging.Logger:
    path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(logging.INFO)
    # The werk tool prints its own output and configures no root logger, so the entries
    # belong in the file and nowhere else.
    logger.propagate = False
    handler = logging.FileHandler(path, encoding="utf-8", delay=True)
    handler.setFormatter(_WerkIdFormatter())
    # Replaced rather than added, so opening a second log does not write every entry twice.
    logger.handlers = [handler]
    return logger
