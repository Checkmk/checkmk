#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import assert_never

from cmk.graphing_engine import (
    ConsolidationFunction,
    converted_graph,
    drawn_curves,
    DrawnCurve,
    EvaluatedCurve,
    EvaluatedGraph,
    SeriesAttributes,
    TimeSeries,
    Unit,
)
from cmk.graphing_engine import TimeRange as EngineTimeRange
from cmk.gui.i18n import _
from cmk.gui.utils.temperature_unit import TemperatureUnit

from .._source import FetchDiagnostics
from .._user_specific_unit import user_unit_format
from .models import (
    ApiAreaRender,
    ApiConsolidation,
    ApiHorizontalLine,
    ApiLineRender,
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


def _api_unit(unit: Unit, temperature_unit: TemperatureUnit) -> ApiUnitFormat:
    unit_format, _conversion = user_unit_format(unit, temperature_unit)
    return ApiUnitFormat.from_shared(unit_format)


def horizontal_lines_to_api(
    converted: EvaluatedGraph, temperature_unit: TemperatureUnit
) -> list[ApiHorizontalLine]:
    lines: list[ApiHorizontalLine] = []
    for rule in converted.rules:
        lines.append(
            ApiHorizontalLine(
                name=rule.id,
                title=rule.attributes.title,
                value=-rule.value if rule.inverse else rule.value,
                unit=_api_unit(rule.attributes.unit, temperature_unit),
                color=rule.attributes.color,
            )
        )
    return lines


def _bound_values(bound: TimeSeries | None) -> list[float | None] | None:
    return None if bound is None else list(bound.values)


def shaded_regions_to_api(converted: EvaluatedGraph) -> list[ApiShadedRegion]:
    regions = []
    for region in converted.regions:
        regions.append(
            ApiShadedRegion(
                name=region.id,
                title=region.attributes.title,
                color=region.attributes.color,
                data_points=ApiRegionBounds(
                    lower=_bound_values(region.lower),
                    upper=_bound_values(region.upper),
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


def _render_to_api(drawn: DrawnCurve[EvaluatedCurve]) -> ApiMetricRender:
    if drawn.stack is None:
        return ApiLineRender(shape="line", inverse=drawn.mirrored, hidden=False)
    return ApiAreaRender(shape="area", stack=drawn.stack, inverse=drawn.mirrored, hidden=False)


def curve_to_api_metric(
    drawn: DrawnCurve[EvaluatedCurve], temperature_unit: TemperatureUnit
) -> ApiMetric:
    curve = drawn.curve
    return ApiMetric(
        metadata=ApiMetricMetadata(
            name=curve.id,
            title=curve.attributes.title,
            unit=_api_unit(curve.attributes.unit, temperature_unit),
            color=curve.attributes.color,
            attributes=_series_attributes_to_api(curve.series_attributes),
        ),
        render=_render_to_api(drawn),
        data_points=list(curve.time_series.values),
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
    diagnostics: FetchDiagnostics,
    temperature_unit: TemperatureUnit,
) -> GraphFetchResponse:
    converted = converted_graph(evaluated, temperature_unit, None)
    return GraphFetchResponse(
        title=converted.title,
        time_range=api_time_range_from_engine(converted.time_range),
        metrics=[
            curve_to_api_metric(drawn, temperature_unit)
            for drawn in drawn_curves(converted.stacks, converted.lines)
        ],
        horizontal_lines=horizontal_lines_to_api(converted, temperature_unit),
        shaded_regions=shaded_regions_to_api(converted),
        warnings=diagnostics_to_warnings(diagnostics),
        errors=list(diagnostics.errors),
    )
