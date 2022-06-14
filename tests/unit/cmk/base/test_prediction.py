#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import math
import time
from pprint import pprint

import pytest

from tests.testlib import on_time

from cmk.base import prediction


@pytest.mark.parametrize(
    "group_by, timestamp, result",
    [
        (prediction._group_by_wday, 1543402800, ("wednesday", 43200)),
        (prediction._group_by_day, 1543402800, ("everyday", 43200)),
        (prediction._group_by_day_of_month, 1543402800, ("28", 43200)),
        (prediction._group_by_everyhour, 1543402820, ("everyhour", 20)),
    ],
)
def test_group_by(group_by, timestamp, result) -> None:
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
            prediction._PREDICTION_PERIODS["hour"],
            "everyday",
            [(1531008000, 1531094400), (1530921600, 1531008000), (1530835200, 1530921600)],
        ),
        # Same but 2hrs back on timestamp
        (
            "2018-07-08 2:00",
            "Europe/Berlin",
            86400 * 2,
            prediction._PREDICTION_PERIODS["hour"],
            "everyday",
            [(1531000800, 1531087200), (1530914400, 1531000800)],
        ),
        # North Winter time shift
        (
            "2018-07-08 2:00",
            "America/New_York",
            86400 * 2,
            prediction._PREDICTION_PERIODS["hour"],
            "everyday",
            [(1530936000, 1531022400), (1530849600, 1530936000)],
        ),
        # days after each other, start is previous day end
        (
            "2018-10-28 2:00",
            "UTC",
            86400 * 2,
            prediction._PREDICTION_PERIODS["hour"],
            "everyday",
            [(1540684800, 1540771200), (1540598400, 1540684800)],
        ),
        # After change: missing 1hr between current and previous day, current has 1hr to UTC, previous 2hrs
        (
            "2018-10-28 2:00",
            "Europe/Berlin",
            86400 * 2,
            prediction._PREDICTION_PERIODS["hour"],
            "everyday",
            [(1540681200, 1540767600), (1540591200, 1540677600)],
        ),
        # Before change: Sequential days, 2hrs to UTC, missing end of day hour
        (
            "2018-10-28 0:00",
            "Europe/Berlin",
            86400 * 2,
            prediction._PREDICTION_PERIODS["hour"],
            "everyday",
            [(1540677600, 1540764000), (1540591200, 1540677600)],
        ),
        # After change: missing 1hr between current and previous day
        (
            "2018-11-04 7:00",
            "America/New_York",
            86400 * 2,
            prediction._PREDICTION_PERIODS["hour"],
            "everyday",
            [(1541307600, 1541394000), (1541217600, 1541304000)],
        ),
        # Before change: Sequential days, missing end of day hour
        (
            "2018-11-04 5:00",
            "America/New_York",
            86400 * 2,
            prediction._PREDICTION_PERIODS["hour"],
            "everyday",
            [(1541304000, 1541390400), (1541217600, 1541304000)],
        ),
        # North into summer, a week distance is ~6.95 days not 7, jumping an hour
        (
            "2019-04-02 10:00",
            "Europe/Berlin",
            86400 * 12,
            prediction._PREDICTION_PERIODS["wday"],
            "tuesday",
            [(1554156000, 1554242400), (1553554800, 1553641200)],
        ),
    ],
)
def test_time_slices(utcdate, timezone, horizon, period_info, timegroup, result) -> None:
    """Find period slices for predictive levels

    More than a test is an exemplification of our convention
    Predictive levels work on local times, because they are linked to human routines.
    """
    with on_time(utcdate, timezone):
        timestamp = time.time()
        print(timestamp)

        slices = prediction._time_slices(int(timestamp), horizon, period_info, timegroup)
        pprint([("ontz", x, time.ctime(x), time.ctime(y)) for x, y in slices])
    pprint([("sys", x, time.ctime(x), time.ctime(y)) for x, y in slices])
    assert slices == result


@pytest.mark.parametrize(
    "slices, result",
    [
        ([list(range(6))], [[i] * 4 for i in range(6)]),
        ([[1, 5, None, 6]], [[i] * 4 for i in [1, 5, None, 6]]),
        (
            [
                [1, 5, None, 6],
                [2, None, 2, 4],
            ],
            [
                pytest.approx([1.5, 1, 2, math.sqrt(2) / 2]),  # fixed: true-division
                [5.0, 5, 5, 5.0],
                [2.0, 2, 2, 2.0],
                pytest.approx([5.0, 4, 6, math.sqrt(2)]),
            ],
        ),
        (
            [
                [1, 5, 3, 6, 8, None],
                [2, 2, 2, 4, 3, 5],
                [3, 3, None, None, 2, 2],
            ],
            [
                pytest.approx([2.0, 1, 3, 1.0]),
                pytest.approx([10.0 / 3.0, 2, 5, 1.527525]),
                pytest.approx([2.5, 2, 3, math.sqrt(2) / 2]),  # fixed: true-division
                pytest.approx([5.0, 4, 6, math.sqrt(2)]),
                pytest.approx([4.333333, 2, 8, 3.214550]),
                pytest.approx([3.5, 2, 5, 2.121320]),
            ],
        ),
        (
            [
                [1, 5, 3, 2, 6, 8, None],
                [None] * 7,
                [5, 5, 5, 5, 2, 2, 2],
            ],
            [
                pytest.approx([3.0, 1, 5, 2.828427]),
                pytest.approx([5.0, 5, 5, 0.0]),
                pytest.approx([4.0, 3, 5, 1.414213]),
                pytest.approx([3.5, 2, 5, 2.121320]),
                pytest.approx([4.0, 2, 6, 2.828427]),
                pytest.approx([5.0, 2, 8, 4.242640]),
                pytest.approx([2.0, 2, 2, 2.0]),
            ],
        ),
    ],
)
def test_data_stats(slices, result) -> None:
    assert prediction._data_stats(slices) == result
