#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import assert_never

from cmk.graphing_engine import (
    ConsolidationFunction,
    EvaluatedCurve,
    EvaluatedGraph,
    SeriesAttributes,
)
from cmk.graphing_engine import TimeRange as EngineTimeRange
from cmk.gui.i18n import _

from .._engine_curves import DrawnCurve, serialize_drawn_curves
from .._engine_source import FetchDiagnostics
from .models import (
    ApiConsolidation,
    ApiHorizontalLine,
    ApiMetric,
    ApiMetricAttribute,
    ApiMetricMetadata,
    ApiMetricRender,
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


def horizontal_lines_to_api(evaluated: EvaluatedGraph) -> list[ApiHorizontalLine]:
    return [
        ApiHorizontalLine(
            name=rule.id,
            title=rule.attributes.title,
            value=-rule.value if rule.inverse else rule.value,
            unit=ApiUnitFormat.from_engine_unit(rule.attributes.unit),
            color=rule.attributes.color,
        )
        for rule in evaluated.rules
    ]


def _series_attributes_to_api(attributes: SeriesAttributes) -> list[ApiMetricAttribute]:
    # Flattened into one entry per attribute so the order the response carries is stable: the kinds
    # in the order the fetch layer grouped them, each kind's attributes sorted by name.
    return [
        ApiMetricAttribute(kind=kind, name=name, value=value)
        for kind, of_kind in attributes.items()
        for name, value in sorted(of_kind.items())
    ]


def curve_to_api_metric(drawn: DrawnCurve[EvaluatedCurve]) -> ApiMetric:
    curve = drawn.curve
    return ApiMetric(
        metadata=ApiMetricMetadata(
            name=curve.id,
            title=curve.attributes.title,
            unit=ApiUnitFormat.from_engine_unit(curve.attributes.unit),
            color=curve.attributes.color,
            attributes=_series_attributes_to_api(curve.series_attributes),
        ),
        render=ApiMetricRender(stack=drawn.stack, inverse=drawn.mirrored, hidden=drawn.hidden),
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
    fallback_time_range: EngineTimeRange,
    diagnostics: FetchDiagnostics,
) -> GraphFetchResponse:
    time_range, metrics = serialize_drawn_curves(
        evaluated,
        curve_to_api_metric,
        fallback_time_range=fallback_time_range,
        include_reference=True,
    )
    return GraphFetchResponse(
        title=evaluated.title,
        time_range=api_time_range_from_engine(time_range),
        metrics=metrics,
        horizontal_lines=horizontal_lines_to_api(evaluated),
        warnings=diagnostics_to_warnings(diagnostics),
        errors=list(diagnostics.errors),
    )
