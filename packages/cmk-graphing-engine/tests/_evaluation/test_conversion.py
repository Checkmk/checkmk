#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing_engine import (
    AutoPrecision,
    converted_graph,
    CurveAttributes,
    DecimalNotation,
    EvaluatedCurve,
    EvaluatedGraph,
    EvaluatedLine,
    EvaluatedVerticalRange,
    NonConvertibleUnit,
    TemperatureUnit,
    TimeRange,
    TimeSeries,
    Unit,
    VerticalRangeKind,
)

_RANGE = TimeRange(start=0, end=20, step=10)
_CELSIUS = Unit(notation=DecimalNotation("°C"), precision=AutoPrecision(2))


def _graph(unit: Unit) -> EvaluatedGraph:
    return EvaluatedGraph(
        name="temperature",
        title="Temperature",
        time_range=_RANGE,
        vertical_range=EvaluatedVerticalRange(
            range_kind=VerticalRangeKind.MINIMAL, lower=0.0, upper=100.0
        ),
        stacks=[],
        lines=[
            EvaluatedLine(
                curve=EvaluatedCurve(
                    id="t",
                    attributes=CurveAttributes(title="T", unit=unit, color="#000000"),
                    value=100.0,
                    time_series=TimeSeries(time_range=_RANGE, values=[0.0, None]),
                ),
                inverse=False,
            )
        ],
    )


def test_a_curve_converts_into_the_users_temperature_unit() -> None:
    [line] = converted_graph(_graph(_CELSIUS), TemperatureUnit.FAHRENHEIT, None).lines
    assert (line.curve.value, list(line.curve.time_series.values)) == (212.0, [32.0, None])


def test_the_vertical_range_converts_with_the_axis_unit() -> None:
    converted = converted_graph(_graph(_CELSIUS), TemperatureUnit.FAHRENHEIT, _CELSIUS)
    assert converted.vertical_range == EvaluatedVerticalRange(
        range_kind=VerticalRangeKind.MINIMAL, lower=32.0, upper=212.0
    )


def test_a_non_convertible_axis_unit_keeps_the_vertical_range() -> None:
    non_convertible = NonConvertibleUnit(notation=DecimalNotation("°C"), precision=AutoPrecision(2))
    converted = converted_graph(_graph(_CELSIUS), TemperatureUnit.FAHRENHEIT, non_convertible)
    assert converted.vertical_range == EvaluatedVerticalRange(
        range_kind=VerticalRangeKind.MINIMAL, lower=0.0, upper=100.0
    )
