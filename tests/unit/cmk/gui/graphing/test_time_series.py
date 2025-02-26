#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.gui.graphing._time_series import rrd_timestamps, TimeSeries, TimeSeriesValues, TimeWindow


@pytest.mark.parametrize(
    "start, end, step, result",
    [
        (0, 0, 0, []),
        (100, 200, 25, [125, 150, 175, 200]),
    ],
)
def test_rrdtimestamps(start: int, end: int, step: int, result: list[int]) -> None:
    assert rrd_timestamps(start=start, end=end, step=step) == result


@pytest.mark.parametrize(
    "time_series, start, end, step, upsampled",
    [
        # The following test resamples the identity function consisting of the points
        # (0|0), (10|10), (20|20), (30|30) and (40|40).
        # Resampling at other times will always repeat the last measured value
        # until the next sample is reached/passed, resulting in
        # (4|0), (8|0), (12|10), (16|10), (20|20) ...
        # When dealing with missing data, this is commonly refered to as "forward filling".
        (
            TimeSeries(start=0, end=50, step=10, values=[0, 10, 20, 30, 40]),
            4,
            47,
            4,
            [0, 0, 10, 10, 20, 20, 20, 30, 30, 40, 40],
        ),
        # Here are some more tests that I don't know the significance of:
        (
            TimeSeries(start=10, end=20, step=10, values=[20]),
            10,
            20,
            10,
            [20],
        ),
        (
            TimeSeries(start=10, end=20, step=10, values=[20]),
            10,
            20,
            5,
            [20, 20],
        ),
        (
            TimeSeries(start=0, end=120, step=40, values=[25, 65, 105]),
            0,
            100,
            10,
            [25, 25, 25, 25, 65, 65, 65, 65, 105, 105],
        ),
        (
            TimeSeries(start=0, end=120, step=40, values=[25, None, 105]),
            0,
            100,
            10,
            [25, 25, 25, 25, None, None, None, None, 105, 105],
        ),
        (
            TimeSeries(start=0, end=120, step=40, values=[25, 65, 105]),
            30,
            110,
            10,
            [25, 65, 65, 65, 65, 105, 105, 105],
        ),
    ],
)
def test_time_series_upsampling(
    time_series: TimeSeries,
    start: int,
    end: int,
    step: int,
    upsampled: TimeSeriesValues,
) -> None:
    assert time_series.forward_fill_resample(start=start, end=end, step=step) == upsampled


@pytest.mark.parametrize(
    "time_series, twindow, cf, downsampled",
    [
        (
            TimeSeries(start=10, end=25, step=5, values=[15, 20, 25]),
            (10, 30, 10),
            "average",
            [17.5, 25],
        ),
        (
            TimeSeries(start=10, end=25, step=5, values=[15, 20, 25]),
            (10, 30, 10),
            "max",
            [20, 25],
        ),
        (
            TimeSeries(start=10, end=45, step=5, values=[15, 20, 25, 30, 35, 40, 45]),
            (10, 40, 10),
            "max",
            [20, 30, 40],
        ),
        (
            TimeSeries(start=10, end=45, step=5, values=[15, 20, 25, 30, 35, 40, 45]),
            (10, 60, 10),
            "max",
            [20, 30, 40, 45, None],
        ),
        (
            TimeSeries(start=10, end=45, step=5, values=[15, None, 25, None, None, None, 45]),
            (10, 60, 10),
            "max",
            [15, 25, None, 45, None],
        ),
        (
            TimeSeries(start=10, end=45, step=5, values=[15, 20, 25, 30, 35, 40, 45]),
            (0, 60, 10),
            "max",
            [None, 20, 30, 40, 45, None],
        ),
        (
            TimeSeries(start=10, end=45, step=5, values=[15, 20, 25, 30, 35, 40, 45]),
            (10, 40, 10),
            "average",
            [17.5, 27.5, 37.5],
        ),
        (
            TimeSeries(start=10, end=45, step=5, values=[15, 20, 25, 30, None, 40, 45]),
            (10, 40, 10),
            "average",
            [17.5, 27.5, 40.0],
        ),
    ],
)
def test_time_series_downsampling(
    time_series: TimeSeries,
    twindow: TimeWindow,
    cf: str,
    downsampled: TimeSeriesValues,
) -> None:
    assert time_series.downsample(twindow, cf) == downsampled


class TestTimeseries:
    def test_conversion(self) -> None:
        assert TimeSeries(
            start=1,
            end=2,
            step=3,
            values=[4, None, 5],
            conversion=lambda v: 2 * v - 3,
        ).values == [
            2 * 4 - 3,
            None,
            2 * 5 - 3,
        ]

    def test_conversion_noop_default(self) -> None:
        assert TimeSeries(
            start=1,
            end=2,
            step=3,
            values=[4, None, 5],
        ).values == [4, None, 5]

    def test_count(self) -> None:
        assert (
            TimeSeries(
                start=7,
                end=8,
                step=9,
                values=[1, 2, None, 4, None, 5],
            ).count(None)
            == 2
        )
