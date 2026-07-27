#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from __future__ import annotations

from collections.abc import Mapping, Sequence

from cmk.ccc.exceptions import MKGeneralException
from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing_engine import (
    build_matched_graphs,
    evaluate_graphs,
    EvaluatedGraph,
    Graph,
    RRDFetchData,
    RRDFetchMetricNames,
)
from cmk.gui.config import active_config
from cmk.gui.graphing._graph_templates import TemplateGraphSpecification
from cmk.gui.i18n import _, translate_to_current_language

from ._engine_dispatch import (
    CommonGraphOptions,
    EngineGraphDispatcher,
    EvaluatedGraphs,
)
from ._engine_plugins import registered_translations
from ._engine_rrd import EngineRRDFetchData
from ._engine_serialization import (
    graph_codec,
    GraphCodec,
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


def build_template_graphs(
    specification: TemplateGraphSpecification,
    *,
    registered_graphs: Sequence[GraphFromAPI],
    registered_metrics: Mapping[str, metrics_v1.Metric],
    fetch_metric_names: RRDFetchMetricNames,
) -> Sequence[Graph]:
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
    return graphs


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
    *, codec: GraphCodec, graph: Mapping[str, object], options: Mapping[str, object]
) -> EvaluatedGraphs:
    fetch_data = EngineRRDFetchData(
        debug=active_config.debug,
        registered_translations=registered_translations(),
    )
    return EvaluatedGraphs(
        graphs=evaluate_template_graphs(
            graphs=[codec.deserialize_graph(graph)],
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
