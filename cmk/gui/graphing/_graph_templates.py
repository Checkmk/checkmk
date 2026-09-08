#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final, Literal, override, Self

from cmk import trace
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName as GUIHostName
from cmk.ccc.site import SiteId
from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing.v1 import Title as TitleV1
from cmk.graphing.v2_unstable import graphs as graphs_v2_unstable
from cmk.graphing.v2_unstable import metrics as metrics_v2_unstable
from cmk.graphing_engine import (
    build_matched_graphs,
    evaluate_graphs,
    FetchMetricNamesProtocol,
    Graph,
    HostName,
    RRDMetric,
    ServiceName,
)
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKMissingDataError
from cmk.gui.graphing._graph_codec import GraphCodec
from cmk.gui.i18n import _, translate_to_current_language
from cmk.utils.servicename import ServiceName as GUIServiceName

from ._from_api import GraphFromAPI
from ._graph_choices import BuiltGraph, DiscoveredGraphs, GraphPluginChoice
from ._graph_dispatch import (
    CommonGraphOptions,
    EvaluatedGraphs,
    FetchDataWithDiagnosticsProtocol,
    GraphDispatcher,
    legacy_graph_id,
)
from ._graph_metric_expressions import (
    AnnotatedHostName,
)
from ._graph_specification import (
    graph_specification_registry,
    GraphSpecification,
)
from ._graphs_order import sort_registered_graph_plugins
from ._plugins import registered_graphs, registered_metrics, registered_translations
from ._source import RRDFetchData, RRDFetchMetricNames

tracer = trace.get_tracer()


class MKGraphNotFound(MKGeneralException): ...


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
    service_description: GUIServiceName
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
    host_name: GUIHostName,
    service_name: GUIServiceName,
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


TEMPLATE_KIND: Final = "template"


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
    fetch_metric_names: FetchMetricNamesProtocol,
) -> Sequence[BuiltGraph]:
    graphs = build_matched_graphs(
        localizer=translate_to_current_language,
        fetch_metric_names=fetch_metric_names,
        kind=TEMPLATE_KIND,
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
                graph_id=legacy_graph_id(graph, registered_graphs),
                destination=specification.destination,
            ),
        )
        for graph in graphs
    ]


@dataclass(frozen=True)
class _EvaluateTemplateGraphs:
    options: CommonGraphOptions
    fetch_data: FetchDataWithDiagnosticsProtocol

    @classmethod
    def make(cls, options: Mapping[str, object]) -> Self:
        return cls(
            CommonGraphOptions.from_request_options(options),
            RRDFetchData(
                debug=active_config.debug,
                registered_translations=registered_translations(),
            ),
        )

    def __call__(self, graph: Graph) -> EvaluatedGraphs:
        return EvaluatedGraphs(
            graphs=evaluate_graphs(
                consolidation_function=self.options.consolidation_function,
                time_range=self.options.time_range,
                graphs=[graph],
                fetch_data=self.fetch_data,
            ),
            diagnostics=self.fetch_data.diagnostics,
        )


def template_graph_dispatcher(codec: GraphCodec) -> GraphDispatcher:
    # The codec is the edition's, not this kind's: every graph of an edition is read with all of
    # its quantities, so a definition holding one another kind introduced still round-trips.
    return GraphDispatcher(
        kind=TEMPLATE_KIND,
        codec=codec,
        make_evaluate=_EvaluateTemplateGraphs.make,
    )


def discover_template_graphs(
    specification: TemplateGraphSpecification, *, debug: bool
) -> DiscoveredGraphs:
    """Discover the template graphs of a service."""
    try:
        graphs = build_template_graphs(
            specification,
            registered_graphs=registered_graphs(),
            registered_metrics=registered_metrics(),
            fetch_metric_names=RRDFetchMetricNames(
                host_name=HostName(specification.host_name),
                service_name=ServiceName(specification.service_description),
                debug=debug,
                site_id=specification.site,
                registered_translations=registered_translations(),
            ),
        )
    except MKMissingDataError as exc:
        return DiscoveredGraphs.nothing(str(exc))

    if not graphs:
        return DiscoveredGraphs.nothing(
            _("The service '%(service)s' of host '%(host)s' has no matching template graphs.")
            % {
                "service": specification.service_description,
                "host": specification.host_name,
            }
        )
    return DiscoveredGraphs.found(graphs)


def resolve_graph_id_from_index(
    *,
    site_id: SiteId | None,
    host_name: GUIHostName,
    service_name: GUIServiceName,
    graph_index: int,
    debug: bool,
) -> str | None:
    discovered = discover_template_graphs(
        TemplateGraphSpecification(
            site=site_id,
            host_name=host_name,
            service_description=service_name,
        ),
        debug=debug,
    )
    if not 0 <= graph_index < len(discovered.graphs):
        return None
    return legacy_graph_id(discovered.graphs[graph_index].graph, registered_graphs())
