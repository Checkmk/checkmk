#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import ClassVar, Literal

from cmk.graphing.v1 import metrics as metrics_v1

from ._evaluate import DiscoveredGraph
from ._fetch import fetch_translated_metrics, GraphRequest, RRDSource, update_graph_data
from ._objects import (
    Graph,
    metric_data_of,
    MetricName,
    MetricTranslation,
    ServiceRef,
)
from ._options import TimeRange
from ._title import evaluate_title


@dataclass(frozen=True, kw_only=True)
class ExplicitDiscoveryOptions:
    time_range: TimeRange
    graph: Graph
    localizer: Callable[[str], str]
    metrics: Mapping[str, metrics_v1.Metric]
    translations: Mapping[str, Mapping[MetricName, MetricTranslation]]


@dataclass(frozen=True, kw_only=True)
class ExplicitOptions:
    kind: ClassVar[Literal["explicit"]] = "explicit"
    time_range: TimeRange


def discover_explicit_graphs(
    options: ExplicitDiscoveryOptions,
    *,
    rrd: RRDSource,
) -> Sequence[DiscoveredGraph[ExplicitOptions]]:
    # The graph's metrics carry their own service, so the services to fetch are derived from them.
    translated_metrics = fetch_translated_metrics(
        (
            ServiceRef(host_name=metric.host_name, service_name=metric.service_name)
            for metric in options.graph.rrd_metrics()
        ),
        rrd=rrd,
        translations=options.translations,
        metrics=options.metrics,
        localizer=options.localizer,
    )
    [evaluated] = update_graph_data(
        [
            GraphRequest(
                time_range=options.time_range,
                graph=options.graph,
                metric_data=metric_data_of(options.graph, translated_metrics),
            )
        ],
        rrd=rrd,
    )
    return [
        DiscoveredGraph(
            graph=options.graph,
            options=ExplicitOptions(time_range=options.time_range),
            title=evaluate_title(options.graph.title, translated_metrics),
            stacks=evaluated.stacks,
            lines=evaluated.lines,
        )
    ]
