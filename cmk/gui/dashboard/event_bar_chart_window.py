#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import datetime as dt
import time

from dateutil.relativedelta import relativedelta

from cmk.gui.valuespec import TimerangeValue

EVENT_BAR_CHART_TYPES = frozenset({"alerts_bar_chart", "notifications_bar_chart"})

_MAX_AGE_SECONDS = 730 * 24 * 3600


def exceeds_event_bar_chart_span(start: int, end: int) -> bool:
    """Whether a window of the alert or notification timeline spans more than two years."""
    limit = dt.datetime.fromtimestamp(start, tz=dt.UTC) + relativedelta(years=2)
    return dt.datetime.fromtimestamp(end, tz=dt.UTC) > limit


def clamp_event_bar_chart_window(window: TimerangeValue) -> TimerangeValue:
    """The window of the alert or notification timeline, cut to the newest two years."""
    match window:
        case int() as age if age > _MAX_AGE_SECONDS:
            return ("age", _MAX_AGE_SECONDS)
        case ("age", int() as age) if age > _MAX_AGE_SECONDS:
            return ("age", _MAX_AGE_SECONDS)
        case ("date", (start, end)):
            first = _first_day_within_two_years(end)
            return ("date", (first, end)) if start < first else window
        case _:
            return window


def _first_day_within_two_years(last_day: float) -> float:
    day_after = dt.date.fromtimestamp(last_day) + dt.timedelta(days=1)
    until = int(_local_midnight(day_after))
    first_day = day_after - relativedelta(years=2)
    while exceeds_event_bar_chart_span(int(_local_midnight(first_day)), until):
        first_day += dt.timedelta(days=1)
    return _local_midnight(first_day)


def _local_midnight(day: dt.date) -> float:
    return time.mktime(day.timetuple())
