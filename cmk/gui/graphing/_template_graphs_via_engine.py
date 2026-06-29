#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from __future__ import annotations

from collections.abc import Mapping, Sequence

from cmk.ccc.exceptions import MKGeneralException
from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing.v1 import translations as translations_v1
from cmk.graphing_engine import (
    build_service_graphs,
    ConsolidationFunction,
    EvaluatedGraph,
    fetch_performance_data,
    Graph,
    RRDSource,
    ServiceRef,
    TimeRange,
    update_graphs,
)
from cmk.gui.config import active_config
from cmk.gui.i18n import _, translate_to_current_language

from ._engine_dispatch import EngineGraphUpdater, GraphDataRequest
from ._engine_plugins import registered_translations
from ._engine_rrd_source import EngineRRDSource
from ._engine_serialization import deserialize_graphs, ensure_type
from ._from_api import GraphFromAPI


# A template graph has a single value axis, so its drawn curves must share one unit (legacy parity).
# Only drawn curves are checked — threshold rules (warn / crit) are a separate concern.
def _assert_uniform_unit(graph: Graph) -> None:
    drawn = [
        *(member for stack in graph.stacks for member in stack.members),
        *(stack.reference for stack in graph.stacks if stack.reference is not None),
        *(line.curve for line in graph.lines),
    ]
    units = {curve.attributes.unit for curve in drawn}
    if len(units) > 1:
        raise MKGeneralException(
            _("Cannot create graph with metrics of different units: %s")
            % ", ".join(sorted(repr(unit) for unit in units))
        )


def build_template_graphs(
    *,
    service: ServiceRef,
    rrd: RRDSource,
    graphs: Sequence[GraphFromAPI],
    metric_registry: Mapping[str, metrics_v1.Metric],
    translations: Sequence[translations_v1.Translation],
) -> Sequence[Graph]:
    available = fetch_performance_data(
        services=[service],
        translations=translations,
        rrd=rrd,
    ).get(service, {})
    built_graphs = build_service_graphs(
        service=service,
        registered_graphs=graphs,
        metrics=metric_registry,
        localizer=translate_to_current_language,
        available=available,
        graph_type="template",
    )
    for graph in built_graphs:
        _assert_uniform_unit(graph)
    return built_graphs


def update_template_graphs(
    *,
    built_graphs: Sequence[Graph],
    rrd: RRDSource,
    consolidation_function: ConsolidationFunction,
    time_range: TimeRange,
) -> Sequence[EvaluatedGraph]:
    return update_graphs(
        graphs=built_graphs,
        translations=registered_translations(),
        consolidation_function=consolidation_function,
        time_range=time_range,
        rrd=rrd,
    )


def _dispatched_update_template_graphs(request: GraphDataRequest) -> Sequence[EvaluatedGraph]:
    return update_template_graphs(
        built_graphs=deserialize_graphs(request.definition),
        rrd=EngineRRDSource(site_id=None, debug=active_config.debug),
        consolidation_function=ensure_type(
            request.options["consolidation_function"], ConsolidationFunction
        ),
        time_range=ensure_type(request.options["time_range"], TimeRange),
    )


TEMPLATE_GRAPH_UPDATER = EngineGraphUpdater(
    graph_type="template", update=_dispatched_update_template_graphs
)
