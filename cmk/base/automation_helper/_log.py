#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from pathlib import Path
from typing import Final

APPLICATION_LOGGER: Final = "automation-helper"

logger = logging.getLogger(APPLICATION_LOGGER)


def configure_logger(log_directory: Path) -> None:
    handler = logging.FileHandler(log_directory / f"{APPLICATION_LOGGER}.log", encoding="UTF-8")
    formatter = logging.Formatter("%(asctime)s [%(levelno)s] [%(name)s %(process)d] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
