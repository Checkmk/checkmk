#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping, Sequence
from typing import Literal

from cmk.gui.color import fade_color, parse_color, render_color
from cmk.gui.utils.temperate_unit import TemperatureUnit
from cmk.utils.macros import replace_macros_in_str

from ._from_api import RegisteredMetric
from ._graph_metric_expressions import (
    AugmentedTimeSeries,
    LineType,
    QueryDataKey,
    RRDDataKey,
    TimeSeriesMetaData,
)
from ._graph_specification import GraphDataRange, GraphRecipe
from ._metric_backend_registry import FetchTimeSeries
from ._rrd import fetch_time_series_rrd
from ._unit import user_specific_unit


def fetch_augmented_time_series(
    registered_metrics: Mapping[str, RegisteredMetric],
    graph_recipe: GraphRecipe,
    graph_data_range: GraphDataRange,
    *,
    temperature_unit: TemperatureUnit,
    backend_time_series_fetcher: FetchTimeSeries | None,
) -> Iterator[AugmentedTimeSeries]:
    consolidation_function = graph_recipe.consolidation_function
    conversion = user_specific_unit(graph_recipe.unit_spec, temperature_unit).conversion
    start_time = graph_data_range.time_range[0]
    end_time = graph_data_range.time_range[1]
    step = graph_data_range.step

    rrd_keys = set()
    query_keys = set()
    for graph_metric in graph_recipe.metrics:
        for key in graph_metric.operation.keys(registered_metrics):
            match key:
                case RRDDataKey():
                    rrd_keys.add(key)
                case QueryDataKey():
                    query_keys.add(key)
                case _:
                    pass

    rrd_data = fetch_time_series_rrd(
        list(rrd_keys),
        consolidation_function,
        conversion,
        start_time=start_time,
        end_time=end_time,
        step=step,
    )

    if backend_time_series_fetcher and query_keys:
        # Align grid (start, end, step) to RRD data if available. We need this because our graph
        # rendering code assumes a fixed grid for all time series in a graph. The RRDs are already
        # aligned to a fixed grid (the grid used by the first RRD time series).
        if first_rrd_series := next(iter(rrd_data.values()), None):
            start_time = first_rrd_series.start
            end_time = first_rrd_series.end
            step = first_rrd_series.step
        else:
            # A too low step size leads to two negative effects:
            # 1. Higher query load
            # 2. Lots of None values in the time series ==> Lots of holes in the graphs
            # Note that the RRDs also adjust to their internal precision. They dont't return data at higher
            # precision than they store it.
            step = max(int(step), 60)

        query_data = backend_time_series_fetcher(
            list(query_keys),
            start_time=start_time,
            end_time=end_time,
            step=step,
        )
    else:
        query_data = {}

    for graph_metric in graph_recipe.metrics:
        if augmented_time_series := graph_metric.operation.compute_augmented_time_series(
            registered_metrics, rrd_data, query_data
        ):
            yield from _refine_augmented_time_series(
                augmented_time_series,
                graph_metric_title=graph_metric.title,
                graph_metric_line_type=graph_metric.line_type,
                graph_metric_color=graph_metric.color,
                graph_metric_expression_name=graph_metric.operation.expression_name(),
                fade_odd_color=graph_metric.operation.fade_odd_color(),
            )


def _refine_augmented_time_series(
    augmented_time_series: Sequence[AugmentedTimeSeries],
    *,
    graph_metric_title: str,
    graph_metric_line_type: LineType | Literal["ref"],
    graph_metric_color: str,
    graph_metric_expression_name: str,
    fade_odd_color: bool,
) -> Iterator[AugmentedTimeSeries]:
    multi = len(augmented_time_series) > 1
    for i, ats in enumerate(augmented_time_series):
        title = graph_metric_title
        line_type = graph_metric_line_type
        color = graph_metric_color
        if ats.meta_data:
            if graph_metric_expression_name == "query" and ats.meta_data.title is not None:
                macros: dict[str, str] = {
                    "$SERIES_ID$": ats.meta_data.title,
                }
                if ats.meta_data.metric_name is not None:
                    macros["$METRIC_NAME$"] = ats.meta_data.metric_name
                for key, value in ats.meta_data.attributes.get("resource", {}).items():
                    macros[f"$RESOURCE_ATTR.{key}$"] = value
                for key, value in ats.meta_data.attributes.get("scope", {}).items():
                    macros[f"$SCOPE_ATTR.{key}$"] = value
                for key, value in ats.meta_data.attributes.get("data_point", {}).items():
                    macros[f"$DATA_POINT_ATTR.{key}$"] = value

                title = replace_macros_in_str(graph_metric_title, macros)
            elif (
                multi or graph_metric_expression_name == "query"
            ) and ats.meta_data.title is not None:
                title = f"{graph_metric_title} - {ats.meta_data.title}"
            if multi and ats.meta_data.line_type is not None:
                line_type = ats.meta_data.line_type
            if ats.meta_data.color:
                color = ats.meta_data.color

        if i % 2 == 1 and fade_odd_color:
            color = render_color(fade_color(parse_color(color), 0.3))

        yield AugmentedTimeSeries(
            time_series=ats.time_series,
            meta_data=TimeSeriesMetaData(
                title=title,
                line_type=line_type,
                color=color,
                attributes={} if ats.meta_data is None else ats.meta_data.attributes,
                metric_name=None if ats.meta_data is None else ats.meta_data.metric_name,
            ),
        )
