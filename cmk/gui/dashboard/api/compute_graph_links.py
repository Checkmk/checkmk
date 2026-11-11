#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Annotated, TypeIs

from annotated_types import MaxLen
from pydantic import Discriminator

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.gui.graphing.openapi.models import ApiCurveOrigin
from cmk.gui.openapi.framework import ApiContext
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.type_defs import FilterHTTPVariables, FilterName
from cmk.gui.visuals.filter.drilldowns import RowValues

from ._compute_endpoint import widget_compute_endpoint
from ._contextual_link_encoding import link_columns, link_properties_for
from ._link_rows import link_service_rows
from ._widget_resolution import no_built_in_link, resolve_widget
from .model.link_properties import LinkProperties, ResolvedLink
from .model.response_model import ComputedWidgetResponse
from .model.widget_content._base import BaseWidgetContent
from .model.widget_content.graph import (
    CombinedGraphContent,
    PerformanceGraphContent,
    SingleTimeseriesContent,
)
from .model.widget_content.metric import AverageScatterplotContent
from .model.widget_source import ExplicitWidgetContent

# The services per request: COMBINED_GRAPH_OBJECT_LIMIT, which this free code cannot import.
GRAPH_LINK_SERVICE_LIMIT = 200

type GraphLinkContent = Annotated[
    SingleTimeseriesContent
    | PerformanceGraphContent
    | CombinedGraphContent
    | AverageScatterplotContent,
    Discriminator("type"),
]


@api_model
class GraphLinksRequest:
    source: ExplicitWidgetContent[GraphLinkContent] = api_field(
        description="The graph widget whose links to resolve."
    )
    services: Annotated[list[ApiCurveOrigin], MaxLen(GRAPH_LINK_SERVICE_LIMIT)] = api_field(
        description="The services the graph draws a curve for; one without a site is looked up on "
        "all sites."
    )


@api_model
class GraphServiceLinks(ApiCurveOrigin):
    link_properties: LinkProperties = api_field(
        description="What following a link from the service carries, per link."
    )


@api_model
class GraphLinks:
    links: list[ResolvedLink] = api_field(
        description="The resolved links of the widget; empty when it links nowhere."
    )
    services: list[GraphServiceLinks] = api_field(
        description="The requested services, in their order."
    )


@dataclass(frozen=True)
class _Service:
    site_id: SiteId | None
    host_name: HostName
    service_description: str


def _is_linked_graph(content: BaseWidgetContent) -> TypeIs[GraphLinkContent]:
    return isinstance(
        content,
        (
            SingleTimeseriesContent,
            PerformanceGraphContent,
            CombinedGraphContent,
            AverageScatterplotContent,
        ),
    )


def compute_graph_links(
    api_context: ApiContext, body: GraphLinksRequest
) -> ComputedWidgetResponse[GraphLinks]:
    """Resolve the contextual links of a graph widget for the services it draws."""
    with resolve_widget(api_context, body.source, _is_linked_graph, no_built_in_link) as widget:
        services = [
            _Service(
                site_id=None if service.site_id is None else SiteId(service.site_id),
                host_name=HostName(service.host_name),
                service_description=service.service_description,
            )
            for service in body.services
        ]
        columns = link_columns(widget.links, valued={"siteopt", "host", "service"})
        rows = link_service_rows(services, columns) if columns else {}
        return ComputedWidgetResponse.of(
            GraphLinks(
                links=widget.links_to_api(),
                services=[
                    GraphServiceLinks(
                        site_id=service.site_id,
                        host_name=service.host_name,
                        service_description=service.service_description,
                        link_properties=link_properties_for(
                            widget.links, _native_key(service), _row_of(service, rows)
                        ),
                    )
                    for service in services
                ],
            )
        )


def _native_key(service: _Service) -> dict[FilterName, FilterHTTPVariables]:
    key: dict[FilterName, FilterHTTPVariables] = {
        "host": {"host": service.host_name},
        "service": {"service": service.service_description},
    }
    if service.site_id is not None:
        key["siteopt"] = {"site": service.site_id}
    return key


def _row_of(
    service: _Service, rows: Mapping[tuple[SiteId, HostName, str], RowValues]
) -> RowValues | None:
    """The row of the service; of the first site that has it, if its site is unknown."""
    if service.site_id is not None:
        return rows.get((service.site_id, service.host_name, service.service_description))
    return next(
        (
            row
            for (_site_id, host_name, service_description), row in rows.items()
            if host_name == service.host_name and service_description == service.service_description
        ),
        None,
    )


ENDPOINT_COMPUTE_GRAPH_LINKS = widget_compute_endpoint(
    action="compute-graph-links",
    link_relation="cmk/compute_graph_links",
    handler=compute_graph_links,
    link_targets=True,
    supported_editions="all",
    shared_dashboards=False,
)
