#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# The expected ticks are the ones cmk-frontend-vue's timeAxis.test.ts expects for the same
# inputs: the PNG time axis must match the on-screen one.

import datetime
from zoneinfo import ZoneInfo

import pytest

from cmk.gui.graphing._time_axis import compute_time_axis, TimeAxisTick

BERLIN = ZoneInfo("Europe/Berlin")
CHAR_WIDTH_PX = 6
PLOT_WIDTH_PX = 770


def _measure_label(text: str) -> float:
    return len(text) * CHAR_WIDTH_PX


def _ticks(start: float, end: float, tz: datetime.tzinfo = BERLIN) -> list[TimeAxisTick]:
    return compute_time_axis(start, end, PLOT_WIDTH_PX, _measure_label, tz)


def _utc(year: int, month: int, day: int, hour: int = 0) -> int:
    return int(datetime.datetime(year, month, day, hour, tzinfo=datetime.UTC).timestamp())


def test_labels_a_within_day_range_as_hour_and_minute() -> None:
    assert _ticks(1668502320, 1668516720) == [
        TimeAxisTick(position=position, text=text, line_width=2)
        for position, text in [
            (1668502800, "10:00"),
            (1668504000, "10:20"),
            (1668505200, "10:40"),
            (1668506400, "11:00"),
            (1668507600, "11:20"),
            (1668508800, "11:40"),
            (1668510000, "12:00"),
            (1668511200, "12:20"),
            (1668512400, "12:40"),
            (1668513600, "13:00"),
            (1668514800, "13:20"),
            (1668516000, "13:40"),
        ]
    ]


def test_labels_a_sub_week_range_as_weekday_and_time() -> None:
    assert _ticks(1668426600, 1668516600) == [
        TimeAxisTick(position=position, text=text, line_width=2)
        for position, text in [
            (1668438000, "Mon 16:00"),
            (1668452400, "Mon 20:00"),
            (1668466800, "Tue 00:00"),
            (1668481200, "Tue 04:00"),
            (1668495600, "Tue 08:00"),
            (1668510000, "Tue 12:00"),
        ]
    ]


def test_labels_a_within_month_range_as_centered_day_of_month() -> None:
    day_boundaries = range(1667862000, 1668510000, 86400)

    assert _ticks(1667826000, 1668517200) == [
        tick
        for day, boundary in enumerate(day_boundaries, start=8)
        for tick in (
            TimeAxisTick(position=boundary, text=None, line_width=2),
            TimeAxisTick(position=boundary + 43200, text=f"{day:02d}", line_width=0),
        )
    ]


def test_labels_a_within_year_range_as_month_and_day() -> None:
    assert _ticks(1665486000, 1668519000) == [
        TimeAxisTick(position=position, text=text, line_width=2)
        for position, text in [
            (1665698400, "10-14"),
            (1665957600, "10-17"),
            (1666216800, "10-20"),
            (1666476000, "10-23"),
            (1666735200, "10-26"),
            (1666994400, "10-29"),
            (1667257200, "11-01"),
            (1667516400, "11-04"),
            (1667775600, "11-07"),
            (1668034800, "11-10"),
            (1668294000, "11-13"),
        ]
    ]


def test_labels_a_multi_year_range_as_iso_date() -> None:
    assert _ticks(1633910400, 1668470400) == [
        TimeAxisTick(position=position, text=text, line_width=2)
        for position, text in [
            (1638313200, "2021-12-01"),
            (1643670000, "2022-02-01"),
            (1648764000, "2022-04-01"),
            (1654034400, "2022-06-01"),
            (1659304800, "2022-08-01"),
            (1664575200, "2022-10-01"),
        ]
    ]


@pytest.mark.parametrize("days", [400, 35, 8, 25 / 24])
def test_labels_do_not_overlap_or_overflow_the_plot(days: float) -> None:
    plot_width = 750
    start = 1633910400
    end = start + days * 86400

    boxes = [
        (center - _measure_label(tick.text) / 2, center + _measure_label(tick.text) / 2)
        for tick in compute_time_axis(start, end, plot_width, _measure_label, BERLIN)
        if tick.text is not None
        for center in [(tick.position - start) / (end - start) * plot_width]
    ]

    assert len(boxes) > 2
    assert boxes[0][0] >= 0
    assert boxes[-1][1] <= plot_width
    assert all(left > previous_right for (_, previous_right), (left, _) in zip(boxes, boxes[1:]))


def test_aligns_weekly_spaced_ticks_to_mondays() -> None:
    start = 1659312000

    ticks = _ticks(start, start + 60 * 86400)

    assert len(ticks) > 2
    assert {datetime.datetime.fromtimestamp(t.position, BERLIN).weekday() for t in ticks} == {0}


def test_aligns_ticks_to_local_midnight_in_a_half_hour_offset_zone() -> None:
    kolkata = ZoneInfo("Asia/Kolkata")

    grid_ticks = [t for t in _ticks(1665486000, 1668519000, kolkata) if t.line_width > 0]

    assert grid_ticks
    for tick in grid_ticks:
        local = datetime.datetime.fromtimestamp(tick.position, kolkata)
        assert (local.hour, local.minute) == (0, 0)


def test_keeps_daily_ticks_on_local_midnight_across_a_dst_spring_forward() -> None:
    grid_ticks = [t for t in _ticks(_utc(2024, 3, 25), _utc(2024, 4, 6)) if t.line_width > 0]

    assert len(grid_ticks) > 2
    assert {datetime.datetime.fromtimestamp(t.position, BERLIN).hour for t in grid_ticks} == {0}


@pytest.mark.parametrize(
    "midnight",
    [
        pytest.param(_utc(2022, 3, 26, 23), id="spring-forward"),
        pytest.param(_utc(2022, 10, 29, 22), id="fall-back"),
    ],
)
def test_hourly_labels_across_a_dst_shift_are_unique(midnight: int) -> None:
    labels = [t.text for t in _ticks(midnight, midnight + 8 * 3600) if t.text is not None]

    assert len(labels) > 2
    assert len(set(labels)) == len(labels)


def test_keeps_a_tick_for_both_instants_of_the_repeated_fall_back_hour() -> None:
    midnight = _utc(2022, 10, 29, 22)
    two_am_cest = _utc(2022, 10, 30, 0)
    two_am_cet = _utc(2022, 10, 30, 1)

    ticks = {t.position: t for t in _ticks(midnight, midnight + 8 * 3600)}

    assert ticks[two_am_cest] == TimeAxisTick(position=two_am_cest, text="02:00", line_width=2)
    assert ticks[two_am_cet] == TimeAxisTick(position=two_am_cet, text=None, line_width=2)


def test_returns_no_ticks_for_an_empty_range() -> None:
    assert _ticks(1_700_000_000, 1_700_000_000) == []


def test_yields_at_least_two_ticks_on_a_very_narrow_plot() -> None:
    assert len(compute_time_axis(1668502320, 1668516720, 4, _measure_label, BERLIN)) >= 2


def test_ticks_a_window_narrower_than_one_step() -> None:
    midnight = _utc(2026, 4, 21)

    assert len(_ticks(midnight, midnight + 600)) >= 2
