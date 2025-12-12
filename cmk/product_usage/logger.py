#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import logging.handlers
from pathlib import Path


def get_product_usage_logger() -> logging.Logger:
    return logging.getLogger("cmk.product_usage")


def init_logging(log_dir: Path, level: str | int = logging.INFO) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter("%(asctime)s [%(levelno)s] [%(name)s %(process)d] %(message)s")

    handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / "product_usage_analytics.log", maxBytes=5 * 1024 * 2014, backupCount=3
    )

    handler.setFormatter(formatter)

    logger = get_product_usage_logger()
    del logger.handlers[:]  # Remove all previously existing handlers
    logger.addHandler(handler)
    logger.propagate = False
    logger.setLevel(level)

    return logger
