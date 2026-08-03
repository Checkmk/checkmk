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

from cmk.gui.dashboard.exceptions import WidgetRenderError
from cmk.gui.dashboard.graph_widget_discovery import discover_widget_graphs
from cmk.gui.dashboard.token_util import (
    disable_dashboard_token_by_id,
    get_dashboard_widget_by_id,
    impersonate_dashboard_token_issuer,
    InvalidWidgetError,
)
from cmk.gui.dashboard.type_defs import CombinedGraphDashletConfig, DashletConfig
from cmk.gui.exceptions import MKMissingDataError, MKUserError
from cmk.gui.graphing._engine_dispatch import serialize_graphs
from cmk.gui.graphing.openapi.fetch_graph_data import evaluate_graph_to_response
from cmk.gui.graphing.openapi.models import (
    ApiCombinationMode,
    ApiConsolidation,
    ApiTimeRange,
    GraphFetchResponse,
)
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.restful_objects.constructors import domain_type_action_href
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.token_auth import AuthToken, DashboardToken
from cmk.livestatus_client import MKLivestatusException

from ._family import DASHBOARD_FAMILY
from .model.widget_content.graph import CombinedGraphContent


@api_model
class WidgetGraphFetchRequest:
    widget_id: str = api_field(
        description="The ID of the widget of the token's dashboard to fetch the data for.",
        example="widget_1",
    )
    requested_time_range: ApiTimeRange = api_field(
        description="The time range (and step) to fetch data for. The returned range may differ.",
    )
    consolidation_function: ApiConsolidation = api_field(
        description="The consolidation function to use for RRD data.", example="avg"
    )


def _dashboard_token(token: AuthToken | None) -> tuple[AuthToken, DashboardToken]:
    if token is None:
        raise ProblemException(
            status=401,
            title="Authentication required",
            detail="This endpoint requires token authentication.",
        )
    if not isinstance(token.details, DashboardToken) or token.details.disabled:
        raise ProblemException(
            status=401,
            title="Authentication required",
            detail="The provided token is not valid for dashboard access.",
        )
    return token, token.details


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
    token, token_details = _dashboard_token(api_context.token)
    user_permissions = api_context.config.user_permissions()

    try:
        with impersonate_dashboard_token_issuer(
            token.issuer, token_details, user_permissions
        ) as issuer:
            dashboard = issuer.load_dashboard()
            widget_config = get_dashboard_widget_by_id(dashboard, body.widget_id)
            try:
                discovered = discover_widget_graphs(
                    widget_config,
                    dashboard.get("context"),
                    debug=api_context.config.debug,
                    user_permissions=user_permissions,
                )
            except MKLivestatusException as exc:
                raise ProblemException(
                    status=503,
                    title="Monitoring data source unavailable",
                    detail=str(exc),
                ) from exc
            except (MKMissingDataError, MKUserError, WidgetRenderError) as exc:
                raise ProblemException(
                    status=404,
                    title="No graph data available",
                    detail=str(exc),
                ) from exc

            # The widget renders the first discovered graph, so that is the one to fetch.
            if not discovered.graphs:
                raise ProblemException(
                    status=404,
                    title="No graph data available",
                    detail=discovered.no_data_message or "The widget has no graph to fetch.",
                )

            return evaluate_graph_to_response(
                serialize_graphs([discovered.graphs[0].graph]),
                requested_time_range=body.requested_time_range,
                consolidation_function=body.consolidation_function,
                combination_mode=_combination_mode(widget_config),
            )
    except InvalidWidgetError as exc:
        if exc.disable_token:
            disable_dashboard_token_by_id(token.token_id)
        raise ProblemException(
            status=404,
            title="Widget not found",
            detail=str(exc),
        ) from exc


ENDPOINT_FETCH_WIDGET_GRAPH_DATA = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=domain_type_action_href(domain_type="dashboard", action="fetch-widget-graph-data"),
        link_relation="cmk/fetch_dashboard_widget_graph_data",
        method="post",
    ),
    permissions=EndpointPermissions(),
    doc=EndpointDoc(family=DASHBOARD_FAMILY.name),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=fetch_widget_graph_data_v1)},
    allowed_tokens={"dashboard"},
)
