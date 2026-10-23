#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import datetime as dt
import time

import pytest

from cmk.gui.dashboard.event_bar_chart_window import (
    clamp_event_bar_chart_window,
    exceeds_event_bar_chart_span,
)
from cmk.gui.valuespec import Timerange, TimerangeValue

DAY = 24 * 3600


def _midnight(year: int, month: int, day: int) -> float:
    return time.mktime(dt.date(year, month, day).timetuple())


THREE_YEARS_OF_DATES = ("date", (_midnight(2023, 10, 10), _midnight(2026, 10, 9)))
TWO_YEARS_OF_DATES = ("date", (_midnight(2024, 10, 10), _midnight(2026, 10, 9)))


@pytest.mark.parametrize(
    "window, clamped",
    [
        pytest.param(("age", 800 * DAY), ("age", 730 * DAY), id="an age over two years"),
        pytest.param(800 * DAY, ("age", 730 * DAY), id="a graph time range over two years"),
        pytest.param(THREE_YEARS_OF_DATES, TWO_YEARS_OF_DATES, id="dates over two years"),
        pytest.param(
            ("date", (_midnight(2022, 1, 1), _midnight(2025, 2, 28))),
            ("date", (_midnight(2023, 3, 1), _midnight(2025, 2, 28))),
            id="dates over two years that end before a leap day",
        ),
        pytest.param(("age", 730 * DAY), ("age", 730 * DAY), id="an age of 730 days"),
        pytest.param(TWO_YEARS_OF_DATES, TWO_YEARS_OF_DATES, id="dates of two years"),
        pytest.param("y1", "y1", id="a predefined time range"),
    ],
)
def test_cuts_a_window_to_the_newest_two_years(
    window: TimerangeValue, clamped: TimerangeValue
) -> None:
    assert clamp_event_bar_chart_window(window) == clamped


@pytest.mark.parametrize("window", [("age", 800 * DAY), 800 * DAY, THREE_YEARS_OF_DATES])
def test_a_cut_window_passes_the_span_check(window: TimerangeValue) -> None:
    start, end = Timerange.compute_range(clamp_event_bar_chart_window(window)).range

    assert not exceeds_event_bar_chart_span(start, end)
