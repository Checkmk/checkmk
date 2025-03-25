#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
import logging
from collections.abc import Generator
from logging import Logger
from pathlib import Path

LOGGER = logging.getLogger()


def configure_logger(log_directory: Path) -> None:
    handler = logging.FileHandler(log_directory / "automation-helper.log", encoding="UTF-8")
    formatter = logging.Formatter("%(asctime)s [%(levelno)s] [%(process)d] %(message)s")
    handler.setFormatter(formatter)
    LOGGER.addHandler(handler)
    LOGGER.setLevel(logging.INFO)


@contextlib.contextmanager
def temporary_log_level(logger: Logger, level: int) -> Generator[None]:
    prev_level = logger.level
    try:
        logger.setLevel(level)
        yield
    finally:
        logger.setLevel(prev_level)
