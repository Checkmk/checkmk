#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import math
from collections.abc import Mapping, Sequence

import pytest

from cmk.graphing.v1 import metrics as metrics_api
from cmk.graphing.v1 import perfometers as perfometers_api
from cmk.gui.graphing._perfometer import (
    _ArcTan,
    _get_first_matching_perfometer_testable,
    _make_projection,
    MetricometerRendererPerfometer,
    MetricometerRendererStacked,
)
from cmk.gui.graphing._translated_metrics import (
    Original,
    ScalarBounds,
    TranslatedMetric,
)
from cmk.gui.graphing._unit import ConvertibleUnitSpecification, DecimalNotation
from cmk.gui.unit_formatter import AutoPrecision
from cmk.gui.utils.temperate_unit import TemperatureUnit


@pytest.mark.usefixtures("request_context")
def test_get_first_matching_perfometer_testable_without_superseding() -> None:
    assert (
        first_renderer := _get_first_matching_perfometer_testable(
            {
                "active_connections": TranslatedMetric(
                    originals=[Original("active_connections", 1.0)],
                    value=1.0,
                    scalar=ScalarBounds(),
                    auto_graph=True,
                    title="Active connections",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#111111",
                ),
            },
            {},
            {
                "active_connections": perfometers_api.Perfometer(
                    name="active_connections",
                    focus_range=perfometers_api.FocusRange(
                        perfometers_api.Closed(0),
                        perfometers_api.Open(90),
                    ),
                    segments=["active_connections"],
                )
            },
            {},
        )
    ) is not None
    assert first_renderer.perfometer == perfometers_api.Perfometer(
        name="active_connections",
        focus_range=perfometers_api.FocusRange(
            lower=perfometers_api.Closed(0),
            upper=perfometers_api.Open(90),
        ),
        segments=["active_connections"],
    )


@pytest.mark.usefixtures("request_context")
def test_get_first_matching_perfometer_testable_with_superseding() -> None:
    assert (
        first_renderer := _get_first_matching_perfometer_testable(
            {
                "active_connections": TranslatedMetric(
                    originals=[Original("active_connections", 1.0)],
                    value=1.0,
                    scalar=ScalarBounds(),
                    auto_graph=True,
                    title="Active connections",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#111111",
                ),
            },
            {},
            {
                "active_connections": perfometers_api.Perfometer(
                    name="active_connections",
                    focus_range=perfometers_api.FocusRange(
                        perfometers_api.Closed(0),
                        perfometers_api.Open(90),
                    ),
                    segments=["active_connections"],
                ),
                "active_connections_better": perfometers_api.Perfometer(
                    name="active_connections_better",
                    focus_range=perfometers_api.FocusRange(
                        perfometers_api.Closed(0),
                        perfometers_api.Open(90),
                    ),
                    segments=["active_connections"],
                ),
            },
            {"active_connections": "active_connections_better"},
        )
    ) is not None
    assert first_renderer.perfometer == perfometers_api.Perfometer(
        name="active_connections_better",
        focus_range=perfometers_api.FocusRange(
            lower=perfometers_api.Closed(0),
            upper=perfometers_api.Open(90),
        ),
        segments=["active_connections"],
    )


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
        {},
        focus_range,
        MetricometerRendererPerfometer._PROJECTION_PARAMETERS,
        {},
        "name",
        temperature_unit=TemperatureUnit.CELSIUS,
    )
    assert math.isnan(projection.start_of_focus_range)
    assert math.isnan(projection.end_of_focus_range)
    assert math.isnan(projection(projection.start_of_focus_range - 10))
    assert math.isnan((projection.start_of_focus_range + projection.end_of_focus_range) / 2)
    assert math.isnan(projection(projection.end_of_focus_range + 10))


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
        {},
        perfometers_api.FocusRange(perfometers_api.Closed(-10), perfometers_api.Closed(20)),
        MetricometerRendererPerfometer._PROJECTION_PARAMETERS,
        {},
        "name",
        temperature_unit=TemperatureUnit.CELSIUS,
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
        {},
        perfometers_api.FocusRange(perfometers_api.Closed(-10), perfometers_api.Closed(20)),
        MetricometerRendererPerfometer._PROJECTION_PARAMETERS,
        {},
        "name",
        temperature_unit=TemperatureUnit.CELSIUS,
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
        {},
        perfometers_api.FocusRange(perfometers_api.Open(-10), perfometers_api.Closed(20)),
        MetricometerRendererPerfometer._PROJECTION_PARAMETERS,
        {},
        "name",
        temperature_unit=TemperatureUnit.CELSIUS,
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
        {},
        perfometers_api.FocusRange(perfometers_api.Open(-10), perfometers_api.Closed(20)),
        MetricometerRendererPerfometer._PROJECTION_PARAMETERS,
        {},
        "name",
        temperature_unit=TemperatureUnit.CELSIUS,
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
        {},
        perfometers_api.FocusRange(perfometers_api.Closed(-10), perfometers_api.Open(20)),
        MetricometerRendererPerfometer._PROJECTION_PARAMETERS,
        {},
        "name",
        temperature_unit=TemperatureUnit.CELSIUS,
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
        {},
        perfometers_api.FocusRange(perfometers_api.Closed(-10), perfometers_api.Open(20)),
        MetricometerRendererPerfometer._PROJECTION_PARAMETERS,
        {},
        "name",
        temperature_unit=TemperatureUnit.CELSIUS,
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
        {},
        perfometers_api.FocusRange(perfometers_api.Open(-10), perfometers_api.Open(20)),
        MetricometerRendererPerfometer._PROJECTION_PARAMETERS,
        {},
        "name",
        temperature_unit=TemperatureUnit.CELSIUS,
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
                    scalar=ScalarBounds(),
                    auto_graph=True,
                    title="Metric name 1",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#111111",
                ),
            },
            [(88.27, "#111111")],
            id="one-metric",
        ),
        pytest.param(
            ["metric-name1", "metric-name2"],
            {
                "metric-name1": TranslatedMetric(
                    originals=[Original("metric-name1", 1.0)],
                    value=2000.0,
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
                    value=600.0,
                    scalar=ScalarBounds(),
                    auto_graph=True,
                    title="Metric name 2",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#222222",
                ),
            },
            [(67.9, "#111111"), (20.37, "#222222")],
            id="two-metrics",
        ),
        pytest.param(
            ["metric-name1", "metric-name2", "metric-name3"],
            {
                "metric-name1": TranslatedMetric(
                    originals=[Original("metric-name1", 1.0)],
                    value=2000.0,
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
                    value=400.0,
                    scalar=ScalarBounds(),
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
                    scalar=ScalarBounds(),
                    auto_graph=True,
                    title="Metric name 3",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#333333",
                ),
            },
            [(67.9, "#111111"), (13.58, "#222222"), (6.79, "#333333")],
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
    patch_theme: None,
) -> None:
    assert MetricometerRendererPerfometer(
        {},
        perfometers_api.Perfometer(
            name="name",
            focus_range=perfometers_api.FocusRange(
                perfometers_api.Closed(0), perfometers_api.Open(2500.0)
            ),
            segments=segments,
        ),
        translated_metrics,
        "#bdbdbd",
    ).get_stack(TemperatureUnit.CELSIUS) == [list(value_projections) + [(11.73, "#bdbdbd")]]


def test_perfometer_renderer_stack_same_values(patch_theme: None) -> None:
    assert MetricometerRendererPerfometer(
        {},
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
                value=1300.0,
                scalar=ScalarBounds(),
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
    ).get_stack(TemperatureUnit.CELSIUS) == [
        [(44.13, "#111111"), (44.13, "#222222"), (11.74, "#bdbdbd")]
    ]


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
        {},
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
    assert metricometer.get_stack(TemperatureUnit.CELSIUS) == stack
    assert metricometer.get_label(TemperatureUnit.CELSIUS) == label


def test_metricometer_renderer_stacked(request_context: None, patch_theme: None) -> None:
    metricometer = MetricometerRendererStacked(
        {},
        perfometers_api.Stacked(
            name="stacked",
            lower=perfometers_api.Perfometer(
                name="lower",
                focus_range=perfometers_api.FocusRange(
                    lower=perfometers_api.Closed(0),
                    upper=perfometers_api.Open(10),
                ),
                segments=["metric_1"],
            ),
            upper=perfometers_api.Perfometer(
                name="upper",
                focus_range=perfometers_api.FocusRange(
                    lower=perfometers_api.Closed(0),
                    upper=perfometers_api.Open(10),
                ),
                segments=["metric_2"],
            ),
        ),
        {
            "metric_1": TranslatedMetric(
                originals=[Original("metric_1", 1.0)],
                value=2.0,
                scalar=ScalarBounds(),
                auto_graph=True,
                title="Metric 1",
                unit_spec=ConvertibleUnitSpecification(
                    notation=DecimalNotation(symbol=""),
                    precision=AutoPrecision(digits=2),
                ),
                color="#111111",
            ),
            "metric_2": TranslatedMetric(
                originals=[Original("metric_2", 1.0)],
                value=7.0,
                scalar=ScalarBounds(),
                auto_graph=True,
                title="Metric 2",
                unit_spec=ConvertibleUnitSpecification(
                    notation=DecimalNotation(symbol=""),
                    precision=AutoPrecision(digits=2),
                ),
                color="#111111",
            ),
        },
    )
    assert metricometer.get_stack(TemperatureUnit.CELSIUS) == [
        [(59.5, "#111111"), (40.5, "#bdbdbd")],
        [(17.0, "#111111"), (83.0, "#bdbdbd")],
    ]
    assert metricometer.get_label(TemperatureUnit.CELSIUS) == "7 / 2"


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
