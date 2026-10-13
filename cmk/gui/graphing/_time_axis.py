#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The time axis ticks of a graph, computed the same way as cmk-frontend-vue's
TimeSeriesGraph/axes/timeAxis.ts, so a PNG graph labels its time axis like the on-screen one.

The timezone is injected (None: the local zone) so the axis is deterministic and testable
across zones. Label widths are measured, so tick density follows the text that is really drawn.
"""

import datetime
import math
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Literal

_SECONDS_PER_DAY = 86_400
_DAYS_PER_WEEK = 7
_MIN_LABEL_GAP_PX = 24

type MeasureLabel = Callable[[str], float]
type _Format = Literal["%H:%M", "%a %H:%M", "%d", "%m-%d", "%Y-%m-%d"]
type _Producer = Callable[[datetime.datetime, datetime.datetime], Iterator[datetime.datetime]]


@dataclass(frozen=True)
class TimeAxisTick:
    position: int
    text: str | None
    line_width: int


@dataclass(frozen=True)
class _Labelling:
    format: _Format
    label_shift: int = 0
    label_distance_at_least: int = 0


# Every label of a given format has the same digit count, so one sample stands in for all of them.
_WIDEST_LABEL_SAMPLE: dict[_Format, str] = {
    "%H:%M": "00:00",
    "%d": "00",
    "%m-%d": "00-00",
    "%Y-%m-%d": "0000-00-00",
}


def _pick_labelling(
    start: datetime.datetime, end: datetime.datetime, time_range_days: float
) -> _Labelling:
    same_year = start.year == end.year
    same_month = same_year and start.month == end.month
    same_date = same_month and start.day == end.day

    if same_date:
        return _Labelling("%H:%M")
    if time_range_days < 7:
        return _Labelling("%a %H:%M")
    if time_range_days < 32 and same_month:
        return _Labelling(
            "%d",
            label_shift=_SECONDS_PER_DAY // 2,
            label_distance_at_least=_SECONDS_PER_DAY,
        )
    if same_year:
        return _Labelling("%m-%d")
    return _Labelling("%Y-%m-%d")


def _widest_label_width(
    labelling: _Labelling, start: datetime.datetime, measure_label: MeasureLabel
) -> float:
    if labelling.format == "%a %H:%M":
        return max(
            measure_label(_format_label(labelling.format, _add_days(start, day_offset)))
            for day_offset in range(_DAYS_PER_WEEK)
        )
    return measure_label(_WIDEST_LABEL_SAMPLE[labelling.format])


def _format_label(label_format: _Format, dt: datetime.datetime) -> str:
    return dt.strftime(label_format)


def _from_timestamp(timestamp: float, tz: datetime.tzinfo | None) -> datetime.datetime:
    # tz=None yields a naive local datetime whose timestamp() resolves through the local zone.
    return datetime.datetime.fromtimestamp(timestamp, tz)


def _add_seconds(dt: datetime.datetime, seconds: int) -> datetime.datetime:
    # Absolute time, so a step across a DST fall-back reaches both instants of the repeated hour.
    return _from_timestamp(dt.timestamp() + seconds, dt.tzinfo)


def _add_days(dt: datetime.datetime, days: int) -> datetime.datetime:
    # Wall-clock time, so a daily step stays on local midnight across a DST shift.
    return (dt + datetime.timedelta(days=days)).replace(fold=0)


def _add_months(dt: datetime.datetime, months: int) -> datetime.datetime:
    # Only ever applied to the first of a month, so the day never needs clamping.
    year, month_index = divmod(dt.month - 1 + months, 12)
    return dt.replace(year=dt.year + year, month=month_index + 1, fold=0)


def _start_of_day(dt: datetime.datetime) -> datetime.datetime:
    return dt.replace(hour=0, minute=0, second=0, microsecond=0, fold=0)


def _t_axis_labels(
    start: datetime.datetime,
    end: datetime.datetime,
    add_step: Callable[[datetime.datetime], datetime.datetime],
    initial_position: datetime.datetime,
) -> Iterator[datetime.datetime]:
    # Compared as instants: naive local datetimes compare by wall clock, which a DST shift breaks.
    position = (
        add_step(initial_position)
        if initial_position.timestamp() < start.timestamp()
        else initial_position
    )
    while position.timestamp() <= end.timestamp():
        yield position
        position = add_step(position)


def _seconds_producer(step_seconds: int) -> _Producer:
    def produce(start: datetime.datetime, end: datetime.datetime) -> Iterator[datetime.datetime]:
        midnight = _start_of_day(start)
        seconds_since_midnight = math.floor(start.timestamp() - midnight.timestamp())
        initial_offset = seconds_since_midnight // step_seconds * step_seconds
        return _t_axis_labels(
            start,
            end,
            lambda dt: _add_seconds(dt, step_seconds),
            _add_seconds(midnight, initial_offset),
        )

    return produce


def _days_producer(step_days: int) -> _Producer:
    def produce(start: datetime.datetime, end: datetime.datetime) -> Iterator[datetime.datetime]:
        return _t_axis_labels(start, end, lambda dt: _add_days(dt, step_days), _start_of_day(start))

    return produce


def _week_producer(start: datetime.datetime, end: datetime.datetime) -> Iterator[datetime.datetime]:
    monday = _add_days(_start_of_day(start), -start.weekday())
    return _t_axis_labels(start, end, lambda dt: _add_days(dt, _DAYS_PER_WEEK), monday)


def _months_producer(step_months: int) -> _Producer:
    def produce(start: datetime.datetime, end: datetime.datetime) -> Iterator[datetime.datetime]:
        first_of_month = _start_of_day(start).replace(day=1)
        return _t_axis_labels(start, end, lambda dt: _add_months(dt, step_months), first_of_month)

    return produce


def _select_tick_producer(min_distance: float) -> _Producer:
    for dist_minutes in (1, 2, 5, 10, 20, 30, 60, 120, 240, 360, 480, 720):
        if min_distance <= dist_minutes * 60:
            return _seconds_producer(dist_minutes * 60)
    for dist_days in (1, 2, 3, 4):
        if min_distance <= dist_days * _SECONDS_PER_DAY:
            return _days_producer(dist_days)
    if min_distance <= _SECONDS_PER_DAY * _DAYS_PER_WEEK:
        return _week_producer
    for step_months in (1, 2, 3, 4, 6, 12, 18, 24, 36, 48):
        if min_distance <= _SECONDS_PER_DAY * 31 * step_months:
            return _months_producer(step_months)
    return _months_producer(96)


def compute_time_axis(
    start_time: float,
    end_time: float,
    plot_width: float,
    measure_label: MeasureLabel,
    tz: datetime.tzinfo | None = None,
) -> list[TimeAxisTick]:
    time_range = end_time - start_time
    if time_range <= 0:
        return []
    seconds_per_pixel = time_range / max(plot_width, 1)

    def position_to_x(position: float) -> float:
        return (position - start_time) / seconds_per_pixel

    start = _from_timestamp(start_time, tz)
    end = _from_timestamp(end_time, tz)

    labelling = _pick_labelling(start, end, time_range / _SECONDS_PER_DAY)
    required_distance = (
        _widest_label_width(labelling, start, measure_label) + _MIN_LABEL_GAP_PX
    ) * seconds_per_pixel
    producer = _select_tick_producer(
        # Half the range is the floor, so even a plot too narrow for a single label still gets
        # a couple of grid lines.
        max(labelling.label_distance_at_least, min(required_distance, time_range / 2))
    )

    ticks: list[TimeAxisTick] = []
    emitted_labels: set[str] = set()
    previous_label_right_edge = -math.inf
    for position_dt in producer(start, end):
        line_width = 2
        position = round(position_dt.timestamp())
        label: str | None = _format_label(labelling.format, position_dt)

        if labelling.label_shift:
            ticks.append(TimeAxisTick(position=position, text=None, line_width=line_width))
            line_width = 0
            position += labelling.label_shift

        # A DST fall-back repeats a local hour, so wall-clock labels ("02:00") would show up
        # twice (hour-level counterpart of Werk #14830). Keep the tick but suppress the
        # repeated label so every rendered label stays unambiguous.
        if label is not None and label in emitted_labels:
            label = None
        if label is not None:
            half_width = measure_label(label) / 2
            center = position_to_x(position)
            overlaps_previous = center - half_width < previous_label_right_edge + _MIN_LABEL_GAP_PX
            overflows_plot = center - half_width < 0 or center + half_width > plot_width
            if overlaps_previous or overflows_plot:
                label = None
            else:
                emitted_labels.add(label)
                previous_label_right_edge = center + half_width
        ticks.append(TimeAxisTick(position=position, text=label, line_width=line_width))
    return ticks
