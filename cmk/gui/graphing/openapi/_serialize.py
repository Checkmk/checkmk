#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Callable
from typing import assert_never

from cmk.graphing_engine import (
    ConsolidationFunction,
    EvaluatedCurve,
    EvaluatedGraph,
    SeriesAttributes,
    TimeSeries,
    Unit,
)
from cmk.graphing_engine import TimeRange as EngineTimeRange
from cmk.gui.i18n import _
from cmk.gui.utils.temperature_unit import TemperatureUnit

from .._drawn_curves import DrawnCurve, serialize_drawn_curves
from .._source import FetchDiagnostics
from .._unit_format import apply_temperature_unit, unit_to_unit_format
from .models import (
    ApiConsolidation,
    ApiHorizontalLine,
    ApiMetric,
    ApiMetricAttribute,
    ApiMetricMetadata,
    ApiMetricRender,
    ApiRegionBounds,
    ApiShadedRegion,
    ApiTimeRange,
    ApiUnitFormat,
    GraphFetchResponse,
)


def api_consolidation_to_engine(value: ApiConsolidation) -> ConsolidationFunction:
    match value:
        case "min":
            return ConsolidationFunction.MIN
        case "max":
            return ConsolidationFunction.MAX
        case "avg":
            return ConsolidationFunction.AVERAGE
    assert_never(value)


def api_time_range_to_engine(time_range: ApiTimeRange) -> EngineTimeRange:
    return EngineTimeRange(start=time_range.start, end=time_range.end, step=time_range.step)


def api_time_range_from_engine(time_range: EngineTimeRange) -> ApiTimeRange:
    return ApiTimeRange(start=time_range.start, end=time_range.end, step=time_range.step)


def _api_unit_and_conversion(
    unit: Unit, temperature_unit: TemperatureUnit
) -> tuple[ApiUnitFormat, Callable[[float], float]]:
    """The unit to label the response with, and the converter its values must go through."""
    unit_format, conversion = apply_temperature_unit(unit_to_unit_format(unit), temperature_unit)
    return ApiUnitFormat.from_shared(unit_format), conversion


def horizontal_lines_to_api(
    evaluated: EvaluatedGraph, temperature_unit: TemperatureUnit
) -> list[ApiHorizontalLine]:
    lines: list[ApiHorizontalLine] = []
    for rule in evaluated.rules:
        unit, conversion = _api_unit_and_conversion(rule.attributes.unit, temperature_unit)
        # Converted before mirroring: conversion belongs to the value, the sign to the drawing.
        value = conversion(rule.value)
        lines.append(
            ApiHorizontalLine(
                name=rule.id,
                title=rule.attributes.title,
                value=-value if rule.inverse else value,
                unit=unit,
                color=rule.attributes.color,
            )
        )
    return lines


def _converted_bound(
    bound: TimeSeries | None, conversion: Callable[[float], float]
) -> list[float | None] | None:
    if bound is None:
        return None
    return [None if value is None else conversion(value) for value in bound.values]


def shaded_regions_to_api(
    evaluated: EvaluatedGraph, temperature_unit: TemperatureUnit
) -> list[ApiShadedRegion]:
    regions = []
    for region in evaluated.regions:
        # A region is drawn against the same axis as the curves, so it converts with them.
        _unit, conversion = _api_unit_and_conversion(region.attributes.unit, temperature_unit)
        regions.append(
            ApiShadedRegion(
                name=region.id,
                title=region.attributes.title,
                color=region.attributes.color,
                data_points=ApiRegionBounds(
                    lower=_converted_bound(region.lower, conversion),
                    upper=_converted_bound(region.upper, conversion),
                ),
            )
        )
    return regions


def _series_attributes_to_api(attributes: SeriesAttributes) -> list[ApiMetricAttribute]:
    # Flattened into one entry per attribute so the order the response carries is stable: the kinds
    # in the order the fetch layer grouped them, each kind's attributes sorted by name.
    return [
        ApiMetricAttribute(kind=kind, name=name, value=value)
        for kind, of_kind in attributes.items()
        for name, value in sorted(of_kind.items())
    ]


def curve_to_api_metric(
    drawn: DrawnCurve[EvaluatedCurve], temperature_unit: TemperatureUnit
) -> ApiMetric:
    curve = drawn.curve
    unit, conversion = _api_unit_and_conversion(curve.attributes.unit, temperature_unit)
    return ApiMetric(
        metadata=ApiMetricMetadata(
            name=curve.id,
            title=curve.attributes.title,
            unit=unit,
            color=curve.attributes.color,
            attributes=_series_attributes_to_api(curve.series_attributes),
        ),
        render=ApiMetricRender(stack=drawn.stack, inverse=drawn.mirrored, hidden=drawn.hidden),
        data_points=[
            None if value is None else conversion(value) for value in curve.time_series.values
        ],
    )


def diagnostics_to_warnings(diagnostics: FetchDiagnostics) -> list[str]:
    return [
        _(
            "The query for '%(metric)s' matched more than %(max)d time series, so the result "
            "is truncated. Please narrow down the query."
        )
        % {"metric": limit.metric_name, "max": limit.max_series}
        for limit in diagnostics.limits_reached
    ]


def evaluated_to_response(
    evaluated: EvaluatedGraph,
    *,
    fallback_time_range: EngineTimeRange,
    diagnostics: FetchDiagnostics,
    temperature_unit: TemperatureUnit,
) -> GraphFetchResponse:
    time_range, metrics = serialize_drawn_curves(
        evaluated,
        lambda drawn: curve_to_api_metric(drawn, temperature_unit),
        fallback_time_range=fallback_time_range,
        include_reference=True,
    )
    return GraphFetchResponse(
        title=evaluated.title,
        time_range=api_time_range_from_engine(time_range),
        metrics=metrics,
        horizontal_lines=horizontal_lines_to_api(evaluated, temperature_unit),
        shaded_regions=shaded_regions_to_api(evaluated, temperature_unit),
        warnings=diagnostics_to_warnings(diagnostics),
        errors=list(diagnostics.errors),
    )
