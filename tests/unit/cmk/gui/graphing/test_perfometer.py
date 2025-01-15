#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import math
from collections.abc import Mapping, Sequence

import pytest

from cmk.gui.graphing import get_first_matching_perfometer
from cmk.gui.graphing._formatter import AutoPrecision
from cmk.gui.graphing._perfometer import (
    _make_projection,
    _PERFOMETER_PROJECTION_PARAMETERS,
    MetricometerRendererPerfometer,
)
from cmk.gui.graphing._translated_metrics import Original, ScalarBounds, TranslatedMetric
from cmk.gui.graphing._unit import ConvertibleUnitSpecification, DecimalNotation

from cmk.graphing.v1 import metrics as metrics_api
from cmk.graphing.v1 import perfometers as perfometers_api


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
