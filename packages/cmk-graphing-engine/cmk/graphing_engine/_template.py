#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Container, Mapping, Sequence
from dataclasses import dataclass
from typing import ClassVar, Literal

from cmk.graphing.v1 import graphs as graphs_v1
from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing.v2_unstable import graphs as graphs_v2_unstable

from ._fetch import fetch_translated_metrics, FetchRRD
from ._from_api import (
    metric_names_of_graph,
    metric_names_of_title,
    parse_graph_from_api,
)
from ._objects import (
    DiscoveredGraph,
    Graph,
    Line,
    metric_data_of,
    MetricName,
    MetricTranslation,
    RRDMetric,
    RRDMetricData,
    ServiceRef,
    Stack,
)
from ._options import ConsolidationFunction, TimeRange
from ._title import evaluate_title

# A predictive metric (predict_<name> / predict_lower_<name>) is drawn alongside the metric it
# predicts; predict_lower_ also starts with this prefix.
_PREDICT_PREFIX = "predict_"


@dataclass(frozen=True, kw_only=True)
class TemplateDiscoveryOptions:
    time_range: TimeRange
    service: ServiceRef
    consolidation_function: ConsolidationFunction
    localizer: Callable[[str], str]
    registered_graphs: Sequence[
        graphs_v1.Graph
        | graphs_v1.Bidirectional
        | graphs_v2_unstable.Graph
        | graphs_v2_unstable.Bidirectional
    ]
    metrics: Mapping[str, metrics_v1.Metric]
    translations: Mapping[str, Mapping[MetricName, MetricTranslation]]


@dataclass(frozen=True, kw_only=True)
class TemplateOptions:
    kind: ClassVar[Literal["template"]] = "template"
    time_range: TimeRange
    consolidation_function: ConsolidationFunction


def _matches(
    graph: graphs_v1.Graph | graphs_v2_unstable.Graph,
    names: Sequence[MetricName],
    available: Container[MetricName],
) -> bool:
    if any(MetricName(name) in available for name in graph.conflicting):
        return False
    optional = frozenset(MetricName(name) for name in graph.optional)
    return all(name in available for name in names if name not in optional)


@dataclass(frozen=True, kw_only=True)
class _GraphMatch:
    metric_names: Sequence[MetricName]
    matched: bool


def _walk(
    graph: (
        graphs_v1.Graph
        | graphs_v1.Bidirectional
        | graphs_v2_unstable.Graph
        | graphs_v2_unstable.Bidirectional
    ),
    available: Container[MetricName],
) -> _GraphMatch:
    match graph:
        case graphs_v1.Graph() | graphs_v2_unstable.Graph():
            names = metric_names_of_graph(graph)
            return _GraphMatch(metric_names=names, matched=_matches(graph, names, available))
        case graphs_v1.Bidirectional() | graphs_v2_unstable.Bidirectional():
            title_names = metric_names_of_title(graph.title)
            lower_names = metric_names_of_graph(graph.lower)
            upper_names = metric_names_of_graph(graph.upper)
            return _GraphMatch(
                metric_names=list(set((*title_names, *lower_names, *upper_names))),
                matched=(
                    all(name in available for name in title_names)
                    and (
                        _matches(graph.lower, lower_names, available)
                        or _matches(graph.upper, upper_names, available)
                    )
                ),
            )


def _add_predictive_lines(
    graph: Graph,
    service: ServiceRef,
    available: Mapping[MetricName, RRDMetricData],
) -> tuple[Graph, set[MetricName]]:
    """Augment a template graph with the predictive companions of its metrics (new graph object)."""
    # A predictive companion is drawn in the same direction as the line of the metric it predicts.
    inverse_by_metric: dict[MetricName, bool] = {}
    for drawn in graph.drawn_metrics():
        inverse_by_metric.setdefault(drawn.metric.metric_name, drawn.inverse)

    added: list[Line] = []
    names: set[MetricName] = set()
    for base, inverse in inverse_by_metric.items():
        for predictive in (
            MetricName(f"predict_{base}"),
            MetricName(f"predict_lower_{base}"),
        ):
            if predictive in available and predictive not in names:
                added.append(
                    Line(
                        quantity=RRDMetric(
                            host_name=service.host_name,
                            service_name=service.service_name,
                            metric_name=predictive,
                        ),
                        inverse=inverse,
                    )
                )
                names.add(predictive)
    if not added:
        return graph, names
    return (
        Graph(
            name=graph.name,
            title=graph.title,
            vertical_range=graph.vertical_range,
            stacks=graph.stacks,
            lines=[*graph.lines, *added],
        ),
        names,
    )


def discover_template_graphs(
    options: TemplateDiscoveryOptions,
    *,
    rrd: FetchRRD,
) -> Sequence[DiscoveredGraph[TemplateOptions]]:
    translated_metrics = fetch_translated_metrics(
        [options.service],
        rrd=rrd,
        translations=options.translations,
        metrics=options.metrics,
        localizer=options.localizer,
    )
    service_metrics = translated_metrics.get(options.service, {})
    post_options = TemplateOptions(
        time_range=options.time_range,
        consolidation_function=options.consolidation_function,
    )

    discovered: list[DiscoveredGraph[TemplateOptions]] = []
    claimed: set[MetricName] = set()

    def _discover(base: Graph) -> DiscoveredGraph[TemplateOptions]:
        # Draw the predictive companions of the graph's metrics, claim them, and build the result.
        graph, predictive_names = _add_predictive_lines(base, options.service, service_metrics)
        claimed.update(predictive_names)
        return DiscoveredGraph(
            graph=graph,
            options=post_options,
            graph_title=evaluate_title(graph.title, translated_metrics),
            metric_data=metric_data_of(graph, translated_metrics),
        )

    for plugin in options.registered_graphs:
        walk = _walk(plugin, service_metrics)
        if not walk.matched:
            continue
        claimed.update(walk.metric_names)
        discovered.append(
            _discover(
                parse_graph_from_api(
                    plugin,
                    options.localizer,
                    options.service,
                    options.metrics,
                )
            )
        )

    for name in service_metrics:
        # Predictive metrics are companions of the metric they predict, never graphed on their own.
        if name in claimed or name.startswith(_PREDICT_PREFIX):
            continue
        discovered.append(
            _discover(
                Graph(
                    name=name,
                    title=name,
                    stacks=[
                        Stack(
                            members=[
                                RRDMetric(
                                    host_name=options.service.host_name,
                                    service_name=options.service.service_name,
                                    metric_name=name,
                                )
                            ],
                            inverse=False,
                        )
                    ],
                )
            )
        )

    return discovered
