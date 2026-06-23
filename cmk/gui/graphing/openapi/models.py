#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping
from typing import Annotated, Literal

from pydantic import Json

from cmk.gui.openapi.framework.model import api_field, api_model


@api_model
class ApiPrecision:
    type: Literal["auto", "strict"] = api_field(
        description="The precision rounding mode.", example="auto"
    )
    digits: int = api_field(description="The number of digits.", example=2)


@api_model
class ApiUnitFormat:
    notation: Literal[
        "decimal", "si", "iec", "standard_scientific", "engineering_scientific", "time"
    ] = api_field(description="The unit notation.", example="decimal")
    symbol: str = api_field(description="The unit symbol.", example="B")
    precision: ApiPrecision = api_field(description="The unit precision.")
    convertible: bool = api_field(description="Whether the unit is auto-convertible.", example=True)


@api_model
class ApiTimeRange:
    start: int = api_field(description="The start timestamp (epoch seconds).", example=1700000000)
    end: int = api_field(description="The end timestamp (epoch seconds).", example=1700003600)
    step: int = api_field(description="The step size in seconds.", example=60)


@api_model
class ApiMetricMetadata:
    name: str = api_field(
        description="The stable structural identifier of the metric.",
        example="<implementation detail>",
    )
    title: str = api_field(
        description="The metric title.",
        example="CPU utilization",
    )
    unit: ApiUnitFormat = api_field(description="The metric unit.")
    color: str = api_field(description="The metric color.", example="#ff0000")


@api_model
class ApiMetricRender:
    stack: str | None = api_field(
        description="The stack group id. None = line; unique id = area; shared id = stacked.",
        example="stack-0",
    )
    inverse: bool = api_field(description="Whether the metric is mirrored.", example=False)
    hidden: bool = api_field(
        description="Whether the metric is drawn (used for stack baselines).", example=False
    )


@api_model
class ApiMetric:
    metadata: ApiMetricMetadata = api_field(description="The metric metadata.")
    render: ApiMetricRender = api_field(description="The metric rendering options.")
    data_points: list[float | None] | None = api_field(
        description="The data points. None when unfetched; an array (possibly with nulls) otherwise.",
        example=[1.0, 2.5, None, 3.0],
    )


@api_model
class ApiHorizontalLine:
    name: str = api_field(
        description="The stable structural identifier of the horizontal line.",
        example="<implementation detail>",
    )
    value: float = api_field(description="The horizontal line value.", example=80.0)
    color: str = api_field(description="The horizontal line color.", example="#ffcc00")


@api_model
class GraphFetchRequest:
    graph_type: str = api_field(
        description="The graph type, selecting the engine evaluator.", example="template"
    )
    internal: Annotated[Mapping[str, object], Json] = api_field(
        description="The self-contained graph definition needed to recompute the data, as JSON.",
        example="<implementation detail>",
    )
    requested_time_range: ApiTimeRange = api_field(
        description="The time range (and step) to fetch data for. The returned range may differ.",
    )
    consolidation_function: Literal["min", "max", "avg"] = api_field(
        description="The consolidation function to use for RRD data.", example="avg"
    )


@api_model
class GraphFetchResponse:
    time_range: ApiTimeRange = api_field(
        description="The actual time range the returned data covers (may differ from the request).",
    )
    metrics: list[ApiMetric] = api_field(description="The new metrics.")
    horizontal_lines: list[ApiHorizontalLine] = api_field(description="The new horizontal lines.")
