#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable

import numpy as np
import pytest

from cmk.gui.graphing import (
    get_first_matching_perfometer,
    MetricometerRendererLogarithmic,
    perfometer_info,
    PerfometerSpec,
    renderer_registry,
)
from cmk.gui.graphing._perfometer import (
    _perfometer_possible,
    MetricometerRendererLinear,
    MetricRendererStack,
)
from cmk.gui.type_defs import TranslatedMetrics, UnitInfo


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
        pytest.param(
            {
                "fs_used": {"value": 10, "scalar": {"max": 30}, "unit": "", "color": "#123456"},
                "uncommitted": {"value": 4, "unit": "", "color": "#123456"},
                "fs_size": {"value": 15, "unit": "", "color": "#123456"},
            },
            62,
            id="filesystem check without overcommittment",
        ),
        pytest.param(
            {
                "fs_used": {"value": 10, "scalar": {"max": 100}, "unit": "", "color": "#123456"},
                "uncommitted": {"value": 4, "unit": "", "color": "#123456"},
                "fs_size": {"value": 15, "unit": "", "color": "#123456"},
                "overprovisioned": {"value": 7, "unit": "", "color": "#123456"},
            },
            62,
            id="filesystem check without overcommittment (+overprovisioned)",
        ),
        pytest.param(
            {
                "fs_used": {"value": 10, "scalar": {"max": 100}, "unit": "", "color": "#123456"},
                "uncommitted": {"value": 5, "unit": "", "color": "#123456"},
                "fs_size": {"value": 15, "unit": "", "color": "#123456"},
                "overprovisioned": {"value": 7, "unit": "", "color": "#123456"},
            },
            63,
            id="filesystem check with overcommittment",
        ),
    ],
)
def test_get_first_matching_perfometer(
    translated_metrics: TranslatedMetrics, perfometer_index: int
) -> None:
    assert get_first_matching_perfometer(translated_metrics) == perfometer_info[perfometer_index]


def test_registered_renderers() -> None:
    registered_plugins = sorted(renderer_registry.keys())
    assert registered_plugins == ["dual", "linear", "logarithmic", "stacked"]


class TestMetricometerRendererLinear:
    def _renderer(
        self,
        unit_info: UnitInfo,
    ) -> MetricometerRendererLinear:
        return MetricometerRendererLinear(
            {
                "type": "linear",
                "segments": ["my_metric"],
                "total": 100.0,
            },
            {
                "my_metric": {
                    "orig_name": ["my_metric"],
                    "value": 60.0,
                    "scalar": {"warn": 80.0, "crit": 90.0},
                    "scale": [1.0],
                    "auto_graph": True,
                    "title": "My metric",
                    "unit": unit_info,
                    "color": "#ffa000",
                }
            },
        )

    @pytest.mark.parametrize(
        ["unit_info", "expected_result"],
        [
            pytest.param(
                {
                    "title": "My unit",
                    "symbol": "U",
                    "render": str,
                    "js_render": "v => cmk.number_format.drop_dotzero(v) + ' U'",
                    "id": "u",
                    "description": "My unit",
                },
                [[(60.0, "#ffa000"), (40.0, "#bdbdbd")]],
                id="no unit conversion",
            ),
            pytest.param(
                {
                    "title": "My unit",
                    "symbol": "U",
                    "render": str,
                    "js_render": "v => cmk.number_format.drop_dotzero(v) + ' U'",
                    "id": "u",
                    "description": "My unit",
                    "conversion": lambda v: 2 * v - 10,
                },
                [
                    [
                        (60.0 / (2 * 100 - 10) * 100, "#ffa000"),
                        (100 - 60.0 / (2 * 100 - 10) * 100, "#bdbdbd"),
                    ]
                ],
                id="with unit conversion",
            ),
        ],
    )
    def test_get_stack(
        self,
        unit_info: UnitInfo,
        expected_result: MetricRendererStack,
    ) -> None:
        assert self._renderer(unit_info).get_stack() == expected_result

    @pytest.mark.parametrize(
        ["perfometer_render", "expected_result"],
        [
            pytest.param(
                None,
                "60.0",
                id="no dedicated perfometer renderer",
            ),
            pytest.param(
                lambda v: f"{2*v} U",
                "120.0 U",
                id="dedicated perfometer renderer",
            ),
        ],
    )
    def test_get_label(
        self,
        perfometer_render: Callable[[float], str] | None,
        expected_result: str,
    ) -> None:
        unit_info: UnitInfo = {
            "title": "My unit",
            "symbol": "U",
            "render": str,
            "js_render": "v => cmk.number_format.drop_dotzero(v) + ' U'",
            "id": "u",
            "description": "My unit",
        }
        if perfometer_render:
            unit_info["perfometer_render"] = perfometer_render
        assert self._renderer(unit_info).get_label() == expected_result


class TestMetricometerRendererLogarithmic:
    def _renderer(
        self,
        unit_info: UnitInfo,
    ) -> MetricometerRendererLogarithmic:
        return MetricometerRendererLogarithmic(
            {
                "type": "logarithmic",
                "metric": "my_metric",
                "half_value": 40.0,
                "exponent": 1.2,
            },
            {
                "my_metric": {
                    "orig_name": ["my_metric"],
                    "value": 123.0,
                    "scalar": {"warn": 158.0, "crit": 176.0},
                    "scale": [1.0],
                    "auto_graph": True,
                    "title": "My metric",
                    "unit": unit_info,
                    "color": "#ffa000",
                }
            },
        )

    @pytest.mark.parametrize(
        ["conversion", "expected_result"],
        [
            pytest.param(
                lambda v: v,
                (40, 1.2),
                id="no-op conversion",
            ),
            # a purely multiplicate conversion should not lead to change in the 10%-factor
            pytest.param(
                lambda v: 0.7 * v,
                (0.7 * 40, 1.2),
                id="multiplicative stretch only",
            ),
            # a huge additive offset should lead to a multiplicate 10%-factor very close to 1
            pytest.param(
                lambda v: v + 1000000,
                (40 + 1000000, 1.0),
                id="huge additive offset",
            ),
        ],
    )
    def test_estimate_parameters_for_converted_units(
        self,
        conversion: Callable[[float], float],
        expected_result: tuple[float, float],
    ) -> None:
        assert np.allclose(
            self._renderer(
                {
                    "title": "My unit",
                    "symbol": "U",
                    "render": str,
                    "js_render": "v => cmk.number_format.drop_dotzero(v) + ' U'",
                    "id": "u",
                    "description": "My unit",
                    "perfometer_render": lambda _v: "testing",
                }
            ).estimate_parameters_for_converted_units(conversion),
            expected_result,
        )

    @pytest.mark.parametrize(
        ["perfometer_render", "expected_result"],
        [
            pytest.param(
                None,
                "123.0",
                id="no dedicated perfometer renderer",
            ),
            pytest.param(
                lambda v: f"{2*v} U",
                "246.0 U",
                id="dedicated perfometer renderer",
            ),
        ],
    )
    def test_get_label(
        self,
        perfometer_render: Callable[[float], str] | None,
        expected_result: str,
    ) -> None:
        unit_info: UnitInfo = {
            "title": "My unit",
            "symbol": "U",
            "render": str,
            "js_render": "v => cmk.number_format.drop_dotzero(v) + ' U'",
            "id": "u",
            "description": "My unit",
        }
        if perfometer_render:
            unit_info["perfometer_render"] = perfometer_render
        assert self._renderer(unit_info).get_label() == expected_result
