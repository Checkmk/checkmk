#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from __future__ import annotations

from collections.abc import Mapping, Sequence

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.site import SiteId
from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing_engine import (
    build_matched_graphs,
    evaluate_graphs,
    EvaluatedGraph,
    Graph,
    RRDFetchData,
    RRDFetchMetricNames,
    RRDMetric,
)
from cmk.gui.config import active_config
from cmk.gui.graphing._graph_templates import TemplateGraphSpecification
from cmk.gui.i18n import _, translate_to_current_language

from ._engine_dispatch import (
    BuiltGraph,
    CommonGraphOptions,
    EngineGraphDispatcher,
    EvaluatedGraphs,
)
from ._engine_plugins import registered_translations
from ._engine_rrd import EngineRRDFetchData
from ._engine_serialization import (
    graph_codec,
)
from ._from_api import GraphFromAPI


def _assert_uniform_unit(graph: Graph) -> None:
    drawn = [
        *(member for stack in graph.stacks for member in stack.members),
        *(stack.reference for stack in graph.stacks if stack.reference is not None),
        *(line.curve for line in graph.lines),
    ]
    units = {curve.attributes.unit for curve in drawn}
    if len(units) > 1:
        raise MKGeneralException(
            _("Cannot create graph with metrics of different units: %(units)s")
            % {"units": ", ".join(sorted(repr(unit) for unit in units))}
        )


def _legacy_graph_id(graph: Graph, registered_graphs: Sequence[GraphFromAPI]) -> str:
    # The write side of the graph-name match the engine filters by: a graph named after a registered
    # plug-in is addressed by that name, while a fallback single-metric graph must carry the
    # "METRIC_" prefix legacy stores it under - without it the legacy recipe lookup finds neither a
    # plug-in nor the metric.
    if graph.name.startswith("METRIC_") or any(
        registered.name == graph.name for registered in registered_graphs
    ):
        return graph.name
    return f"METRIC_{graph.name}"


def _resolved_site(graph: Graph) -> SiteId | None:
    # The metric-name fetch tagged the service (hence its metrics) with the site its data lives on;
    # a template graph is single-service, so any RRD metric carries that resolved site.
    for metric in graph.metrics():
        if isinstance(metric, RRDMetric) and metric.site_id is not None:
            return SiteId(str(metric.site_id))
    return None


def build_template_graphs(
    specification: TemplateGraphSpecification,
    *,
    registered_graphs: Sequence[GraphFromAPI],
    registered_metrics: Mapping[str, metrics_v1.Metric],
    fetch_metric_names: RRDFetchMetricNames,
) -> Sequence[BuiltGraph]:
    graphs = build_matched_graphs(
        localizer=translate_to_current_language,
        fetch_metric_names=fetch_metric_names,
        kind="template",
        registered_graphs=registered_graphs,
        registered_metrics=registered_metrics,
        graph_name=specification.graph_id,
    )
    for graph in graphs:
        _assert_uniform_unit(graph)
    return [
        BuiltGraph(
            graph=graph,
            specification=TemplateGraphSpecification(
                site=_resolved_site(graph) or specification.site,
                host_name=specification.host_name,
                service_description=specification.service_description,
                graph_id=_legacy_graph_id(graph, registered_graphs),
                destination=specification.destination,
            ),
        )
        for graph in graphs
    ]


def evaluate_template_graphs(
    *,
    graphs: Sequence[Graph],
    options: CommonGraphOptions,
    fetch_data: RRDFetchData,
) -> Sequence[EvaluatedGraph]:
    return evaluate_graphs(
        consolidation_function=options.consolidation_function,
        time_range=options.time_range,
        graphs=graphs,
        fetch_data=fetch_data,
    )


def _dispatched_evaluate_template_graphs(
    *, graph: Graph, options: Mapping[str, object]
) -> EvaluatedGraphs:
    fetch_data = EngineRRDFetchData(
        debug=active_config.debug,
        registered_translations=registered_translations(),
    )
    return EvaluatedGraphs(
        graphs=evaluate_template_graphs(
            graphs=[graph],
            options=CommonGraphOptions.from_request_options(options),
            fetch_data=fetch_data,
        ),
        diagnostics=fetch_data.diagnostics,
    )


TEMPLATE_GRAPH_DISPATCHER = EngineGraphDispatcher(
    kind="template",
    codec=graph_codec(),
    evaluate=_dispatched_evaluate_template_graphs,
)
