#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime
from typing import Literal

from cmk.utils.schedule import next_scheduled_time

from .job import ScheduleConfig

type NextSchedule = float | Literal["disabled"] | None


def next_schedule(schedule: ScheduleConfig | None, after: datetime) -> NextSchedule:
    """Earliest scheduled start after `after`, "disabled", or None for manual-only jobs."""
    if not schedule:
        return None
    if schedule["disabled"]:
        return "disabled"
    return min(
        (
            next_scheduled_time(schedule["period"], timeofday, after)
            for timeofday in schedule["timeofday"]
        ),
        default=None,
    )
