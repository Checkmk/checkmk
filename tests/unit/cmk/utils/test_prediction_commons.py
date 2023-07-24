#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.prediction import _prediction


@pytest.mark.parametrize(
    "filter_condition, values, join, result",
    [
        ("Filter: metrics =", [], "And", ""),
        ("Filter: description =", ["CPU load"], "And", "Filter: description = CPU load\n"),
        (
            "Filter: host_name =",
            ["heute", "beta"],
            "Or",
            "Filter: host_name = heute\nFilter: host_name = beta\nOr: 2\n",
        ),
    ],
)
def test_lq_logic(filter_condition: str, values: list[str], join: str, result: str) -> None:
    assert _prediction.lq_logic(filter_condition, values, join) == result


@pytest.mark.parametrize(
    "args, result",
    [
        (
            (["heute"], ["util", "user"], "CPU"),
            """GET services
Columns: util user
Filter: host_name = heute
Filter: service_description = CPU\n""",
        ),
        (
            (["gestern"], ["check_command"], None),
            """GET hosts
Columns: check_command
Filter: host_name = gestern\n""",
        ),
        (
            (["fire", "water"], ["description", "metrics"], "cpu"),
            """GET services
Columns: description metrics
Filter: host_name = fire
Filter: host_name = water
Or: 2
Filter: service_description = cpu\n""",
        ),
        (
            ([], ["test"], "invent"),
            """GET services
Columns: test
Filter: service_description = invent\n""",
        ),
    ],
)
def test_livestatus_lql(args: tuple[list[str], list[str], str], result: str) -> None:
    assert _prediction.livestatus_lql(*args) == result


@pytest.mark.parametrize(
    "twindow, result", [((0, 0, 0), []), ((100, 200, 25), [125, 150, 175, 200])]
)
def test_rrdtimestamps(twindow: _prediction.TimeWindow, result: list[int]) -> None:
    assert _prediction.rrd_timestamps(twindow) == result


@pytest.mark.parametrize(
    "rrddata, twindow, shift, upsampled",
    [
        ([10, 20, 10, 20], (10, 20, 10), 0, [20]),
        ([10, 20, 10, 20], (10, 20, 5), 0, [20, 20]),
        ([10, 20, 10, 20], (20, 30, 5), 10, [20, 20]),
        (
            [0, 120, 40, 25, 65, 105],
            (300, 400, 10),
            300,
            [25, 25, 25, 25, 65, 65, 65, 65, 105, 105],
        ),
        (
            [0, 120, 40, 25, None, 105],
            (300, 400, 10),
            300,
            [25, 25, 25, 25, None, None, None, None, 105, 105],
        ),
        ([0, 120, 40, 25, 65, 105], (330, 410, 10), 300, [25, 65, 65, 65, 65, 105, 105, 105]),
    ],
)
def test_time_series_upsampling(
    rrddata: _prediction.TimeSeriesValues,
    twindow: _prediction.TimeWindow,
    shift: int,
    upsampled: _prediction.TimeSeriesValues,
) -> None:
    ts = _prediction.TimeSeries(rrddata)
    assert ts.bfill_upsample(twindow, shift) == upsampled


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
    rrddata: _prediction.TimeSeriesValues,
    twindow: _prediction.TimeWindow,
    cf: _prediction.ConsolidationFunctionName,
    downsampled: _prediction.TimeSeriesValues,
) -> None:
    ts = _prediction.TimeSeries(rrddata)
    assert ts.downsample(twindow, cf) == downsampled


class TestTimeseries:
    def test_conversion(self) -> None:
        assert _prediction.TimeSeries(
            [1, 2, 3, 4, None, 5],
            conversion=lambda v: 2 * v - 3,
        ).values == [
            2 * 4 - 3,
            None,
            2 * 5 - 3,
        ]

    def test_conversion_noop_default(self) -> None:
        assert _prediction.TimeSeries([1, 2, 3, 4, None, 5]).values == [4, None, 5]

    def test_count(self) -> None:
        assert (
            _prediction.TimeSeries(
                [1, 2, None, 4, None, 5],
                time_window=(7, 8, 9),
            ).count(None)
            == 2
        )
