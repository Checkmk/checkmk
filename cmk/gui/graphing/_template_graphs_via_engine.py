#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from __future__ import annotations

import functools
from collections.abc import Mapping, Sequence

from cmk.ccc.exceptions import MKGeneralException
from cmk.discover_plugins import discover_all_plugins, DiscoveredPlugins, PluginGroup
from cmk.graphing.v1 import entry_point_prefixes as entry_point_prefixes_v1
from cmk.graphing.v1 import graphs as graphs_v1
from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing.v1 import translations as translations_v1
from cmk.graphing.v2_unstable import (
    entry_point_prefixes as entry_point_prefixes_v2_unstable,
)
from cmk.graphing.v2_unstable import graphs as graphs_v2_unstable
from cmk.graphing_engine import (
    build_service_graphs,
    ConsolidationFunction,
    EvaluatedGraph,
    fetch_performance_data,
    ResolvedGraph,
    RRDSource,
    ServiceRef,
    TimeRange,
    update_graph,
)
from cmk.gui.config import active_config
from cmk.gui.i18n import _, translate_to_current_language

from ._engine_dispatch import EngineGraphUpdater, GraphDataRequest
from ._engine_rrd_source import EngineRRDSource
from ._engine_serialization import deserialize_resolved_graphs, ensure_type
from ._from_api import GraphFromAPI, PerfometerFromAPI
from ._graph_templates import sort_registered_graph_plugins

# The graph types the engine accepts; used to pick graph plugins out of the resolved set.
_GRAPH_TYPES = (
    graphs_v1.Graph,
    graphs_v1.Bidirectional,
    graphs_v2_unstable.Graph,
    graphs_v2_unstable.Bidirectional,
)


@functools.cache
def _graphing_plugins() -> DiscoveredPlugins[
    metrics_v1.Metric | PerfometerFromAPI | GraphFromAPI | translations_v1.Translation
]:
    return discover_all_plugins(
        PluginGroup.GRAPHING,
        dict(entry_point_prefixes_v1()) | dict(entry_point_prefixes_v2_unstable()),
        skip_wrong_types=False,
        raise_errors=False,
    )


def registered_metrics() -> Mapping[str, metrics_v1.Metric]:
    return {
        plugin.name: plugin
        for plugin in _graphing_plugins().plugins.values()
        if isinstance(plugin, metrics_v1.Metric)
    }


def registered_graphs() -> Sequence[GraphFromAPI]:
    # Emit graphs in the legacy discovery order (cf. sort_registered_graph_plugins): ordered by
    # GRAPHS_ORDER, with any graph not listed there kept ahead of the ordered ones.
    registered = {
        plugin.name: plugin
        for plugin in _graphing_plugins().plugins.values()
        if isinstance(plugin, _GRAPH_TYPES)
    }
    return [plugin for _name, plugin in sort_registered_graph_plugins(registered)]


def registered_translations() -> Sequence[translations_v1.Translation]:
    return [
        plugin
        for plugin in _graphing_plugins().plugins.values()
        if isinstance(plugin, translations_v1.Translation)
    ]


def resolve_template_graphs(
    *,
    service: ServiceRef,
    rrd: RRDSource,
) -> Sequence[ResolvedGraph]:
    available = fetch_performance_data(
        services=[service],
        translations=registered_translations(),
        rrd=rrd,
    ).get(service, {})
    graphs = build_service_graphs(
        service=service,
        registered_graphs=registered_graphs(),
        metrics=registered_metrics(),
        localizer=translate_to_current_language,
        available=available,
        graph_type="template",
    )
    for graph in graphs:
        _assert_uniform_unit(graph)
    return graphs


# A template graph has a single value axis, so its drawn curves must share one unit (legacy parity).
# Only drawn curves are checked — threshold rules (warn / crit) are a separate concern.
def _assert_uniform_unit(graph: ResolvedGraph) -> None:
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


def update_template_graph_via_engine(
    *,
    resolved: Sequence[ResolvedGraph],
    rrd: RRDSource,
    consolidation_function: ConsolidationFunction,
    time_range: TimeRange,
) -> Sequence[EvaluatedGraph]:
    return update_graph(
        graphs=resolved,
        translations=registered_translations(),
        consolidation_function=consolidation_function,
        time_range=time_range,
        rrd=rrd,
    )


def _update_template_graph_via_dispatch(request: GraphDataRequest) -> Sequence[EvaluatedGraph]:
    return update_template_graph_via_engine(
        resolved=deserialize_resolved_graphs(request.definition),
        rrd=EngineRRDSource(site_id=None, debug=active_config.debug),
        consolidation_function=ensure_type(
            request.options["consolidation_function"], ConsolidationFunction
        ),
        time_range=ensure_type(request.options["time_range"], TimeRange),
    )


TEMPLATE_GRAPH_UPDATER = EngineGraphUpdater(
    graph_type="template", update=_update_template_graph_via_dispatch
)
