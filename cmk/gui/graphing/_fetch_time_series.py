#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping, Sequence
from typing import Literal

from cmk.gui.color import fade_color, parse_color, render_color
from cmk.gui.utils.temperate_unit import TemperatureUnit

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


def _refine_augmented_time_series(
    augmented_time_series: Sequence[AugmentedTimeSeries],
    *,
    graph_metric_title: str,
    graph_metric_line_type: LineType | Literal["ref"],
    graph_metric_color: str,
    fade_odd_color: bool,
) -> Iterator[AugmentedTimeSeries]:
    multi = len(augmented_time_series) > 1
    for i, ts in enumerate(augmented_time_series):
        title = graph_metric_title
        line_type = graph_metric_line_type
        color = graph_metric_color
        if ts.metadata:
            if multi:
                title = f"{graph_metric_title} - {ts.metadata.title}"
                line_type = ts.metadata.line_type
            if ts.metadata.color:
                color = ts.metadata.color

        if i % 2 == 1 and fade_odd_color:
            color = render_color(fade_color(parse_color(color), 0.3))

        yield AugmentedTimeSeries(
            time_series=ts.time_series,
            metadata=TimeSeriesMetaData(
                title=title,
                line_type=line_type,
                color=color,
            ),
        )


def fetch_augmented_time_series(
    registered_metrics: Mapping[str, RegisteredMetric],
    graph_recipe: GraphRecipe,
    graph_data_range: GraphDataRange,
    *,
    temperature_unit: TemperatureUnit,
    fetch_time_series: FetchTimeSeries,
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

    rrd_data = fetch_time_series_rrd(
        registered_metrics,
        list(rrd_keys),
        consolidation_function,
        conversion,
        start_time=start_time,
        end_time=end_time,
        step=step,
    )
    query_data = fetch_time_series(
        list(query_keys),
        start_time=start_time,
        end_time=end_time,
    )

    for graph_metric in graph_recipe.metrics:
        if augmented_time_series := graph_metric.operation.compute_augmented_time_series(
            registered_metrics, rrd_data, query_data
        ):
            yield from _refine_augmented_time_series(
                augmented_time_series,
                graph_metric_title=graph_metric.title,
                graph_metric_line_type=graph_metric.line_type,
                graph_metric_color=graph_metric.color,
                fade_odd_color=graph_metric.operation.fade_odd_color(),
            )
