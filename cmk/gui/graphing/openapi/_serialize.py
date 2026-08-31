#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import assert_never, NamedTuple, Protocol

from cmk.graphing_engine import (
    ConsolidationFunction,
    EvaluatedCurve,
    EvaluatedGraph,
    SeriesAttributes,
    Unit,
)
from cmk.graphing_engine import TimeRange as EngineTimeRange
from cmk.gui.i18n import _

from .._engine_source import FetchDiagnostics
from .._engine_unit_format import notation_name, precision_kind
from .models import (
    ApiConsolidation,
    ApiHorizontalLine,
    ApiMetric,
    ApiMetricAttribute,
    ApiMetricMetadata,
    ApiMetricRender,
    ApiPrecision,
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


class _ToMetric[MetricT](Protocol):
    def __call__(
        self, curve: EvaluatedCurve, *, stack: str | None, inverse: bool, hidden: bool
    ) -> MetricT: ...


class SerializedCurves[MetricT](NamedTuple):
    time_range: ApiTimeRange
    metrics: list[MetricT]


def serialize_curves[MetricT](
    evaluated: EvaluatedGraph,
    to_metric: _ToMetric[MetricT],
    *,
    fallback_time_range: EngineTimeRange,
) -> SerializedCurves[MetricT]:
    metrics: list[MetricT] = []
    data_time_range: EngineTimeRange | None = None

    def add(curve: EvaluatedCurve, *, stack: str | None, inverse: bool, hidden: bool) -> None:
        nonlocal data_time_range
        if data_time_range is None:
            data_time_range = curve.time_series.time_range
        metrics.append(to_metric(curve, stack=stack, inverse=inverse, hidden=hidden))

    for index, stack in enumerate(evaluated.stacks):
        stack_id = f"stack-{index}"
        # The reference (invisible baseline) is emitted first so it is the stacking floor by order.
        if stack.reference is not None:
            add(stack.reference, stack=stack_id, inverse=stack.inverse, hidden=True)
        for member in stack.members:
            add(member, stack=stack_id, inverse=stack.inverse, hidden=False)
    for line in evaluated.lines:
        add(line.curve, stack=None, inverse=line.inverse, hidden=False)

    effective = fallback_time_range if data_time_range is None else data_time_range
    return SerializedCurves(
        ApiTimeRange(start=effective.start, end=effective.end, step=effective.step), metrics
    )


def horizontal_lines_to_api(evaluated: EvaluatedGraph) -> list[ApiHorizontalLine]:
    return [
        ApiHorizontalLine(
            name=rule.id,
            title=rule.attributes.title,
            value=-rule.value if rule.inverse else rule.value,
            unit=unit_to_api_unit_format(rule.attributes.unit),
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


def curve_to_api_metric(
    curve: EvaluatedCurve, *, stack: str | None, inverse: bool, hidden: bool
) -> ApiMetric:
    return ApiMetric(
        metadata=ApiMetricMetadata(
            name=curve.id,
            title=curve.attributes.title,
            unit=unit_to_api_unit_format(curve.attributes.unit),
            color=curve.attributes.color,
            attributes=_series_attributes_to_api(curve.series_attributes),
        ),
        render=ApiMetricRender(stack=stack, inverse=inverse, hidden=hidden),
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
    time_range, metrics = serialize_curves(
        evaluated, curve_to_api_metric, fallback_time_range=fallback_time_range
    )
    return GraphFetchResponse(
        title=evaluated.title,
        time_range=time_range,
        metrics=metrics,
        horizontal_lines=horizontal_lines_to_api(evaluated),
        warnings=diagnostics_to_warnings(diagnostics),
        errors=list(diagnostics.errors),
    )


def unit_to_api_unit_format(unit: Unit) -> ApiUnitFormat:
    # TODO: The engine ``Unit`` has no convertibility concept, so default to convertible (matches
    #  the shared unit-format default).
    return ApiUnitFormat(
        notation=notation_name(unit),
        symbol=unit.notation.symbol,
        precision=ApiPrecision(type=precision_kind(unit), digits=unit.precision.digits),
        convertible=True,
    )
