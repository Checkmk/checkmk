#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import ClassVar, Literal

from cmk.graphing.v1 import metrics as metrics_v1

from ._discovery import DiscoveredGraph
from ._fetch import FetchRRD
from ._objects import Bidirectional, Graph, MetricTranslations, ServiceRef
from ._options import TimeRange
from ._translate import fetch_translated_metrics


@dataclass(frozen=True, kw_only=True)
class ExplicitDiscoveryOptions:
    time_range: TimeRange
    graph: Graph | Bidirectional
    localizer: Callable[[str], str]
    metrics: Mapping[str, metrics_v1.Metric]
    translations: MetricTranslations


@dataclass(frozen=True, kw_only=True)
class ExplicitOptions:
    kind: ClassVar[Literal["explicit"]] = "explicit"
    time_range: TimeRange


def discover_explicit_graphs(
    options: ExplicitDiscoveryOptions,
    *,
    rrd: FetchRRD,
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
    return [
        DiscoveredGraph(
            graph=options.graph,
            options=ExplicitOptions(time_range=options.time_range),
            graph_title=options.graph.evaluated_title(translated_metrics),
            metric_data=options.graph.metric_data(translated_metrics),
        )
    ]
