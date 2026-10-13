#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence
from dataclasses import dataclass

from cmk.graphing_engine import Graph
from cmk.gui.i18n import _

from ._from_api import GraphFromAPI
from ._graph_dispatch import legacy_graph_id


@dataclass(frozen=True)
class GraphPluginChoice:
    id: str
    title: str


@dataclass(frozen=True)
class GraphChoices:
    plugin_graphs: Sequence[GraphPluginChoice]
    single_metrics: Sequence[GraphPluginChoice]


def graph_choices(
    graphs: Sequence[Graph], registered_graphs: Sequence[GraphFromAPI]
) -> GraphChoices:
    plugin_graphs = []
    single_metrics = []
    for graph in graphs:
        graph_id = legacy_graph_id(graph, registered_graphs)
        if graph_id.startswith("METRIC_"):
            single_metrics.append(
                GraphPluginChoice(graph_id, _("Metric: %(title)s") % {"title": graph.title})
            )
        else:
            plugin_graphs.append(GraphPluginChoice(graph_id, graph.title))
    return GraphChoices(plugin_graphs=plugin_graphs, single_metrics=single_metrics)
