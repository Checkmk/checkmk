#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable

from cmk.graphing_engine._data._temperature import (
    TemperatureUnit,
    unit_conversion,
)
from cmk.graphing_engine._data._timeseries import mapped_series
from cmk.graphing_engine._data._units import (
    CurveAttributes,
    NonConvertibleUnit,
    notation_from_name,
    notation_name,
    Unit,
)

from ._graph_evaluation import (
    EvaluatedCurve,
    EvaluatedGraph,
    EvaluatedLine,
    EvaluatedRegion,
    EvaluatedRule,
    EvaluatedStack,
    EvaluatedVerticalRange,
)


def _converted_attributes(attributes: CurveAttributes, symbol: str) -> CurveAttributes:
    return CurveAttributes(
        title=attributes.title,
        unit=Unit(
            notation=notation_from_name(notation_name(attributes.unit.notation), symbol),
            precision=attributes.unit.precision,
        ),
        color=attributes.color,
    )


def _converted_curve(curve: EvaluatedCurve, temperature_unit: TemperatureUnit) -> EvaluatedCurve:
    conversion = unit_conversion(curve.attributes.unit, temperature_unit)
    return EvaluatedCurve(
        id=curve.id,
        attributes=_converted_attributes(curve.attributes, conversion.symbol),
        value=None if curve.value is None else conversion.converter(curve.value),
        time_series=mapped_series(curve.time_series, conversion.converter),
        source_id=curve.source_id,
        series_attributes=curve.series_attributes,
    )


def _converted_stack(stack: EvaluatedStack, temperature_unit: TemperatureUnit) -> EvaluatedStack:
    return EvaluatedStack(
        members=[_converted_curve(member, temperature_unit) for member in stack.members],
        inverse=stack.inverse,
    )


def _converted_rule(rule: EvaluatedRule, temperature_unit: TemperatureUnit) -> EvaluatedRule:
    conversion = unit_conversion(rule.attributes.unit, temperature_unit)
    return EvaluatedRule(
        id=rule.id,
        attributes=_converted_attributes(rule.attributes, conversion.symbol),
        value=conversion.converter(rule.value),
        inverse=rule.inverse,
    )


def _converted_region(
    region: EvaluatedRegion, temperature_unit: TemperatureUnit
) -> EvaluatedRegion:
    conversion = unit_conversion(region.attributes.unit, temperature_unit)
    return EvaluatedRegion(
        id=region.id,
        attributes=_converted_attributes(region.attributes, conversion.symbol),
        lower=None if region.lower is None else mapped_series(region.lower, conversion.converter),
        upper=None if region.upper is None else mapped_series(region.upper, conversion.converter),
    )


def _converted_vertical_range(
    vertical_range: EvaluatedVerticalRange | None, conversion: Callable[[float], float]
) -> EvaluatedVerticalRange | None:
    if vertical_range is None:
        return None
    return EvaluatedVerticalRange(
        range_kind=vertical_range.range_kind,
        lower=None if vertical_range.lower is None else conversion(vertical_range.lower),
        upper=None if vertical_range.upper is None else conversion(vertical_range.upper),
    )


def converted_graph(
    graph: EvaluatedGraph,
    temperature_unit: TemperatureUnit,
    axis_unit: Unit | NonConvertibleUnit | None,
) -> EvaluatedGraph:
    return EvaluatedGraph(
        name=graph.name,
        title=graph.title,
        time_range=graph.time_range,
        vertical_range=_converted_vertical_range(
            graph.vertical_range,
            (lambda value: value)
            if axis_unit is None
            else unit_conversion(axis_unit, temperature_unit).converter,
        ),
        stacks=[_converted_stack(stack, temperature_unit) for stack in graph.stacks],
        lines=[
            EvaluatedLine(
                curve=_converted_curve(line.curve, temperature_unit), inverse=line.inverse
            )
            for line in graph.lines
        ],
        rules=[_converted_rule(rule, temperature_unit) for rule in graph.rules],
        regions=[_converted_region(region, temperature_unit) for region in graph.regions],
    )
