#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.utils.prediction as prediction


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
def test_lq_logic(filter_condition, values, join, result):
    assert prediction.lq_logic(filter_condition, values, join) == result


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
def test_livestatus_lql(args, result):
    assert prediction.livestatus_lql(*args) == result


@pytest.mark.parametrize(
    "twindow, result", [((0, 0, 0), []), ((100, 200, 25), [125, 150, 175, 200])]
)
def test_rrdtimestamps(twindow, result):
    assert prediction.rrd_timestamps(twindow) == result


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
def test_time_series_upsampling(rrddata, twindow, shift, upsampled):
    ts = prediction.TimeSeries(rrddata)
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
def test_time_series_downsampling(rrddata, twindow, cf, downsampled):
    ts = prediction.TimeSeries(rrddata)
    assert ts.downsample(twindow, cf) == downsampled


def test__get_reference_deviation_absolute():
    factor = 3.1415
    assert (
        prediction._get_reference_deviation(
            levels_type="absolute",
            reference_value=42.0,
            stdev=None,
            levels_factor=factor,
        )
        == factor
    )


def test__get_reference_deviation_relative():
    reference_value = 42.0
    assert (
        prediction._get_reference_deviation(
            levels_type="relative",
            reference_value=reference_value,
            stdev=None,
            levels_factor=3.1415,
        )
        == reference_value / 100.0
    )


def test__get_reference_deviation_stdev_good():
    stdev = 23.0
    assert (
        prediction._get_reference_deviation(
            levels_type="stdev",
            reference_value=42.0,
            stdev=stdev,
            levels_factor=3.1415,
        )
        == stdev
    )


def test__get_reference_deviation_stdev_bad():
    with pytest.raises(TypeError):
        _ = prediction._get_reference_deviation(
            levels_type="stdev",
            reference_value=42.0,
            stdev=None,
            levels_factor=3.1415,
        )


@pytest.mark.parametrize(
    "reference_value, reference_deviation, params, levels_factor, result",
    [
        (
            5,
            2,
            {"levels_lower": ("absolute", (2, 4))},
            1,
            (None, None, 3, 1),
        ),
        (
            15,
            2,
            {
                "levels_upper": ("stddev", (2, 4)),
                "levels_lower": ("stddev", (3, 5)),
            },
            1,
            (19, 23, 9, 5),
        ),
        (
            2,
            3,
            {
                "levels_upper": ("relative", (20, 40)),
                "levels_upper_min": (2, 4),
            },
            1,
            (2.4, 4, None, None),
        ),
        (
            None,
            object(),  # should never be used
            {},
            1,
            (None, None, None, None),
        ),
    ],
)
def test_estimate_levels(reference_value, reference_deviation, params, levels_factor, result):
    assert (
        prediction.estimate_levels(
            reference_value=reference_value,
            stdev=reference_deviation,
            levels_lower=params.get("levels_lower"),
            levels_upper=params.get("levels_upper"),
            levels_upper_lower_bound=params.get("levels_upper_min"),
            levels_factor=levels_factor,
        )
        == result
    )
