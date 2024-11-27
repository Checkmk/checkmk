#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from pathlib import Path
from typing import Final

APP_LOGGER_NAME: Final = "automation-helper"

app_logger = logging.getLogger(APP_LOGGER_NAME)


def configure_app_logger(log_directory: Path) -> None:
    handler = logging.FileHandler(log_directory / f"{APP_LOGGER_NAME}.log", encoding="UTF-8")
    log_format = f"%(asctime)s [%(levelno)s] [{APP_LOGGER_NAME} %(process)d] %(message)s"
    formatter = logging.Formatter(log_format)
    handler.setFormatter(formatter)
    app_logger.addHandler(handler)
    app_logger.setLevel(logging.INFO)
