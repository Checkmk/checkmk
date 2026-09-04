#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from typing import Literal, override

from cmk import trace
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing.v1 import Title as TitleV1
from cmk.graphing.v2_unstable import graphs as graphs_v2_unstable
from cmk.graphing.v2_unstable import metrics as metrics_v2_unstable
from cmk.gui.i18n import _, translate_to_current_language
from cmk.utils.servicename import ServiceName

from ._engine_discovery import GraphPluginChoice
from ._from_api import GraphFromAPI
from ._graph_metric_expressions import (
    AnnotatedHostName,
)
from ._graph_specification import (
    graph_specification_registry,
    GraphSpecification,
)
from ._graphs_order import GRAPHS_ORDER

tracer = trace.get_tracer()


class MKGraphNotFound(MKGeneralException): ...


def sort_registered_graph_plugins(
    registered_graphs: Mapping[str, GraphFromAPI],
) -> list[tuple[str, GraphFromAPI]]:
    def _by_index(graph_name: str) -> int:
        try:
            return GRAPHS_ORDER.index(graph_name)
        except ValueError:
            return -1

    return sorted(registered_graphs.items(), key=lambda t: _by_index(t[0]))


def get_graph_plugin_choices(
    registered_graphs: Mapping[str, GraphFromAPI],
) -> list[GraphPluginChoice]:
    return sorted(
        [
            GraphPluginChoice(graph.name, graph.title.localize(translate_to_current_language))
            for graph in registered_graphs.values()
        ],
        key=lambda c: c.title,
    )


def get_graph_plugin_from_id(
    registered_graphs: Mapping[str, GraphFromAPI],
    graph_id: str,
) -> GraphFromAPI:
    if graph_id.startswith("METRIC_"):
        metric_name = graph_id[7:]
        return graphs_v2_unstable.Graph(
            name=graph_id,
            title=TitleV1(""),
            compound_lines=[metric_name],
            simple_lines=[
                metrics_v1.WarningOf(metric_name),
                metrics_v1.CriticalOf(metric_name),
                metrics_v2_unstable.LowerWarningOf(metric_name),
                metrics_v2_unstable.LowerCriticalOf(metric_name),
            ],
        )
    for name, graph_plugin in sort_registered_graph_plugins(registered_graphs):
        if graph_id == name:
            return graph_plugin
    raise MKGraphNotFound(
        _("There is no graph plug-in with the id '%(graph_id)s'") % {"graph_id": graph_id}
    )


class TemplateGraphSpecification(GraphSpecification, frozen=True):
    site: SiteId | None
    host_name: AnnotatedHostName
    service_description: ServiceName
    graph_id: str | None = None
    destination: str | None = None

    @staticmethod
    @override
    def graph_type_name() -> Literal["template"]:
        return "template"

    @classmethod
    @override
    def add_visual_type(cls) -> Literal["pnpgraph"]:
        return "pnpgraph"


def get_template_graph_specification(
    *,
    site_id: SiteId | None,
    host_name: HostName,
    service_name: ServiceName,
    graph_id: str | None = None,
    destination: str | None = None,
) -> TemplateGraphSpecification:
    if issubclass(
        graph_specification := graph_specification_registry["template"], TemplateGraphSpecification
    ):
        return graph_specification(
            site=site_id,
            host_name=host_name,
            service_description=service_name,
            graph_id=graph_id,
            destination=destination,
        )
    raise TypeError(graph_specification)
