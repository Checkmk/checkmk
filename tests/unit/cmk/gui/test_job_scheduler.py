#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime, timedelta, UTC

import time_machine

from cmk.gui.cron import CronJob
from cmk.gui.job_scheduler import run_scheduled_jobs


def test_run_scheduled_jobs() -> None:
    called = {
        "job1": 0,
        "job2": 0,
    }
    jobs = [
        CronJob(
            name="job1",
            callable=lambda: called.update({"job1": called["job1"] + 1}),
            interval=timedelta(minutes=1),
        ),
        CronJob(
            name="job2",
            callable=lambda: called.update({"job2": called["job2"] + 1}),
            interval=timedelta(minutes=5),
        ),
    ]

    with time_machine.travel(datetime.fromtimestamp(0, tz=UTC), tick=False):
        run_scheduled_jobs(jobs)

    assert called["job1"] == 1
    assert called["job2"] == 1

    with time_machine.travel(datetime.fromtimestamp(60, tz=UTC), tick=False):
        run_scheduled_jobs(jobs)

    assert called["job1"] == 2
    assert called["job2"] == 1

    with time_machine.travel(datetime.fromtimestamp(300, tz=UTC), tick=False):
        run_scheduled_jobs(jobs)

    assert called["job1"] == 3
    assert called["job2"] == 2
