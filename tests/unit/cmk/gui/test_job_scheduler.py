#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui import cron
from cmk.gui.job_scheduler import _run_scheduled_jobs


def test_cmk_run_cron_jobs() -> None:
    orig_jobs = list(cron.cron_job_registry.values())
    try:
        cron.cron_job_registry.clear()
        _run_scheduled_jobs()
    finally:
        for job in orig_jobs:
            cron.cron_job_registry.register(job)
