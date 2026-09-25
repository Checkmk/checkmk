#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The data fetch of the client-side graph widgets on a shared (token-authenticated) dashboard.

Unlike the session-authenticated graph fetch, this endpoint does not accept a graph definition:
the caller only names a widget of the dashboard its token was issued for, and the graph is
re-resolved from the current dashboard configuration on every fetch. A token holder therefore
cannot reach any data the dashboard does not already show, and an edited widget takes effect
without the token going stale.
"""

from typing import cast

from cmk.gui.dashboard.graph_widget_discovery import discover_widget_graphs, GRAPH_WIDGET_TYPES
from cmk.gui.dashboard.type_defs import CombinedGraphDashletConfig, DashletConfig
from cmk.gui.graphing import get_temperature_unit
from cmk.gui.graphing.openapi.fetch_graph_data import evaluate_built_graph_to_response
from cmk.gui.graphing.openapi.models import (
    ApiCombinationMode,
    ApiConsolidation,
    ApiTimeRange,
    GraphFetchResponse,
)
from cmk.gui.logged_in import user
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.restful_objects.constructors import domain_type_action_href
from cmk.gui.openapi.utils import ProblemException

from ._family import DASHBOARD_FAMILY
from ._widget_resolution import PERMISSIONS_WIDGET_QUERY, resolve_widget
from .model.widget_content.graph import CombinedGraphContent
from .model.widget_source import SavedWidgetContent


@api_model
class WidgetGraphFetchRequest:
    source: SavedWidgetContent = api_field(
        description="The widget of the token's dashboard to fetch the data for."
    )
    requested_time_range: ApiTimeRange = api_field(
        description="The time range (and step) to fetch data for. The returned range may differ.",
    )
    consolidation_function: ApiConsolidation = api_field(
        description="The consolidation function to use for RRD data.", example="avg"
    )


def _combination_mode(widget_config: DashletConfig) -> ApiCombinationMode | None:
    """How a combined graph widget folds its metrics; the other graph types do not combine.

    Taken from the widget configuration rather than the request: what the widget shows is the
    dashboard owner's decision, not the visitor's.
    """
    if widget_config["type"] != CombinedGraphContent.internal_type():
        return None
    return cast(CombinedGraphDashletConfig, widget_config)["presentation"]


def fetch_widget_graph_data_v1(
    api_context: ApiContext, body: WidgetGraphFetchRequest
) -> GraphFetchResponse:
    """Fetch the data of a shared dashboard's graph widget over a requested time range"""
    with resolve_widget(
        api_context, body.source, GRAPH_WIDGET_TYPES, lambda _content: None
    ) as widget:
        discovered = discover_widget_graphs(
            widget.config,
            widget.context,
            debug=api_context.config.debug,
            user_permissions=api_context.config.user_permissions(),
        )

        # The widget renders the first discovered graph, so that is the one to fetch.
        if not discovered.graphs:
            raise ProblemException(
                status=404,
                title="No graph data available",
                detail=discovered.no_data_message or "The widget has no graph to fetch.",
            )

        return evaluate_built_graph_to_response(
            discovered.graphs[0].graph,
            requested_time_range=body.requested_time_range,
            consolidation_function=body.consolidation_function,
            combination_mode=_combination_mode(widget.config),
            temperature_unit=get_temperature_unit(
                user, api_context.config.default_temperature_unit
            ),
        )


ENDPOINT_FETCH_WIDGET_GRAPH_DATA = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=domain_type_action_href(domain_type="dashboard", action="fetch-widget-graph-data"),
        link_relation="cmk/fetch_dashboard_widget_graph_data",
        method="post",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS_WIDGET_QUERY),
    doc=EndpointDoc(family=DASHBOARD_FAMILY.name),
    behavior=EndpointBehavior(skip_locking=True, update_config_generation=False),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=fetch_widget_graph_data_v1)},
    allowed_tokens={"dashboard"},
)
