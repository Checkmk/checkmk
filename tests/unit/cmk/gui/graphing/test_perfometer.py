#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.graphing import get_first_matching_perfometer, perfometer_info, PerfometerSpec
from cmk.gui.graphing._perfometer import _perfometer_possible
from cmk.gui.type_defs import TranslatedMetrics


@pytest.mark.parametrize(
    "perfometer, translated_metrics",
    [
        pytest.param(
            {
                "type": "linear",
                "segments": ["m1", "m2,m3,+", "m4,10,*"],
                "total": 100.0,
                "label": ("m1,m2,/", "%"),
            },
            {
                "m1": {"value": 1, "unit": "", "color": "#111111"},
                "m2": {"value": 2, "unit": "", "color": "#222222"},
                "m3": {"value": 3, "unit": "", "color": "#333333"},
                "m4": {"value": 4, "unit": "", "color": "#444444"},
            },
            id="linear with total float",
        ),
        pytest.param(
            {
                "type": "linear",
                "segments": ["m1", "m2,m3,+", "m4,10,*"],
                "total": "m5:max",
                "label": ("m1,m2,/", "%"),
            },
            {
                "m1": {"value": 1, "unit": "", "color": "#111111"},
                "m2": {"value": 2, "unit": "", "color": "#222222"},
                "m3": {"value": 3, "unit": "", "color": "#333333"},
                "m4": {"value": 4, "unit": "", "color": "#444444"},
                "m5": {"value": 5, "unit": "", "color": "#555555", "scalar": {"max": 5}},
            },
            id="linear with total RPN expression",
        ),
        pytest.param(
            {
                "type": "linear",
                "segments": ["m1", "m2,m3,+", "m4,10,*"],
                "total": 100.0,
                "condition": "m1,m2,<",
            },
            {
                "m1": {"value": 1, "unit": "", "color": "#111111"},
                "m2": {"value": 2, "unit": "", "color": "#222222"},
                "m3": {"value": 3, "unit": "", "color": "#333333"},
                "m4": {"value": 4, "unit": "", "color": "#444444"},
            },
            id="linear with condition",
        ),
        pytest.param(
            {
                "type": "logarithmic",
                "metric": "m1",
                "half_value": 5,
                "exponent": 2,
            },
            {
                "m1": {"value": 1, "unit": "", "color": "#111111"},
            },
            id="logarithmic with metric name",
        ),
        pytest.param(
            {
                "type": "logarithmic",
                "metric": "m1,m2,+",
                "half_value": 5,
                "exponent": 2,
            },
            {
                "m1": {"value": 1, "unit": "", "color": "#111111"},
                "m2": {"value": 2, "unit": "", "color": "#222222"},
            },
            id="logarithmic with RPN expression",
        ),
    ],
)
def test__perfometer_possible(
    perfometer: PerfometerSpec,
    translated_metrics: TranslatedMetrics,
) -> None:
    assert _perfometer_possible(perfometer, translated_metrics)


@pytest.mark.parametrize(
    "translated_metrics, perfometer_index",
    [
        pytest.param(
            {"active_connections": {}},
            0,
            id="very first perfometer",
        ),
        pytest.param(
            {
                "delivered_notifications": {"value": 0, "unit": "", "color": "#123456"},
                "failed_notifications": {"value": 0, "unit": "", "color": "#456789"},
            },
            -3,
            id="third from last",
        ),
        pytest.param(
            {
                "delivered_notifications": {"value": 0, "unit": "", "color": "#123456"},
                "failed_notifications": {"value": 1, "unit": "", "color": "#456789"},
            },
            -2,
            id="second from last",
        ),
        pytest.param(
            {"test_runtime": {}},
            -1,
            id="very last perfometer",
        ),
    ],
)
def test_get_first_matching_perfometer(
    translated_metrics: TranslatedMetrics, perfometer_index: int
) -> None:
    assert get_first_matching_perfometer(translated_metrics) == perfometer_info[perfometer_index]
