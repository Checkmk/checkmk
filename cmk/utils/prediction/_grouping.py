#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Final, Literal, NamedTuple, NewType, Self

Timegroup = NewType("Timegroup", str)

PeriodName = Literal["wday", "day", "hour", "minute"]

_WEEKDAYS = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]


class PeriodInfo(NamedTuple):
    slice: int
    groupby: Callable[[int], tuple[Timegroup, int]]


def is_dst(timestamp: float) -> bool:
    """Check wether a certain time stamp lies with in daylight saving time (DST)"""
    return bool(time.localtime(timestamp).tm_isdst)


def timezone_at(timestamp: float) -> int:
    """Returns the timezone *including* DST shift at a certain point of time"""
    return time.altzone if is_dst(timestamp) else time.timezone


def _second_of_hour(t: time.struct_time) -> int:
    return t.tm_min * 60 + t.tm_sec


def _second_of_day(t: time.struct_time) -> int:
    return t.tm_hour * 3600 + t.tm_min * 60 + t.tm_sec


def _group_by_wday(timestamp: int) -> tuple[Timegroup, int]:
    st = time.localtime(timestamp)
    return Timegroup(_WEEKDAYS[st.tm_wday]), _second_of_day(st)


def _group_by_day(timestamp: int) -> tuple[Timegroup, int]:
    st = time.localtime(timestamp)
    return Timegroup("everyday"), _second_of_day(st)


def _group_by_day_of_month(timestamp: int) -> tuple[Timegroup, int]:
    st = time.localtime(timestamp)
    return Timegroup(str(st.tm_mday)), _second_of_day(st)


def _group_by_everyhour(timestamp: int) -> tuple[Timegroup, int]:
    st = time.localtime(timestamp)
    return Timegroup("everyhour"), _second_of_hour(st)


PREDICTION_PERIODS: Final[Mapping[PeriodName, PeriodInfo]] = {
    "wday": PeriodInfo(
        slice=86400,  # 7 slices
        groupby=_group_by_wday,
    ),
    "day": PeriodInfo(
        slice=86400,  # 31 slices
        groupby=_group_by_day_of_month,
    ),
    "hour": PeriodInfo(
        slice=86400,  # 1 slice
        groupby=_group_by_day,
    ),
    "minute": PeriodInfo(
        slice=3600,  # 1 slice
        groupby=_group_by_everyhour,
    ),
}


def time_slices(
    timestamp: int,
    horizon_seconds: int,
    period_name: PeriodName,
) -> Sequence[tuple[int, int]]:
    "Collect all slices back into the past until time horizon is reached"
    abs_begin = timestamp - horizon_seconds

    period_info = PREDICTION_PERIODS[period_name]
    timegroup, _rel_time = period_info.groupby(timestamp)

    # Note: due to the f**king DST, we can have several shifts between DST
    # and non-DST during a computation. Treatment is unfair on those longer
    # or shorter days. All days have 24hrs. DST swaps within slices are
    # being ignored, we work with slice shifts. The DST flag is checked
    # against the query timestamp. In general that means test is done at
    # the beginning of the day(because predictive levels refresh at
    # midnight) and most likely before DST swap is applied.

    # Have fun understanding the tests for this function.
    return [
        slice_.interval
        for begin in range(timestamp, abs_begin, -period_info.slice)
        if (slice_ := Slice.from_timestamp(begin, period_info)).group == timegroup
    ]


@dataclass
class Slice:
    group: Timegroup
    """Name of the group, like 'monday' or '12'"""
    interval: tuple[int, int]
    """Absolute epoch times of the first second of the slice
    and the first second *not* in the slice."""

    @classmethod
    def from_timestamp(cls, timestamp: int, period_info: PeriodInfo) -> Self:
        timegroup, rel_time = period_info.groupby(timestamp)
        from_time = timestamp - rel_time
        until_time = from_time + period_info.slice
        return cls(group=timegroup, interval=(from_time, until_time))
