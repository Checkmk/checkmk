#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from functools import partial
from pathlib import Path

from cmk.ccc import store

from cmk.utils.paths import tmp_dir

from cmk.gui import main_modules
from cmk.gui.cron import multisite_cronjobs
from cmk.gui.log import init_logging, logger
from cmk.gui.session import SuperUserContext
from cmk.gui.utils.script_helpers import gui_context


def _lock_file() -> Path:
    return tmp_dir / "cron.lastrun"


def _run_scheduled_jobs() -> None:
    lock_file = _lock_file()
    main_modules.load_plugins()

    with store.locked(lock_file), gui_context(), SuperUserContext():
        logger.debug("Starting cron jobs")

        for cron_job in multisite_cronjobs:
            try:
                job_name = (
                    cron_job.func.__name__ if isinstance(cron_job, partial) else cron_job.__name__
                )

                logger.debug("Starting [%s]", job_name)
                cron_job()
                logger.debug("Finished [%s]", job_name)
            except Exception:
                logger.exception("Exception in cron job [%s]", job_name)

        logger.debug("Finished all cron jobs")


def main() -> int:
    init_logging()
    _run_scheduled_jobs()
    return 0
