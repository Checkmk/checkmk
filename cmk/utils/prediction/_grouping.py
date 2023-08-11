#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Callable, Mapping, Sequence
from typing import Final, Literal, NamedTuple, NewType

from cmk.utils import dateutils

Seconds = int
Timestamp = int

Timegroup = NewType("Timegroup", str)

PeriodName = Literal["wday", "day", "hour", "minute"]


class PeriodInfo(NamedTuple):
    slice: int
    groupby: Callable[[Timestamp], tuple[Timegroup, Timestamp]]
    valid: int


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


def _group_by_wday(t: Timestamp) -> tuple[Timegroup, Timestamp]:
    st = time.localtime(t)
    return Timegroup(dateutils.weekday_ids()[st.tm_wday]), _second_of_day(st)


def _group_by_day(t: Timestamp) -> tuple[Timegroup, Timestamp]:
    st = time.localtime(t)
    return Timegroup("everyday"), _second_of_day(st)


def _group_by_day_of_month(t: Timestamp) -> tuple[Timegroup, Timestamp]:
    st = time.localtime(t)
    return Timegroup(str(st.tm_mday)), _second_of_day(st)


def _group_by_everyhour(t: Timestamp) -> tuple[Timegroup, Timestamp]:
    st = time.localtime(t)
    return Timegroup("everyhour"), _second_of_hour(st)


PREDICTION_PERIODS: Final[Mapping[PeriodName, PeriodInfo]] = {
    "wday": PeriodInfo(
        slice=86400,  # 7 slices
        groupby=_group_by_wday,
        valid=7,
    ),
    "day": PeriodInfo(
        slice=86400,  # 31 slices
        groupby=_group_by_day_of_month,
        valid=28,
    ),
    "hour": PeriodInfo(
        slice=86400,  # 1 slice
        groupby=_group_by_day,
        valid=1,
    ),
    "minute": PeriodInfo(
        slice=3600,  # 1 slice
        groupby=_group_by_everyhour,
        valid=24,
    ),
}


def time_slices(
    timestamp: Timestamp,
    horizon: Seconds,
    period_info: PeriodInfo,
    timegroup: Timegroup,
) -> Sequence[tuple[int, int]]:
    "Collect all slices back into the past until time horizon is reached"
    timestamp = int(timestamp)
    abs_begin = timestamp - horizon
    slices = []

    # Note: due to the f**king DST, we can have several shifts between DST
    # and non-DST during a computation. Treatment is unfair on those longer
    # or shorter days. All days have 24hrs. DST swaps within slices are
    # being ignored, we work with slice shifts. The DST flag is checked
    # against the query timestamp. In general that means test is done at
    # the beginning of the day(because predictive levels refresh at
    # midnight) and most likely before DST swap is applied.

    # Have fun understanding the tests for this function.
    for begin in range(timestamp, abs_begin, -period_info.slice):
        tg, start, end = get_timegroup_relative_time(begin, period_info)[:3]
        if tg == timegroup:
            slices.append((start, end))
    return slices


def get_timegroup_relative_time(
    t: Timestamp,
    period_info: PeriodInfo,
) -> tuple[Timegroup, Timestamp, Timestamp, Seconds]:
    """
    Return:
    timegroup: name of the group, like 'monday' or '12'
    from_time: absolute epoch time of the first second of the
    current slice.
    until_time: absolute epoch time of the first second *not* in the slice
    rel_time: seconds offset of now in the current slice
    """
    # Convert to local timezone
    timegroup, rel_time = period_info.groupby(t)
    from_time = t - rel_time
    until_time = from_time + period_info.slice
    return timegroup, from_time, until_time, rel_time
