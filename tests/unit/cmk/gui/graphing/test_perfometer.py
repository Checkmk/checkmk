#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import math
from collections.abc import Callable, Mapping, Sequence

import numpy as np
import pytest

from cmk.ccc.exceptions import MKGeneralException

from cmk.gui.graphing import get_first_matching_perfometer, PerfometerSpec
from cmk.gui.graphing._formatter import AutoPrecision
from cmk.gui.graphing._legacy import LegacyPerfometer, UnitInfo
from cmk.gui.graphing._perfometer import (
    _make_projection,
    _perfometer_possible,
    _PERFOMETER_PROJECTION_PARAMETERS,
    MetricometerRendererLegacyLinear,
    MetricometerRendererLegacyLogarithmic,
    MetricometerRendererPerfometer,
    MetricRendererStack,
    parse_perfometer,
)
from cmk.gui.graphing._translated_metrics import Original, ScalarBounds, TranslatedMetric
from cmk.gui.graphing._unit import ConvertibleUnitSpecification, DecimalNotation

from cmk.graphing.v1 import metrics as metrics_api
from cmk.graphing.v1 import perfometers as perfometers_api


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
                "m1": TranslatedMetric(
                    originals=[],
                    value=1,
                    scalar={},
                    auto_graph=False,
                    title="",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#111111",
                ),
                "m2": TranslatedMetric(
                    originals=[],
                    value=2,
                    scalar={},
                    auto_graph=False,
                    title="",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#222222",
                ),
                "m3": TranslatedMetric(
                    originals=[],
                    value=3,
                    scalar={},
                    auto_graph=False,
                    title="",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#333333",
                ),
                "m4": TranslatedMetric(
                    originals=[],
                    value=4,
                    scalar={},
                    auto_graph=False,
                    title="",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#444444",
                ),
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
                "m1": TranslatedMetric(
                    originals=[],
                    value=1,
                    scalar={},
                    auto_graph=False,
                    title="",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#111111",
                ),
                "m2": TranslatedMetric(
                    originals=[],
                    value=2,
                    scalar={},
                    auto_graph=False,
                    title="",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#222222",
                ),
                "m3": TranslatedMetric(
                    originals=[],
                    value=3,
                    scalar={},
                    auto_graph=False,
                    title="",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#333333",
                ),
                "m4": TranslatedMetric(
                    originals=[],
                    value=4,
                    scalar={},
                    auto_graph=False,
                    title="",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#444444",
                ),
                "m5": TranslatedMetric(
                    originals=[],
                    value=5,
                    scalar={"max": 5},
                    auto_graph=False,
                    title="",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#555555",
                ),
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
                "m1": TranslatedMetric(
                    originals=[],
                    value=1,
                    scalar={},
                    auto_graph=False,
                    title="",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#111111",
                ),
                "m2": TranslatedMetric(
                    originals=[],
                    value=2,
                    scalar={},
                    auto_graph=False,
                    title="",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#222222",
                ),
                "m3": TranslatedMetric(
                    originals=[],
                    value=3,
                    scalar={},
                    auto_graph=False,
                    title="",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#333333",
                ),
                "m4": TranslatedMetric(
                    originals=[],
                    value=4,
                    scalar={},
                    auto_graph=False,
                    title="",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#444444",
                ),
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
                "m1": TranslatedMetric(
                    originals=[],
                    value=1,
                    scalar={},
                    auto_graph=False,
                    title="",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#111111",
                ),
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
                "m1": TranslatedMetric(
                    originals=[],
                    value=1,
                    scalar={},
                    auto_graph=False,
                    title="",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#111111",
                ),
                "m2": TranslatedMetric(
                    originals=[],
                    value=2,
                    scalar={},
                    auto_graph=False,
                    title="",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#222222",
                ),
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
            perfometers_api.Perfometer(
                name="active_connections",
                focus_range=perfometers_api.FocusRange(
                    lower=perfometers_api.Closed(0),
                    upper=perfometers_api.Open(90),
                ),
                segments=["active_connections"],
            ),
            id="very first perfometer",
        ),
    ],
)
def test_get_first_matching_perfometer(
    translated_metrics: Mapping[str, TranslatedMetric],
    perfometer: (
        perfometers_api.Perfometer | perfometers_api.Bidirectional | perfometers_api.Stacked
    ),
    request_context: None,
) -> None:
    assert (first_renderer := get_first_matching_perfometer(translated_metrics)) is not None
    assert first_renderer.perfometer == perfometer


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
                "my_metric": TranslatedMetric(
                    originals=[Original("my_metric", 1.0)],
                    value=60.0,
                    scalar={"warn": 80.0, "crit": 90.0},
                    auto_graph=True,
                    title="My metric",
                    unit_spec=unit_info,
                    color="#ffa000",
                )
            },
        )

    @pytest.mark.parametrize(
        ["unit_info", "expected_result"],
        [
            pytest.param(
                UnitInfo(
                    id="u",
                    title="My unit",
                    symbol="U",
                    render=str,
                    js_render="v => cmk.number_format.drop_dotzero(v) + ' U'",
                    conversion=lambda v: v,
                    description="My unit",
                ),
                [[(60.0, "#ffa000"), (40.0, "#bdbdbd")]],
                id="no unit conversion",
            ),
            pytest.param(
                UnitInfo(
                    id="u",
                    title="My unit",
                    symbol="U",
                    render=str,
                    js_render="v => cmk.number_format.drop_dotzero(v) + ' U'",
                    conversion=lambda v: 2 * v - 10,
                    description="My unit",
                ),
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
        request_context: None,
        patch_theme: None,
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
                lambda v: f"{2 * v} U",
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
        unit_info = UnitInfo(
            id="u",
            title="My unit",
            symbol="U",
            render=str,
            js_render="v => cmk.number_format.drop_dotzero(v) + ' U'",
            conversion=lambda v: v,
            description="My unit",
            perfometer_render=perfometer_render,
        )
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
                "my_metric": TranslatedMetric(
                    originals=[Original("my_metric", 1.0)],
                    value=123.0,
                    scalar={"warn": 158.0, "crit": 176.0},
                    auto_graph=True,
                    title="My metric",
                    unit_spec=unit_info,
                    color="#ffa000",
                )
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
                UnitInfo(
                    id="u",
                    title="My unit",
                    symbol="U",
                    render=str,
                    js_render="v => cmk.number_format.drop_dotzero(v) + ' U'",
                    conversion=lambda v: v,
                    description="My unit",
                    perfometer_render=lambda _v: "testing",
                )
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
                lambda v: f"{2 * v} U",
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
        unit_info = UnitInfo(
            id="u",
            title="My unit",
            symbol="U",
            render=str,
            js_render="v => cmk.number_format.drop_dotzero(v) + ' U'",
            conversion=lambda v: v,
            description="My unit",
            perfometer_render=perfometer_render,
        )
        assert self._renderer(unit_info).get_label() == expected_result


@pytest.mark.parametrize(
    "focus_range",
    [
        pytest.param(
            perfometers_api.FocusRange(perfometers_api.Closed(10), perfometers_api.Closed(-10)),
            id="closed-closed",
        ),
        pytest.param(
            perfometers_api.FocusRange(perfometers_api.Open(10), perfometers_api.Closed(-10)),
            id="open-closed",
        ),
        pytest.param(
            perfometers_api.FocusRange(perfometers_api.Closed(10), perfometers_api.Open(-10)),
            id="closed-open",
        ),
        pytest.param(
            perfometers_api.FocusRange(perfometers_api.Open(10), perfometers_api.Open(-10)),
            id="open-open",
        ),
        pytest.param(
            perfometers_api.FocusRange(perfometers_api.Closed(0), perfometers_api.Closed(0)),
            id="closed-closed-equal",
        ),
    ],
)
def test_perfometer_projection_error(focus_range: perfometers_api.FocusRange) -> None:
    projection = _make_projection(
        focus_range,
        _PERFOMETER_PROJECTION_PARAMETERS,
        {},
        "name",
    )
    assert math.isnan(projection.lower_x)
    assert math.isnan(projection.upper_x)
    assert math.isnan(projection.lower_atan(123))
    assert math.isnan(projection.focus_linear(456))
    assert math.isnan(projection.upper_atan(789))
    assert math.isnan(projection.limit)


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
        perfometers_api.FocusRange(perfometers_api.Closed(-10), perfometers_api.Closed(20)),
        _PERFOMETER_PROJECTION_PARAMETERS,
        {},
        "name",
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
        perfometers_api.FocusRange(perfometers_api.Closed(-10), perfometers_api.Closed(20)),
        _PERFOMETER_PROJECTION_PARAMETERS,
        {},
        "name",
    )
    assert projection(value) == result


@pytest.mark.parametrize(
    "value, result",
    [
        pytest.param(-11, 14.777817878976812, id="left-lower"),
        pytest.param(-10, 15.0, id="left"),
        pytest.param(5, 57.5, id="middle"),
        pytest.param(20, 100.0, id="right"),
    ],
)
def test_perfometer_projection_open_closed(value: int | float, result: float) -> None:
    projection = _make_projection(
        perfometers_api.FocusRange(perfometers_api.Open(-10), perfometers_api.Closed(20)),
        _PERFOMETER_PROJECTION_PARAMETERS,
        {},
        "name",
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
        perfometers_api.FocusRange(perfometers_api.Open(-10), perfometers_api.Closed(20)),
        _PERFOMETER_PROJECTION_PARAMETERS,
        {},
        "name",
    )
    assert projection(value) == result


@pytest.mark.parametrize(
    "value, result",
    [
        pytest.param(-10, 0.0, id="left"),
        pytest.param(5, 42.5, id="middle"),
        pytest.param(20, 85.0, id="right"),
        pytest.param(21, 85.2221821210232, id="right-higher"),
    ],
)
def test_perfometer_projection_closed_open(value: int | float, result: float) -> None:
    projection = _make_projection(
        perfometers_api.FocusRange(perfometers_api.Closed(-10), perfometers_api.Open(20)),
        _PERFOMETER_PROJECTION_PARAMETERS,
        {},
        "name",
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
        perfometers_api.FocusRange(perfometers_api.Closed(-10), perfometers_api.Open(20)),
        _PERFOMETER_PROJECTION_PARAMETERS,
        {},
        "name",
    )
    assert projection(value) == result


@pytest.mark.parametrize(
    "value, result",
    [
        pytest.param(-11, 14.777817878976812, id="left-lower"),
        pytest.param(-10, 15.0, id="left"),
        pytest.param(5, 50.0, id="middle"),
        pytest.param(20, 85.0, id="right"),
        pytest.param(21, 85.2221821210232, id="right-higher"),
    ],
)
def test_perfometer_projection_open_open(value: int | float, result: float) -> None:
    projection = _make_projection(
        perfometers_api.FocusRange(perfometers_api.Open(-10), perfometers_api.Open(20)),
        _PERFOMETER_PROJECTION_PARAMETERS,
        {},
        "name",
    )
    assert projection(value) == result


@pytest.mark.parametrize(
    "segments, translated_metrics, value_projections",
    [
        pytest.param(
            ["metric-name"],
            {
                "metric-name": TranslatedMetric(
                    originals=[Original("metric-name", 1.0)],
                    value=2600.0,
                    scalar={},
                    auto_graph=True,
                    title="Metric name 1",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#111111",
                ),
            },
            [(85.27, "#111111")],
            id="one-metric",
        ),
        pytest.param(
            ["metric-name1", "metric-name2"],
            {
                "metric-name1": TranslatedMetric(
                    originals=[Original("metric-name1", 1.0)],
                    value=2000.0,
                    scalar={},
                    auto_graph=True,
                    title="Metric name 1",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#111111",
                ),
                "metric-name2": TranslatedMetric(
                    originals=[Original("metric-name2", 1.0)],
                    value=600.0,
                    scalar={},
                    auto_graph=True,
                    title="Metric name 2",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#222222",
                ),
            },
            [(65.59, "#111111"), (19.68, "#222222")],
            id="two-metrics",
        ),
        pytest.param(
            ["metric-name1", "metric-name2", "metric-name3"],
            {
                "metric-name1": TranslatedMetric(
                    originals=[Original("metric-name1", 1.0)],
                    value=2000.0,
                    scalar={},
                    auto_graph=True,
                    title="Metric name 1",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#111111",
                ),
                "metric-name2": TranslatedMetric(
                    originals=[Original("metric-name2", 1.0)],
                    value=400.0,
                    scalar={},
                    auto_graph=True,
                    title="Metric name 2",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#222222",
                ),
                "metric-name3": TranslatedMetric(
                    originals=[Original("metric-name3", 1.0)],
                    value=200.0,
                    scalar={},
                    auto_graph=True,
                    title="Metric name 3",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#333333",
                ),
            },
            [(65.59, "#111111"), (13.12, "#222222"), (6.56, "#333333")],
            id="three-metrics",
        ),
    ],
)
def test_perfometer_renderer_stack(
    segments: Sequence[
        str
        | metrics_api.Constant
        | metrics_api.WarningOf
        | metrics_api.CriticalOf
        | metrics_api.MinimumOf
        | metrics_api.MaximumOf
        | metrics_api.Sum
        | metrics_api.Product
        | metrics_api.Difference
        | metrics_api.Fraction
    ],
    translated_metrics: Mapping[str, TranslatedMetric],
    value_projections: Sequence[tuple[float, str]],
    request_context: None,
    patch_theme: None,
) -> None:
    assert MetricometerRendererPerfometer(
        perfometers_api.Perfometer(
            name="name",
            focus_range=perfometers_api.FocusRange(
                perfometers_api.Closed(0), perfometers_api.Open(2500.0)
            ),
            segments=segments,
        ),
        translated_metrics,
        "#bdbdbd",
    ).get_stack() == [list(value_projections) + [(14.73, "#bdbdbd")]]


def test_perfometer_renderer_stack_same_values(request_context: None, patch_theme: None) -> None:
    assert MetricometerRendererPerfometer(
        perfometers_api.Perfometer(
            name="name",
            focus_range=perfometers_api.FocusRange(
                perfometers_api.Closed(0), perfometers_api.Open(2500.0)
            ),
            segments=["metric-name1", "metric-name2"],
        ),
        {
            "metric-name1": TranslatedMetric(
                originals=[Original("metric-name1", 1.0)],
                value=1300.0,
                scalar={},
                auto_graph=True,
                title="Metric name 1",
                unit_spec=ConvertibleUnitSpecification(
                    notation=DecimalNotation(symbol=""),
                    precision=AutoPrecision(digits=2),
                ),
                color="#111111",
            ),
            "metric-name2": TranslatedMetric(
                originals=[Original("metric-name2", 1.0)],
                value=1300.0,
                scalar={},
                auto_graph=True,
                title="Metric name 2",
                unit_spec=ConvertibleUnitSpecification(
                    notation=DecimalNotation(symbol=""),
                    precision=AutoPrecision(digits=2),
                ),
                color="#222222",
            ),
        },
        "#bdbdbd",
    ).get_stack() == [[(42.63, "#111111"), (42.63, "#222222"), (14.74, "#bdbdbd")]]


@pytest.mark.parametrize(
    "segments, translated_metrics, stack, label",
    [
        pytest.param(
            ["metric-name"],
            {
                "metric-name": TranslatedMetric(
                    originals=[Original("metric-name", 1.0)],
                    value=101.0,
                    scalar=ScalarBounds(),
                    auto_graph=True,
                    title="Metric name",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#111111",
                ),
            },
            [[(100.0, "#111111"), (0.0, "#bdbdbd")]],
            "101",
            id="one-metric",
        ),
        pytest.param(
            ["metric-name1", "metric-name2"],
            {
                "metric-name1": TranslatedMetric(
                    originals=[Original("metric-name1", 1.0)],
                    value=99.0,
                    scalar=ScalarBounds(),
                    auto_graph=True,
                    title="Metric name 1",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#111111",
                ),
                "metric-name2": TranslatedMetric(
                    originals=[Original("metric-name2", 1.0)],
                    value=2.0,
                    scalar=ScalarBounds(),
                    auto_graph=True,
                    title="Metric name 2",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#111111",
                ),
            },
            [[(98.02, "#111111"), (1.98, "#111111"), (0.0, "#bdbdbd")]],
            "101",
            id="two-metrics",
        ),
    ],
)
def test_perfometer_renderer_exceeds_limit(
    segments: Sequence[
        str
        | metrics_api.Constant
        | metrics_api.WarningOf
        | metrics_api.CriticalOf
        | metrics_api.MinimumOf
        | metrics_api.MaximumOf
        | metrics_api.Sum
        | metrics_api.Product
        | metrics_api.Difference
        | metrics_api.Fraction
    ],
    translated_metrics: Mapping[str, TranslatedMetric],
    stack: Sequence[Sequence[tuple[float, str]]],
    label: str,
) -> None:
    metricometer = MetricometerRendererPerfometer(
        perfometers_api.Perfometer(
            name="name",
            focus_range=perfometers_api.FocusRange(
                perfometers_api.Closed(0), perfometers_api.Closed(100)
            ),
            segments=segments,
        ),
        translated_metrics,
        "#bdbdbd",
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
            ("dual", [("linear", ([], 100, "Label 2")), ("linear", ([], 100, "Label 3"))]),
            {
                "type": "dual",
                "perfometers": [
                    {"type": "linear", "segments": [], "total": 100, "label": "Label 2"},
                    {"type": "linear", "segments": [], "total": 100, "label": "Label 3"},
                ],
            },
            id="dual",
        ),
        pytest.param(
            ("stacked", [("linear", ([], 100, "Label 4")), ("linear", ([], 100, "Label 5"))]),
            {
                "type": "stacked",
                "perfometers": [
                    {"type": "linear", "segments": [], "total": 100, "label": "Label 4"},
                    {"type": "linear", "segments": [], "total": 100, "label": "Label 5"},
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
def test_parse_dual_or_stacked_perfometer_errors(legacy_perfometer: LegacyPerfometer) -> None:
    with pytest.raises(MKGeneralException):
        parse_perfometer(legacy_perfometer)
