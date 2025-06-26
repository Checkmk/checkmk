#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Mapping, Sequence

import numpy as np
import pytest

from cmk.utils.exceptions import MKGeneralException

from cmk.gui.graphing import (
    get_first_matching_perfometer,
    MetricometerRendererLegacyLogarithmic,
    PerfometerSpec,
    renderer_registry,
)
from cmk.gui.graphing._perfometer import (
    _ArcTan,
    _make_projection,
    _perfometer_possible,
    _PERFOMETER_PROJECTION_PARAMETERS,
    LegacyPerfometer,
    MetricometerRendererLegacyLinear,
    MetricometerRendererPerfometer,
    MetricometerRendererStacked,
    MetricRendererStack,
    parse_perfometer,
)
from cmk.gui.graphing._type_defs import ScalarBounds, TranslatedMetric, UnitInfo

from cmk.graphing.v1 import metrics, perfometers


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
                "m5": {
                    "value": 5,
                    "unit": "",
                    "color": "#555555",
                    "scalar": {"max": 5},
                },
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
    translated_metrics: Mapping[str, TranslatedMetric],
) -> None:
    assert _perfometer_possible(perfometer, translated_metrics)


@pytest.mark.parametrize(
    "translated_metrics, perfometer",
    [
        pytest.param(
            {"active_connections": {}},
            perfometers.Perfometer(
                name="active_connections",
                focus_range=perfometers.FocusRange(
                    lower=perfometers.Closed(0),
                    upper=perfometers.Open(90),
                ),
                segments=["active_connections"],
            ),
            id="very first perfometer",
        ),
    ],
)
def test_get_first_matching_perfometer(
    translated_metrics: Mapping[str, TranslatedMetric],
    perfometer: perfometers.Perfometer | perfometers.Bidirectional | perfometers.Stacked,
) -> None:
    assert get_first_matching_perfometer(translated_metrics) == perfometer


@pytest.mark.parametrize(
    "translated_metrics, perfometer",
    [
        pytest.param(
            {
                "delivered_notifications": {"value": 0, "unit": "", "color": "#123456"},
                "failed_notifications": {"value": 0, "unit": "", "color": "#456789"},
            },
            {
                "condition": "delivered_notifications,failed_notifications,+,delivered_notifications,failed_notifications,+,2,*,>=",
                "label": ("delivered_notifications,failed_notifications,+,100,+", "%"),
                "segments": ["delivered_notifications,failed_notifications,+,100,+"],
                "total": 100.0,
                "type": "linear",
            },
            id="second to last",
        ),
        pytest.param(
            {
                "delivered_notifications": {"value": 0, "unit": "", "color": "#123456"},
                "failed_notifications": {"value": 1, "unit": "", "color": "#456789"},
            },
            {
                "condition": "delivered_notifications,failed_notifications,+,delivered_notifications,failed_notifications,+,2,*,<",
                "label": (
                    "delivered_notifications,failed_notifications,delivered_notifications,+,/,100,*",
                    "%",
                ),
                "segments": [
                    "delivered_notifications,failed_notifications,delivered_notifications,+,/,100,*"
                ],
                "total": 100.0,
                "type": "linear",
            },
            id="very last perfometer",
        ),
        pytest.param(
            {
                "fs_used": {
                    "value": 10,
                    "scalar": {"max": 30},
                    "unit": "",
                    "color": "#123456",
                },
                "uncommitted": {"value": 4, "unit": "", "color": "#123456"},
                "fs_size": {"value": 15, "unit": "", "color": "#123456"},
            },
            {
                "condition": "fs_used,uncommitted,+,fs_size,<",
                "label": ("fs_used(%)", "%"),
                "segments": [
                    "fs_used",
                    "uncommitted",
                    "fs_size,fs_used,-,uncommitted,-#e3fff9",
                    "0.1#559090",
                ],
                "total": "fs_size",
                "type": "linear",
            },
            id="filesystem check without overcommittment",
        ),
        pytest.param(
            {
                "fs_used": {
                    "value": 10,
                    "scalar": {"max": 100},
                    "unit": "",
                    "color": "#123456",
                },
                "uncommitted": {"value": 4, "unit": "", "color": "#123456"},
                "fs_size": {"value": 15, "unit": "", "color": "#123456"},
                "overprovisioned": {"value": 7, "unit": "", "color": "#123456"},
            },
            {
                "condition": "fs_used,uncommitted,+,fs_size,<",
                "label": ("fs_used(%)", "%"),
                "segments": [
                    "fs_used",
                    "uncommitted",
                    "fs_size,fs_used,-,uncommitted,-#e3fff9",
                    "0.1#559090",
                ],
                "total": "fs_size",
                "type": "linear",
            },
            id="filesystem check without overcommittment (+overprovisioned)",
        ),
        pytest.param(
            {
                "fs_used": {
                    "value": 10,
                    "scalar": {"max": 100},
                    "unit": "",
                    "color": "#123456",
                },
                "uncommitted": {"value": 5, "unit": "", "color": "#123456"},
                "fs_size": {"value": 15, "unit": "", "color": "#123456"},
                "overprovisioned": {"value": 7, "unit": "", "color": "#123456"},
            },
            {
                "condition": "fs_used,uncommitted,+,fs_size,>=",
                "label": ("fs_used,fs_used,uncommitted,+,/,100,*", "%"),
                "segments": [
                    "fs_used",
                    "fs_size,fs_used,-#e3fff9",
                    "0.1#559090",
                    "overprovisioned,fs_size,-#ffa000",
                ],
                "total": "overprovisioned",
                "type": "linear",
            },
            id="filesystem check with overcommittment",
        ),
    ],
)
def test_get_first_matching_legacy_perfometer(
    translated_metrics: Mapping[str, TranslatedMetric], perfometer: dict
) -> None:
    assert get_first_matching_perfometer(translated_metrics) == perfometer


def test_registered_renderers() -> None:
    registered_plugins = sorted(renderer_registry.keys())
    assert registered_plugins == sorted(
        [
            "perfometer",
            "bidirectional",
            "stacked",
            "legacy_dual",
            "legacy_linear",
            "legacy_logarithmic",
            "legacy_stacked",
        ]
    )


class TestMetricometerRendererLegacyLinear:
    def _renderer(
        self,
        unit_info: UnitInfo,
    ) -> MetricometerRendererLegacyLinear:
        return MetricometerRendererLegacyLinear(
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


class TestMetricometerRendererLegacyLogarithmic:
    def _renderer(
        self,
        unit_info: UnitInfo,
    ) -> MetricometerRendererLegacyLogarithmic:
        return MetricometerRendererLegacyLogarithmic(
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


@pytest.mark.parametrize(
    "focus_range",
    [
        pytest.param(
            perfometers.FocusRange(perfometers.Closed(10), perfometers.Closed(-10)),
            id="closed-closed",
        ),
        pytest.param(
            perfometers.FocusRange(perfometers.Open(10), perfometers.Closed(-10)),
            id="open-closed",
        ),
        pytest.param(
            perfometers.FocusRange(perfometers.Closed(10), perfometers.Open(-10)),
            id="closed-open",
        ),
        pytest.param(
            perfometers.FocusRange(perfometers.Open(10), perfometers.Open(-10)),
            id="open-open",
        ),
    ],
)
def test_perfometer_projection_error(focus_range: perfometers.FocusRange) -> None:
    with pytest.raises(ValueError):
        _make_projection(focus_range, _PERFOMETER_PROJECTION_PARAMETERS, {})


@pytest.mark.parametrize(
    "value, result",
    [
        pytest.param(-10, 0.0, id="left"),
        pytest.param(5, 50.0, id="middle"),
        pytest.param(20, 100.0, id="right"),
    ],
)
def test_perfometer_projection_closed_closed(value: int | float, result: float) -> None:
    projection = _make_projection(
        perfometers.FocusRange(perfometers.Closed(-10), perfometers.Closed(20)),
        _PERFOMETER_PROJECTION_PARAMETERS,
        {},
    )
    assert projection(value) == result


@pytest.mark.parametrize(
    "value, result",
    [
        pytest.param(-11, -10, id="left-too-low"),
        pytest.param(21, 20, id="right-too-high"),
    ],
)
def test_perfometer_projection_closed_closed_exceeds(
    value: int | float, result: int | float
) -> None:
    projection = _make_projection(
        perfometers.FocusRange(perfometers.Closed(-10), perfometers.Closed(20)),
        _PERFOMETER_PROJECTION_PARAMETERS,
        {},
    )
    assert projection(value) == result


@pytest.mark.parametrize(
    "value, result",
    [
        pytest.param(-11, 12.245677114157232, id="left-lower"),
        pytest.param(-10, 15.0, id="left"),
        pytest.param(5, 57.5, id="middle"),
        pytest.param(20, 100.0, id="right"),
    ],
)
def test_perfometer_projection_open_closed(value: int | float, result: float) -> None:
    projection = _make_projection(
        perfometers.FocusRange(perfometers.Open(-10), perfometers.Closed(20)),
        _PERFOMETER_PROJECTION_PARAMETERS,
        {},
    )
    assert projection(value) == result


@pytest.mark.parametrize(
    "value, result",
    [
        pytest.param(21, 20, id="right-too-high"),
    ],
)
def test_perfometer_projection_open_closed_exceeds(value: int | float, result: int | float) -> None:
    projection = _make_projection(
        perfometers.FocusRange(perfometers.Open(-10), perfometers.Closed(20)),
        _PERFOMETER_PROJECTION_PARAMETERS,
        {},
    )
    assert projection(value) == result


@pytest.mark.parametrize(
    "value, result",
    [
        pytest.param(-10, 0.0, id="left"),
        pytest.param(5, 42.5, id="middle"),
        pytest.param(20, 85.0, id="right"),
        pytest.param(21, 87.75432288584277, id="right-higher"),
    ],
)
def test_perfometer_projection_closed_open(value: int | float, result: float) -> None:
    projection = _make_projection(
        perfometers.FocusRange(perfometers.Closed(-10), perfometers.Open(20)),
        _PERFOMETER_PROJECTION_PARAMETERS,
        {},
    )
    assert projection(value) == result


@pytest.mark.parametrize(
    "value, result",
    [
        pytest.param(-11, -10, id="left-too-low"),
    ],
)
def test_perfometer_projection_closed_open_exceeds(value: int | float, result: int | float) -> None:
    projection = _make_projection(
        perfometers.FocusRange(perfometers.Closed(-10), perfometers.Open(20)),
        _PERFOMETER_PROJECTION_PARAMETERS,
        {},
    )
    assert projection(value) == result


@pytest.mark.parametrize(
    "value, result",
    [
        pytest.param(-11, 12.711508180641701, id="left-lower"),
        pytest.param(-10, 15.0, id="left"),
        pytest.param(5, 50.0, id="middle"),
        pytest.param(20, 85.0, id="right"),
        pytest.param(21, 87.2884918193583, id="right-higher"),
    ],
)
def test_perfometer_projection_open_open(value: int | float, result: float) -> None:
    projection = _make_projection(
        perfometers.FocusRange(perfometers.Open(-10), perfometers.Open(20)),
        _PERFOMETER_PROJECTION_PARAMETERS,
        {},
    )
    assert projection(value) == result


@pytest.mark.parametrize(
    "segments, translated_metrics, value_projections",
    [
        pytest.param(
            ["metric-name"],
            {
                "metric-name": {
                    "orig_name": ["metric-name"],
                    "value": 2600.0,
                    "scalar": {},
                    "scale": [1.0],
                    "auto_graph": True,
                    "title": "Metric name 1",
                    "unit": {
                        "title": "Title",
                        "symbol": "",
                        "render": lambda v: f"{v}",
                        "js_render": "v => v",
                    },
                    "color": "#111111",
                },
            },
            [(88.27, "#111111")],
            id="one-metric",
        ),
        pytest.param(
            ["metric-name1", "metric-name2"],
            {
                "metric-name1": {
                    "orig_name": ["metric-name1"],
                    "value": 2000.0,
                    "scalar": {},
                    "scale": [1.0],
                    "auto_graph": True,
                    "title": "Metric name 1",
                    "unit": {
                        "title": "Title",
                        "symbol": "",
                        "render": lambda v: f"{v}",
                        "js_render": "v => v",
                    },
                    "color": "#111111",
                },
                "metric-name2": {
                    "orig_name": ["metric-name2"],
                    "value": 600.0,
                    "scalar": {},
                    "scale": [1.0],
                    "auto_graph": True,
                    "title": "Metric name 2",
                    "unit": {
                        "title": "Title",
                        "symbol": "",
                        "render": lambda v: f"{v}",
                        "js_render": "v => v",
                    },
                    "color": "#222222",
                },
            },
            [(67.9, "#111111"), (20.37, "#222222")],
            id="two-metrics",
        ),
        pytest.param(
            ["metric-name1", "metric-name2", "metric-name3"],
            {
                "metric-name1": {
                    "orig_name": ["metric-name1"],
                    "value": 2000.0,
                    "scalar": {},
                    "scale": [1.0],
                    "auto_graph": True,
                    "title": "Metric name 1",
                    "unit": {
                        "title": "Title",
                        "symbol": "",
                        "render": lambda v: f"{v}",
                        "js_render": "v => v",
                    },
                    "color": "#111111",
                },
                "metric-name2": {
                    "orig_name": ["metric-name2"],
                    "value": 400.0,
                    "scalar": {},
                    "scale": [1.0],
                    "auto_graph": True,
                    "title": "Metric name 2",
                    "unit": {
                        "title": "Title",
                        "symbol": "",
                        "render": lambda v: f"{v}",
                        "js_render": "v => v",
                    },
                    "color": "#222222",
                },
                "metric-name3": {
                    "orig_name": ["metric-name3"],
                    "value": 200.0,
                    "scalar": {},
                    "scale": [1.0],
                    "auto_graph": True,
                    "title": "Metric name 3",
                    "unit": {
                        "title": "Title",
                        "symbol": "",
                        "render": lambda v: f"{v}",
                        "js_render": "v => v",
                    },
                    "color": "#333333",
                },
            },
            [(67.9, "#111111"), (13.58, "#222222"), (6.79, "#333333")],
            id="three-metrics",
        ),
    ],
)
def test_perfometer_renderer_stack(
    segments: Sequence[
        str
        | metrics.Constant
        | metrics.WarningOf
        | metrics.CriticalOf
        | metrics.MinimumOf
        | metrics.MaximumOf
        | metrics.Sum
        | metrics.Product
        | metrics.Difference
        | metrics.Fraction
    ],
    translated_metrics: Mapping[str, TranslatedMetric],
    value_projections: Sequence[tuple[float, str]],
) -> None:
    assert MetricometerRendererPerfometer(
        perfometers.Perfometer(
            name="name",
            focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(2500.0)),
            segments=segments,
        ),
        translated_metrics,
    ).get_stack() == [list(value_projections) + [(11.73, "#bdbdbd")]]


def test_perfometer_renderer_stack_same_values() -> None:
    assert MetricometerRendererPerfometer(
        perfometers.Perfometer(
            name="name",
            focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(2500.0)),
            segments=["metric-name1", "metric-name2"],
        ),
        {
            "metric-name1": {
                "orig_name": ["metric-name1"],
                "value": 1300.0,
                "scalar": {},
                "scale": [1.0],
                "auto_graph": True,
                "title": "Metric name 1",
                "unit": {
                    "title": "Title",
                    "symbol": "",
                    "render": lambda v: f"{v}",
                    "js_render": "v => v",
                },
                "color": "#111111",
            },
            "metric-name2": {
                "orig_name": ["metric-name2"],
                "value": 1300.0,
                "scalar": {},
                "scale": [1.0],
                "auto_graph": True,
                "title": "Metric name 2",
                "unit": {
                    "title": "Title",
                    "symbol": "",
                    "render": lambda v: f"{v}",
                    "js_render": "v => v",
                },
                "color": "#222222",
            },
        },
    ).get_stack() == [[(44.13, "#111111"), (44.13, "#222222"), (11.74, "#bdbdbd")]]


@pytest.mark.parametrize(
    "segments, translated_metrics, stack, label",
    [
        pytest.param(
            ["metric-name"],
            {
                "metric-name": TranslatedMetric(
                    orig_name=["metric-name"],
                    value=101.0,
                    scalar=ScalarBounds(),
                    scale=[1.0],
                    auto_graph=True,
                    title="Metric name",
                    unit=UnitInfo(
                        title="Title",
                        symbol="",
                        render=lambda v: f"{v}",
                        js_render="v => v",
                    ),
                    color="#111111",
                ),
            },
            [[(100.0, "#111111"), (0.0, "#bdbdbd")]],
            "101.0",
            id="one-metric",
        ),
        pytest.param(
            ["metric-name1", "metric-name2"],
            {
                "metric-name1": TranslatedMetric(
                    orig_name=["metric-name1"],
                    value=99.0,
                    scalar=ScalarBounds(),
                    scale=[1.0],
                    auto_graph=True,
                    title="Metric name 1",
                    unit=UnitInfo(
                        title="Title",
                        symbol="",
                        render=lambda v: f"{v}",
                        js_render="v => v",
                    ),
                    color="#111111",
                ),
                "metric-name2": TranslatedMetric(
                    orig_name=["metric-name2"],
                    value=2.0,
                    scalar=ScalarBounds(),
                    scale=[1.0],
                    auto_graph=True,
                    title="Metric name 2",
                    unit=UnitInfo(
                        title="Title",
                        symbol="",
                        render=lambda v: f"{v}",
                        js_render="v => v",
                    ),
                    color="#111111",
                ),
            },
            [[(98.02, "#111111"), (1.98, "#111111"), (0.0, "#bdbdbd")]],
            "101.0",
            id="two-metrics",
        ),
    ],
)
def test_perfometer_renderer_exceeds_limit(
    segments: Sequence[
        str
        | metrics.Constant
        | metrics.WarningOf
        | metrics.CriticalOf
        | metrics.MinimumOf
        | metrics.MaximumOf
        | metrics.Sum
        | metrics.Product
        | metrics.Difference
        | metrics.Fraction
    ],
    translated_metrics: Mapping[str, TranslatedMetric],
    stack: Sequence[Sequence[tuple[float, str]]],
    label: str,
) -> None:
    metricometer = MetricometerRendererPerfometer(
        perfometers.Perfometer(
            name="name",
            focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Closed(100)),
            segments=segments,
        ),
        translated_metrics,
    )
    assert metricometer.get_stack() == stack
    assert metricometer.get_label() == label


@pytest.mark.parametrize(
    "legacy_perfometer, expected_perfometer",
    [
        pytest.param(
            ("linear", ([], 100, "Label 1")),
            {"type": "linear", "segments": [], "total": 100, "label": "Label 1"},
            id="linear",
        ),
        pytest.param(
            (
                "dual",
                [("linear", ([], 100, "Label 2")), ("linear", ([], 100, "Label 3"))],
            ),
            {
                "type": "dual",
                "perfometers": [
                    {
                        "type": "linear",
                        "segments": [],
                        "total": 100,
                        "label": "Label 2",
                    },
                    {
                        "type": "linear",
                        "segments": [],
                        "total": 100,
                        "label": "Label 3",
                    },
                ],
            },
            id="dual",
        ),
        pytest.param(
            (
                "stacked",
                [("linear", ([], 100, "Label 4")), ("linear", ([], 100, "Label 5"))],
            ),
            {
                "type": "stacked",
                "perfometers": [
                    {
                        "type": "linear",
                        "segments": [],
                        "total": 100,
                        "label": "Label 4",
                    },
                    {
                        "type": "linear",
                        "segments": [],
                        "total": 100,
                        "label": "Label 5",
                    },
                ],
            },
            id="stacked",
        ),
    ],
)
def test_parse_perfometer(
    legacy_perfometer: LegacyPerfometer, expected_perfometer: PerfometerSpec
) -> None:
    assert parse_perfometer(legacy_perfometer) == expected_perfometer


@pytest.mark.parametrize(
    "legacy_perfometer",
    [
        pytest.param(
            ("dual", [("linear", ([], 100, "Label"))]),
            id="dual-one-sub-perfometers",
        ),
        pytest.param(
            (
                "dual",
                [
                    ("linear", ([], 100, "Label 1")),
                    ("linear", ([], 100, "Label 2")),
                    ("linear", ([], 100, "Label 3")),
                ],
            ),
            id="dual-three-sub-perfometers",
        ),
        pytest.param(
            (
                "dual",
                [
                    (
                        "dual",
                        [
                            ("linear", ([], 100, "Label 1")),
                            ("linear", ([], 100, "Label 2")),
                        ],
                    )
                ],
            ),
            id="dual-dual-sub-perfometers",
        ),
        pytest.param(
            (
                "dual",
                [
                    (
                        "stacked",
                        [
                            ("linear", ([], 100, "Label 1")),
                            ("linear", ([], 100, "Label 2")),
                        ],
                    )
                ],
            ),
            id="dual-stacked-sub-perfometers",
        ),
        pytest.param(
            (
                "stacked",
                [
                    (
                        "stacked",
                        [
                            ("linear", ([], 100, "Label 1")),
                            ("linear", ([], 100, "Label 2")),
                        ],
                    )
                ],
            ),
            id="stacked-stacked-sub-perfometers",
        ),
        pytest.param(
            (
                "stacked",
                [
                    (
                        "dual",
                        [
                            ("linear", ([], 100, "Label 1")),
                            ("linear", ([], 100, "Label 2")),
                        ],
                    )
                ],
            ),
            id="stacked-dual-sub-perfometers",
        ),
    ],
)
def test_parse_dual_or_stacked_perfometer_errors(
    legacy_perfometer: LegacyPerfometer,
) -> None:
    with pytest.raises(MKGeneralException):
        parse_perfometer(legacy_perfometer)


def test_metricometer_renderer_stacked() -> None:
    metricometer = MetricometerRendererStacked(
        perfometers.Stacked(
            name="stacked",
            lower=perfometers.Perfometer(
                name="lower",
                focus_range=perfometers.FocusRange(
                    lower=perfometers.Closed(0),
                    upper=perfometers.Open(10),
                ),
                segments=["metric_1"],
            ),
            upper=perfometers.Perfometer(
                name="upper",
                focus_range=perfometers.FocusRange(
                    lower=perfometers.Closed(0),
                    upper=perfometers.Open(10),
                ),
                segments=["metric_2"],
            ),
        ),
        {
            "metric_1": TranslatedMetric(
                orig_name=["metric_1"],
                value=2.0,
                scalar=ScalarBounds(),
                scale=[1.0],
                auto_graph=True,
                title="Metric 1",
                unit=UnitInfo(
                    title="Title",
                    symbol="",
                    render=lambda v: f"{v}",
                    js_render="v => v",
                ),
                color="#111111",
            ),
            "metric_2": TranslatedMetric(
                orig_name=["metric_2"],
                value=7.0,
                scalar=ScalarBounds(),
                scale=[1.0],
                auto_graph=True,
                title="Metric 1",
                unit=UnitInfo(
                    title="Title",
                    symbol="",
                    render=lambda v: f"{v}",
                    js_render="v => v",
                ),
                color="#111111",
            ),
        },
    )
    assert metricometer.get_stack() == [
        [(59.5, "#111111"), (40.5, "#bdbdbd")],
        [(17.0, "#111111"), (83.0, "#bdbdbd")],
    ]
    assert metricometer.get_label() == "7.0 / 2.0"


class TestArcTan:
    def test_inflection_point_value(self) -> None:
        arc_tan = _ArcTan(
            x_inflection=1.0,
            y_inflection=2.0,
            slope_inflection=1.0,
            scale_in_units_of_pi_half=1.0,
        )
        assert abs(arc_tan(arc_tan.x_inflection) - arc_tan.y_inflection) < 1e-6

    def test_inflection_point_slope(self) -> None:
        arc_tan = _ArcTan(
            x_inflection=0.0,
            y_inflection=0.0,
            slope_inflection=1.0,
            scale_in_units_of_pi_half=1.0,
        )
        value_slightly_left = arc_tan(arc_tan.x_inflection - 0.05)
        value_slightly_right = arc_tan(arc_tan.x_inflection + 0.05)
        assert (
            abs((value_slightly_right - value_slightly_left) / 0.1 - arc_tan.slope_inflection)
            < 1e-2
        )

    def test_scale(self) -> None:
        arc_tan = _ArcTan(
            x_inflection=0.0,
            y_inflection=3.4,
            slope_inflection=1.0,
            scale_in_units_of_pi_half=1.0,
        )
        expected_upper_limit = arc_tan.y_inflection + arc_tan.scale_in_units_of_pi_half
        expected_lower_limit = arc_tan.y_inflection - arc_tan.scale_in_units_of_pi_half

        assert arc_tan(100) < arc_tan(1000) < arc_tan(10000) < expected_upper_limit
        assert abs(arc_tan(100) - expected_upper_limit) < 1e-2
        assert abs(arc_tan(1000) - expected_upper_limit) < 1e-3
        assert abs(arc_tan(10000) - expected_upper_limit) < 1e-4

        assert arc_tan(-100) > arc_tan(-1000) > arc_tan(-10000) > expected_lower_limit
        assert abs(expected_lower_limit - arc_tan(-100)) < 1e-2
        assert abs(expected_lower_limit - arc_tan(-1000)) < 1e-3
        assert abs(expected_lower_limit - arc_tan(-10000)) < 1e-4
