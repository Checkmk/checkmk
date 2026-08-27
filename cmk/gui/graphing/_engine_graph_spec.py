#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The graph spec the metric endpoints and the browser's JSON export answer with."""

from collections.abc import Mapping, Sequence
from typing import Final, TypedDict

from cmk.graphing_engine import EvaluatedCurve, EvaluatedGraph, SeriesAttributes
from cmk.graphing_engine import TimeRange as EngineTimeRange

from ._engine_curves import DrawnCurve, line_type_with_mirroring, serialize_drawn_curves
from ._graph_metric_expressions import AttributeGroup, LineType

_ATTRIBUTE_GROUPS: Final[tuple[AttributeGroup, ...]] = ("resource", "scope", "data_point")


class Curve(TypedDict):
    line_type: LineType
    color: str
    title: str
    attributes: Mapping[AttributeGroup, Mapping[str, str]]
    rrddata: Sequence[float | None]


class GraphSpec(TypedDict):
    start_time: int
    end_time: int
    step: int
    curves: Sequence[Curve]


def _attributes(
    series_attributes: SeriesAttributes,
) -> Mapping[AttributeGroup, Mapping[str, str]]:
    return {
        group: series_attributes[group] for group in _ATTRIBUTE_GROUPS if group in series_attributes
    }


def _curve(drawn: DrawnCurve[EvaluatedCurve]) -> Curve:
    return Curve(
        line_type=line_type_with_mirroring(drawn.line_type, drawn.mirrored),
        color=drawn.curve.attributes.color,
        title=drawn.curve.attributes.title,
        attributes=_attributes(drawn.curve.series_attributes),
        rrddata=drawn.curve.time_series.values,
    )


def empty_graph_spec(time_range: EngineTimeRange) -> GraphSpec:
    """The graph spec of a request that matched no graph."""
    return GraphSpec(
        start_time=time_range.start,
        end_time=time_range.end,
        step=time_range.step,
        curves=[],
    )


def evaluated_to_graph_spec(
    evaluated: EvaluatedGraph,
    *,
    fallback_time_range: EngineTimeRange,
) -> GraphSpec:
    """The evaluated graph in the shape of a graph spec."""
    time_range, curves = serialize_drawn_curves(
        evaluated, _curve, fallback_time_range=fallback_time_range
    )
    return GraphSpec(
        start_time=time_range.start,
        end_time=time_range.end,
        step=time_range.step,
        curves=curves,
    )
