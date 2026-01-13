#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.utils.paths import log_dir

from cmk.product_usage.logger import init_logging


def test_init_logging() -> None:
    assert not (Path(log_dir) / "product_usage_analytics.log").exists()

    logger = init_logging(Path(log_dir))
    assert (Path(log_dir) / "product_usage_analytics.log").exists()

    log_message = "Test log entry"
    logger.info(log_message)

    with (Path(log_dir) / "product_usage_analytics.log").open("r", encoding="utf-8") as log_file:
        lines = log_file.readlines()
        assert len(lines) == 1
        assert log_message in lines[0]
