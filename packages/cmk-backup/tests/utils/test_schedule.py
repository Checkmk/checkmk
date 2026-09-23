#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from datetime import datetime

from cmk.backup.utils.job import ScheduleConfig
from cmk.backup.utils.schedule import next_schedule

NOW = datetime(2026, 1, 1, 12, 0)


def _daily(timeofday: Sequence[tuple[int, int]], disabled: bool = False) -> ScheduleConfig:
    return {"disabled": disabled, "period": "day", "timeofday": timeofday}


def test_manual_job_has_no_next_run() -> None:
    assert next_schedule(None, after=NOW) is None


def test_disabled_schedule_reports_disabled() -> None:
    assert next_schedule(_daily([(13, 0)], disabled=True), after=NOW) == "disabled"


def test_next_run_is_earliest_upcoming_time() -> None:
    assert (
        next_schedule(_daily([(11, 0), (14, 0)]), after=NOW)
        == datetime(2026, 1, 1, 14, 0).timestamp()
    )
