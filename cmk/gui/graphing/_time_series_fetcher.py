#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass

from cmk.gui.utils.temperate_unit import TemperatureUnit

from ._from_api import RegisteredMetric
from ._graph_metric_expressions import AugmentedTimeSeries, LineType, RRDDataKey
from ._graph_specification import GraphDataRange, GraphRecipe
from ._rrd_fetch import fetch_time_series_rrd
from ._unit import user_specific_unit


@dataclass(frozen=True, kw_only=True)
class AugmentedTimeSeriesSpec:
    title: str
    line_type: LineType
    color: str
    fade_odd_color: bool
    augmented_time_series: Sequence[AugmentedTimeSeries]


def fetch_augmented_time_series(
    registered_metrics: Mapping[str, RegisteredMetric],
    graph_recipe: GraphRecipe,
    graph_data_range: GraphDataRange,
    *,
    temperature_unit: TemperatureUnit,
) -> Iterator[AugmentedTimeSeriesSpec]:
    rrd_data = fetch_time_series_rrd(
        registered_metrics,
        [
            k
            for gm in graph_recipe.metrics
            for k in gm.operation.keys(registered_metrics)
            if isinstance(k, RRDDataKey)
        ],
        graph_recipe.consolidation_function,
        user_specific_unit(graph_recipe.unit_spec, temperature_unit).conversion,
        start_time=graph_data_range.time_range[0],
        end_time=graph_data_range.time_range[1],
        step=graph_data_range.step,
    )
    for graph_metric in graph_recipe.metrics:
        if augmented_time_series := graph_metric.operation.compute_augmented_time_series(
            rrd_data, registered_metrics
        ):
            yield AugmentedTimeSeriesSpec(
                title=graph_metric.title,
                line_type=graph_metric.line_type,
                color=graph_metric.color,
                fade_odd_color=graph_metric.operation.fade_odd_color(),
                augmented_time_series=augmented_time_series,
            )
