#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import math
import time
from collections.abc import Callable, Sequence
from pprint import pprint

import pytest

from tests.testlib import on_time

from cmk.utils.prediction import _grouping, _prediction, _time_series, DataStat


@pytest.mark.parametrize(
    "group_by, timestamp, result",
    [
        (_grouping._group_by_wday, 1543402800, ("wednesday", 43200)),
        (_grouping._group_by_day, 1543402800, ("everyday", 43200)),
        (_grouping._group_by_day_of_month, 1543402800, ("28", 43200)),
        (_grouping._group_by_everyhour, 1543402820, ("everyhour", 20)),
    ],
)
def test_group_by(
    group_by: Callable[
        [_time_series.Timestamp], tuple[_grouping.Timegroup, _time_series.Timestamp]
    ],
    timestamp: _time_series.Timestamp,
    result: tuple[_grouping.Timegroup, _time_series.Timestamp],
) -> None:
    with on_time(timestamp, "CET"):
        assert group_by(timestamp) == result


@pytest.mark.parametrize(
    "utcdate, timezone, horizon, period_info, timegroup, result",
    [
        # North Summertime
        # days after each other, start is previous day end
        (
            "2018-07-08 2:00",
            "UTC",
            86400 * 3,
            _grouping.PREDICTION_PERIODS["hour"],
            "everyday",
            [(1531008000, 1531094400), (1530921600, 1531008000), (1530835200, 1530921600)],
        ),
        # Same but 2hrs back on timestamp
        (
            "2018-07-08 2:00",
            "Europe/Berlin",
            86400 * 2,
            _grouping.PREDICTION_PERIODS["hour"],
            "everyday",
            [(1531000800, 1531087200), (1530914400, 1531000800)],
        ),
        # North Winter time shift
        (
            "2018-07-08 2:00",
            "America/New_York",
            86400 * 2,
            _grouping.PREDICTION_PERIODS["hour"],
            "everyday",
            [(1530936000, 1531022400), (1530849600, 1530936000)],
        ),
        # days after each other, start is previous day end
        (
            "2018-10-28 2:00",
            "UTC",
            86400 * 2,
            _grouping.PREDICTION_PERIODS["hour"],
            "everyday",
            [(1540684800, 1540771200), (1540598400, 1540684800)],
        ),
        # After change: missing 1hr between current and previous day, current has 1hr to UTC, previous 2hrs
        (
            "2018-10-28 2:00",
            "Europe/Berlin",
            86400 * 2,
            _grouping.PREDICTION_PERIODS["hour"],
            "everyday",
            [(1540681200, 1540767600), (1540591200, 1540677600)],
        ),
        # Before change: Sequential days, 2hrs to UTC, missing end of day hour
        (
            "2018-10-28 0:00",
            "Europe/Berlin",
            86400 * 2,
            _grouping.PREDICTION_PERIODS["hour"],
            "everyday",
            [(1540677600, 1540764000), (1540591200, 1540677600)],
        ),
        # After change: missing 1hr between current and previous day
        (
            "2018-11-04 7:00",
            "America/New_York",
            86400 * 2,
            _grouping.PREDICTION_PERIODS["hour"],
            "everyday",
            [(1541307600, 1541394000), (1541217600, 1541304000)],
        ),
        # Before change: Sequential days, missing end of day hour
        (
            "2018-11-04 5:00",
            "America/New_York",
            86400 * 2,
            _grouping.PREDICTION_PERIODS["hour"],
            "everyday",
            [(1541304000, 1541390400), (1541217600, 1541304000)],
        ),
        # North into summer, a week distance is ~6.95 days not 7, jumping an hour
        (
            "2019-04-02 10:00",
            "Europe/Berlin",
            86400 * 12,
            _grouping.PREDICTION_PERIODS["wday"],
            "tuesday",
            [(1554156000, 1554242400), (1553554800, 1553641200)],
        ),
    ],
)
def test_time_slices(
    utcdate: str,
    timezone: str,
    horizon: int,
    period_info: _grouping.PeriodInfo,
    timegroup: _grouping.Timegroup,
    result: Sequence[tuple[_time_series.Timestamp, _time_series.Timestamp]],
) -> None:
    """Find period slices for predictive levels

    More than a test is an exemplification of our convention
    Predictive levels work on local times, because they are linked to human routines.
    """
    with on_time(utcdate, timezone):
        timestamp = time.time()
        print(timestamp)

        slices = _grouping.time_slices(int(timestamp), horizon, period_info, timegroup)
        pprint([("ontz", x, time.ctime(x), time.ctime(y)) for x, y in slices])
    pprint([("sys", x, time.ctime(x), time.ctime(y)) for x, y in slices])
    assert slices == result


def approx(value_in: float) -> float:
    # ApproxBase != float :-(
    return pytest.approx(value_in)  # type: ignore[return-value]


@pytest.mark.parametrize(
    "slices, result",
    [
        ([list(range(6))], [DataStat(i, i, i, None) for i in range(6)]),
        (
            [[1, 5, None, 6]],
            [
                DataStat(1, 1, 1, None),
                DataStat(5, 5, 5, None),
                None,
                DataStat(6, 6, 6, None),
            ],
        ),
        (
            [
                [1, 5, None, 6],
                [2, None, 2, 4],
            ],
            [
                DataStat(1.5, 1, 2, approx(math.sqrt(2) / 2)),  # fixed: true-division
                DataStat(5.0, 5, 5, None),
                DataStat(2.0, 2, 2, None),
                DataStat(5.0, 4, 6, approx(math.sqrt(2))),
            ],
        ),
        (
            [
                [1, 5, 3, 6, 8, None],
                [2, 2, 2, 4, 3, 5],
                [3, 3, None, None, 2, 2],
            ],
            [
                DataStat(approx(2.0), 1, 3, approx(1.0)),
                DataStat(approx(3.333333), 2, 5, approx(1.527525)),
                DataStat(2.5, 2, 3, approx(math.sqrt(2) / 2)),  # fixed: true-division
                DataStat(approx(5.0), 4, 6, approx(math.sqrt(2))),
                DataStat(approx(4.333333), 2, 8, approx(3.214550)),
                DataStat(approx(3.5), 2, 5, approx(2.121320)),
            ],
        ),
        (
            [
                [1, 5, 3, 2, 6, 8, None],
                [None] * 7,
                [5, 5, 5, 5, 2, 2, 2],
            ],
            [
                DataStat(3.0, 1, 5, approx(2.828427)),
                DataStat(5.0, 5, 5, approx(0.0)),
                DataStat(4.0, 3, 5, approx(1.414213)),
                DataStat(3.5, 2, 5, approx(2.121320)),
                DataStat(4.0, 2, 6, approx(2.828427)),
                DataStat(5.0, 2, 8, approx(4.242640)),
                DataStat(2.0, 2, 2, None),
            ],
        ),
    ],
)
def test_data_stats(
    slices: list[Sequence[float | None]], result: Sequence[DataStat | None]
) -> None:
    assert _prediction._data_stats(slices) == result
