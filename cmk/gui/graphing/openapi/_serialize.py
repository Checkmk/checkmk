#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import assert_never, Literal

from cmk.graphing_engine import (
    AutoPrecision,
    DecimalNotation,
    EngineeringScientificNotation,
    EvaluatedCurve,
    EvaluatedGraph,
    IECNotation,
    SINotation,
    StandardScientificNotation,
    StrictPrecision,
    TimeNotation,
    Unit,
)
from cmk.graphing_engine import TimeRange as EngineTimeRange

from .models import (
    ApiHorizontalLine,
    ApiMetric,
    ApiMetricMetadata,
    ApiMetricRender,
    ApiPrecision,
    ApiTimeRange,
    ApiUnitFormat,
    GraphFetchResponse,
)


def evaluated_to_response(
    evaluated: EvaluatedGraph, *, fallback_time_range: EngineTimeRange
) -> GraphFetchResponse:
    """Map the evaluated graph to the data-only response (metrics, horizontal lines, resampled range)."""
    metrics: list[ApiMetric] = []
    data_time_range: EngineTimeRange | None = None

    for index, stack in enumerate(evaluated.stacks):
        stack_id = f"stack-{index}"
        # The reference (invisible baseline) is emitted first so it is the stacking floor by order.
        if stack.reference is not None:
            metrics.append(
                _curve_to_api_metric(
                    stack.reference, stack=stack_id, inverse=stack.inverse, hidden=True
                )
            )
            data_time_range = data_time_range or stack.reference.time_series.time_range
        for member in stack.members:
            metrics.append(
                _curve_to_api_metric(member, stack=stack_id, inverse=stack.inverse, hidden=False)
            )
            data_time_range = data_time_range or member.time_series.time_range

    for line in evaluated.lines:
        metrics.append(
            _curve_to_api_metric(line.curve, stack=None, inverse=line.inverse, hidden=False)
        )
        data_time_range = data_time_range or line.curve.time_series.time_range

    horizontal_lines = [
        ApiHorizontalLine(
            name=rule.id,
            value=-rule.value if rule.inverse else rule.value,
            color=rule.attributes.color,
        )
        for rule in evaluated.rules
    ]

    effective_range = fallback_time_range if data_time_range is None else data_time_range
    return GraphFetchResponse(
        time_range=ApiTimeRange(
            start=effective_range.start,
            end=effective_range.end,
            step=effective_range.step,
        ),
        metrics=metrics,
        horizontal_lines=horizontal_lines,
    )


def _curve_to_api_metric(
    curve: EvaluatedCurve, *, stack: str | None, inverse: bool, hidden: bool
) -> ApiMetric:
    return ApiMetric(
        metadata=ApiMetricMetadata(
            name=curve.id,
            title=curve.attributes.title,
            unit=unit_to_api_unit_format(curve.attributes.unit),
            color=curve.attributes.color,
        ),
        render=ApiMetricRender(stack=stack, inverse=inverse, hidden=hidden),
        data_points=list(curve.time_series.values),
    )


def unit_to_api_unit_format(unit: Unit) -> ApiUnitFormat:
    notation: Literal[
        "decimal", "si", "iec", "standard_scientific", "engineering_scientific", "time"
    ]
    match unit.notation:
        case DecimalNotation():
            notation = "decimal"
        case SINotation():
            notation = "si"
        case IECNotation():
            notation = "iec"
        case StandardScientificNotation():
            notation = "standard_scientific"
        case EngineeringScientificNotation():
            notation = "engineering_scientific"
        case TimeNotation():
            notation = "time"
        case _:
            assert_never(unit.notation)

    match unit.precision:
        case AutoPrecision():
            precision = ApiPrecision(type="auto", digits=unit.precision.digits)
        case StrictPrecision():
            precision = ApiPrecision(type="strict", digits=unit.precision.digits)
        case _:
            assert_never(unit.precision)

    # TODO: The engine ``Unit`` has no convertibility concept, so default to convertible (matches
    #  the shared unit-format default).
    return ApiUnitFormat(
        notation=notation, symbol=unit.notation.symbol, precision=precision, convertible=True
    )
