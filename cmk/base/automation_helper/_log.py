#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from pathlib import Path
from typing import Final

LOGGER_NAME: Final = "automation-helper"

logger = logging.getLogger(LOGGER_NAME)


def configure_logger(log_directory: Path) -> None:
    handler = logging.FileHandler(log_directory / f"{LOGGER_NAME}.log", encoding="UTF-8")
    log_format = f"%(asctime)s [%(levelno)s] [{LOGGER_NAME} %(process)d] %(message)s"
    formatter = logging.Formatter(log_format)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
