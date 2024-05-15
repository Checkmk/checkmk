#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.gui.time_series import rrd_timestamps, TimeSeries, TimeSeriesValues, TimeWindow


@pytest.mark.parametrize(
    "twindow, result", [((0, 0, 0), []), ((100, 200, 25), [125, 150, 175, 200])]
)
def test_rrdtimestamps(twindow: TimeWindow, result: list[int]) -> None:
    assert rrd_timestamps(twindow) == result


@pytest.mark.parametrize(
    "rrddata, twindow, upsampled",
    [
        # The following test resamples the identity function consisting of the points
        # (0|0), (10|10), (20|20), (30|30) and (40|40).
        # Resampling at other times will always repeat the last measured value
        # until the next sample is reached/passed, resulting in
        # (4|0), (8|0), (12|10), (16|10), (20|20) ...
        # When dealing with missing data, this is commonly refered to as "forward filling".
        ([0, 50, 10, 0, 10, 20, 30, 40], (4, 47, 4), [0, 0, 10, 10, 20, 20, 20, 30, 30, 40, 40]),
        # Here are some more tests that I don't know the significance of:
        ([10, 20, 10, 20], (10, 20, 10), [20]),
        ([10, 20, 10, 20], (10, 20, 5), [20, 20]),
        (
            [0, 120, 40, 25, 65, 105],
            (0, 100, 10),
            [25, 25, 25, 25, 65, 65, 65, 65, 105, 105],
        ),
        (
            [0, 120, 40, 25, None, 105],
            (0, 100, 10),
            [25, 25, 25, 25, None, None, None, None, 105, 105],
        ),
        ([0, 120, 40, 25, 65, 105], (30, 110, 10), [25, 65, 65, 65, 65, 105, 105, 105]),
    ],
)
def test_time_series_upsampling(
    rrddata: TimeSeriesValues,
    twindow: TimeWindow,
    upsampled: TimeSeriesValues,
) -> None:
    ts = TimeSeries(rrddata)
    assert ts.forward_fill_resample(twindow) == upsampled


@pytest.mark.parametrize(
    "rrddata, twindow, cf, downsampled",
    [
        ([10, 25, 5, 15, 20, 25], (10, 30, 10), "average", [17.5, 25]),
        ([10, 25, 5, 15, 20, 25], (10, 30, 10), "max", [20, 25]),
        ([10, 45, 5, 15, 20, 25, 30, 35, 40, 45], (10, 40, 10), "max", [20, 30, 40]),
        ([10, 45, 5, 15, 20, 25, 30, 35, 40, 45], (10, 60, 10), "max", [20, 30, 40, 45, None]),
        (
            [10, 45, 5, 15, None, 25, None, None, None, 45],
            (10, 60, 10),
            "max",
            [15, 25, None, 45, None],
        ),
        ([10, 45, 5, 15, 20, 25, 30, 35, 40, 45], (0, 60, 10), "max", [None, 20, 30, 40, 45, None]),
        ([10, 45, 5, 15, 20, 25, 30, 35, 40, 45], (10, 40, 10), "average", [17.5, 27.5, 37.5]),
        ([10, 45, 5, 15, 20, 25, 30, None, 40, 45], (10, 40, 10), "average", [17.5, 27.5, 40.0]),
    ],
)
def test_time_series_downsampling(
    rrddata: TimeSeriesValues,
    twindow: TimeWindow,
    cf: str,
    downsampled: TimeSeriesValues,
) -> None:
    ts = TimeSeries(rrddata)
    assert ts.downsample(twindow, cf) == downsampled


class TestTimeseries:
    def test_conversion(self) -> None:
        assert TimeSeries(
            [1, 2, 3, 4, None, 5],
            conversion=lambda v: 2 * v - 3,
        ).values == [
            2 * 4 - 3,
            None,
            2 * 5 - 3,
        ]

    def test_conversion_noop_default(self) -> None:
        assert TimeSeries([1, 2, 3, 4, None, 5]).values == [4, None, 5]

    def test_count(self) -> None:
        assert (
            TimeSeries(
                [1, 2, None, 4, None, 5],
                time_window=(7, 8, 9),
            ).count(None)
            == 2
        )
