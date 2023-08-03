#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

import cmk.utils.prediction as prediction


@pytest.mark.parametrize("filter_condition, values, join, result", [
    (u"Filter: metrics =", [], u"And", u""),
    (u"Filter: description =", [u"CPU load"], u"And", u"Filter: description = CPU load\n"),
    (u"Filter: host_name =", [u'heute', u'beta'], u"Or",
     u"Filter: host_name = heute\nFilter: host_name = beta\nOr: 2\n"),
])
def test_lq_logic(filter_condition, values, join, result):
    assert prediction.lq_logic(filter_condition, values, join) == result


@pytest.mark.parametrize("args, result",
                         [((['heute'], ['util', 'user'], 'CPU'), """GET services
Columns: util user
Filter: host_name = heute
Filter: service_description = CPU\n"""),
                          ((['gestern'], ['check_command'], None), """GET hosts
Columns: check_command
Filter: host_name = gestern\n"""),
                          ((['fire', 'water'], ['description', 'metrics'], 'cpu'), """GET services
Columns: description metrics
Filter: host_name = fire
Filter: host_name = water
Or: 2
Filter: service_description = cpu\n"""),
                          (([], ['test'], 'invent'), """GET services
Columns: test
Filter: service_description = invent\n""")])
def test_livestatus_lql(args, result):
    assert prediction.livestatus_lql(*args) == result


@pytest.mark.parametrize("twindow, result", [((0, 0, 0), []),
                                             ((100, 200, 25), [125, 150, 175, 200])])
def test_rrdtimestamps(twindow, result):
    assert prediction.rrd_timestamps(twindow) == result


@pytest.mark.parametrize("rrddata, twindow, shift, upsampled", [
    ([10, 20, 10, 20], (10, 20, 10), 0, [20]),
    ([10, 20, 10, 20], (10, 20, 5), 0, [20, 20]),
    ([10, 20, 10, 20], (20, 30, 5), 10, [20, 20]),
    ([0, 120, 40, 25, 65, 105], (300, 400, 10), 300, [25, 25, 25, 25, 65, 65, 65, 65, 105, 105]),
    ([0, 120, 40, 25, None, 105],
     (300, 400, 10), 300, [25, 25, 25, 25, None, None, None, None, 105, 105]),
    ([0, 120, 40, 25, 65, 105], (330, 410, 10), 300, [25, 65, 65, 65, 65, 105, 105, 105]),
])
def test_time_series_upsampling(rrddata, twindow, shift, upsampled):
    ts = prediction.TimeSeries(rrddata)
    assert ts.bfill_upsample(twindow, shift) == upsampled


@pytest.mark.parametrize("rrddata, twindow, cf, downsampled", [
    ([10, 25, 5, 15, 20, 25], (10, 30, 10), "average", [17.5, 25]),
    ([10, 25, 5, 15, 20, 25], (10, 30, 10), "max", [20, 25]),
    ([10, 45, 5, 15, 20, 25, 30, 35, 40, 45], (10, 40, 10), "max", [20, 30, 40]),
    ([10, 45, 5, 15, 20, 25, 30, 35, 40, 45], (10, 60, 10), "max", [20, 30, 40, 45, None]),
    ([10, 45, 5, 15, None, 25, None, None, None, 45],
     (10, 60, 10), "max", [15, 25, None, 45, None]),
    ([10, 45, 5, 15, 20, 25, 30, 35, 40, 45], (0, 60, 10), "max", [None, 20, 30, 40, 45, None]),
    ([10, 45, 5, 15, 20, 25, 30, 35, 40, 45], (10, 40, 10), "average", [17.5, 27.5, 37.5]),
    ([10, 45, 5, 15, 20, 25, 30, None, 40, 45], (10, 40, 10), "average", [17.5, 27.5, 40.]),
])
def test_time_series_downsampling(rrddata, twindow, cf, downsampled):
    ts = prediction.TimeSeries(rrddata)
    assert ts.downsample(twindow, cf) == downsampled


@pytest.mark.parametrize("ref_value, stdev, sig, params, levels_factor, result", [
    (2, 0.5, 1, ("absolute", (3, 5)), 0.5, (3.5, 4.5)),
    (2, 0.5, -1, ("relative", (20, 50)), 0.5, (1.6, 1)),
    (2, 0.5, -1, ("stdev", (2, 4)), 0.5, (1, 0)),
])
def test_estimate_level_bounds(ref_value, stdev, sig, params, levels_factor, result):
    assert prediction.estimate_level_bounds(ref_value, stdev, sig, params, levels_factor) == result


@pytest.mark.parametrize("reference, params, levels_factor, result", [
    (
        {
            'average': 5,
            'stdev': 2
        },
        {
            'levels_lower': ('absolute', (2, 4))
        },
        1,
        (5, (None, None, 3, 1)),
    ),
    (
        {
            'average': 0,
            'stdev': 2
        },
        {
            'levels_upper': ('absolute', (2, 4))
        },
        1,
        (0, (2, 4, None, None)),
    ),
    (
        {
            'average': 0,
            'stdev': 2
        },
        {
            'levels_upper': ('relative', (2, 4))
        },
        1,
        (0, (None, None, None, None)),
    ),
    (
        {
            'average': 0,
            'stdev': 2
        },
        {
            'levels_upper': ('stdev', (2, 4))
        },
        1,
        (0, (4, 8, None, None)),
    ),
    (
        {
            'average': 15,
            'stdev': 2,
        },
        {
            'levels_upper': ('stddev', (2, 4)),
            'levels_lower': ('stddev', (3, 5)),
        },
        1,
        (15, (19, 23, 9, 5)),
    ),
    (
        {
            'average': 2,
            'stdev': 3,
        },
        {
            'levels_upper': ('relative', (20, 40)),
            'levels_upper_min': (2, 4),
        },
        1,
        (2, (2.4, 4, None, None)),
    ),
    (
        {
            'average': 200,
            'stdev': 3,
        },
        {
            'levels_upper': ('relative', (20, 40)),
            'levels_upper_min': (2, 4),
        },
        100,
        (200, (240, 400, None, None)),
    ),
])
def test_estimate_levels(reference, params, levels_factor, result):
    assert prediction.estimate_levels(reference, params, levels_factor) == result
