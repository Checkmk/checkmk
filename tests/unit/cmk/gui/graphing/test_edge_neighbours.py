#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.graphing_engine import TimeRange
from cmk.gui.graphing._edge_neighbours import expected_served_step

_MINUTE = 60
_HOUR = 60 * _MINUTE
_DAY = 24 * _HOUR
_NOW = 1_800_000_000


def _half_hour_ending(ago: int, *, step: int = _MINUTE) -> TimeRange:
    end = _NOW - ago
    return TimeRange(start=end - 30 * _MINUTE, end=end, step=step)


@pytest.mark.parametrize(
    "window, served_step",
    [
        pytest.param(_half_hour_ending(0), _MINUTE, id="just now"),
        pytest.param(_half_hour_ending(_DAY), _MINUTE, id="yesterday"),
        pytest.param(_half_hour_ending(7 * _DAY), 5 * _MINUTE, id="a week ago"),
        pytest.param(_half_hour_ending(60 * _DAY), 30 * _MINUTE, id="two months ago"),
        pytest.param(_half_hour_ending(400 * _DAY), 6 * _HOUR, id="over a year ago"),
        pytest.param(_half_hour_ending(3650 * _DAY), 6 * _HOUR, id="older than any archive keeps"),
    ],
)
def test_the_finest_default_archive_reaching_back_to_the_window_is_expected_to_answer(
    window: TimeRange, served_step: int
) -> None:
    step = expected_served_step(window, now=_NOW)

    assert step == served_step


def test_neighbours_reaching_past_an_archive_expect_the_next_coarser_one() -> None:
    window = TimeRange(start=_NOW - 2 * _DAY + _MINUTE, end=_NOW - _DAY, step=_MINUTE)

    step = expected_served_step(window, now=_NOW)

    assert step == 5 * _MINUTE


def test_a_requested_step_coarser_than_the_archive_is_expected_instead() -> None:
    window = _half_hour_ending(0, step=10 * _MINUTE)

    step = expected_served_step(window, now=_NOW)

    assert step == 10 * _MINUTE
