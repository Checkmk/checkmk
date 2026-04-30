#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Final

from cmk.bi.compiler import BICompiler
from cmk.bi.log import LOGGER
from cmk.gui.bi.bi_manager import create_default_sites_callback, get_bi_config_path
from cmk.gui.config import Config
from cmk.gui.job_scheduler_client import JobSchedulerClient

COMPILE_BI_AGGREGATIONS_JOB_ID: Final = "compile_bi_aggregations"


def compile_bi_aggregations(config: Config) -> None:
    compiler = BICompiler(get_bi_config_path(), create_default_sites_callback())
    compiler.compile_if_needed()


def reset_compile_bi_aggregations_scheduling() -> None:
    response = JobSchedulerClient().post(
        "reset_scheduling",
        {"job_id": COMPILE_BI_AGGREGATIONS_JOB_ID},
    )
    if response.is_error():
        LOGGER.error("Cannot reset scheduler: %(error)r", {"error": response.error})
