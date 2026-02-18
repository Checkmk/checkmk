#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Token-auth graph hover endpoint for shared dashboards."""

from __future__ import annotations

from typing import cast, override

from cmk.gui.dashboard.api import GraphDashletConfig
from cmk.gui.dashboard.api.model.widget_content import content_from_internal
from cmk.gui.dashboard.api.model.widget_content.graph import (
    CombinedGraphContent,
    CustomGraphContent,
    PerformanceGraphContent,
    ProblemGraphContent,
    SingleTimeseriesContent,
)
from cmk.gui.dashboard.dashlet.dashlets.graph import ABCGraphDashlet
from cmk.gui.dashboard.dashlet.registry import dashlet_registry
from cmk.gui.dashboard.token_util import (
    DashboardTokenAuthenticatedPage,
    get_dashboard_widget_by_id,
    impersonate_dashboard_token_issuer,
    InvalidWidgetError,
)
from cmk.gui.dashboard.type_defs import ABCGraphDashletConfig
from cmk.gui.graphing._graph_render_config import GraphRenderConfigBase
from cmk.gui.graphing._graph_specification import GraphSpecification
from cmk.gui.graphing._html_render import make_graph_data_range, render_graph_hover_for_recipe
from cmk.gui.pages import PageContext, PageResult
from cmk.gui.permissions import permission_registry
from cmk.gui.token_auth import AuthToken, DashboardToken
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.valuespec import Timerange

__all__ = ["GraphHoverTokenAuthPage"]

_ALLOWED_GRAPH_TYPES: frozenset[str] = frozenset(
    {
        CombinedGraphContent.internal_type(),
        CustomGraphContent.internal_type(),
        PerformanceGraphContent.internal_type(),
        ProblemGraphContent.internal_type(),
        SingleTimeseriesContent.internal_type(),
    }
)


class GraphHoverTokenAuthPage(DashboardTokenAuthenticatedPage):
    """Graph hover data for shared dashboards via token auth."""

    @classmethod
    def ident(cls) -> str:
        return "ajax_graph_hover_token_auth"

    @override
    def _post(
        self, token: AuthToken, token_details: DashboardToken, ctx: PageContext
    ) -> PageResult:
        widget_id = ctx.request.get_str_input_mandatory("widget_id")
        user_permissions = UserPermissions.from_config(ctx.config, permission_registry)
        with impersonate_dashboard_token_issuer(
            token.issuer, token_details, user_permissions
        ) as issuer:
            dashboard = issuer.load_dashboard()

            # IDOR prevention
            widget_config = get_dashboard_widget_by_id(dashboard, widget_id)

            # Only graph-type widgets are permitted
            if widget_config["type"] not in _ALLOWED_GRAPH_TYPES:
                raise InvalidWidgetError()

            # Build dashlet config from the stored widget (server-side), same as
            # GraphWidgetTokenAuthPage — ensures graph render option defaults are applied.
            updated_widget_config = content_from_internal(widget_config).to_internal()
            updated_widget_config.update(
                {
                    "context": widget_config.get("context", {}),
                    "single_infos": widget_config.get("single_infos", []),
                }
            )
            graph_dashlet_config = cast(GraphDashletConfig, updated_widget_config)

            try:
                dashlet_type = cast(
                    type[ABCGraphDashlet[ABCGraphDashletConfig, GraphSpecification]],
                    dashlet_registry[updated_widget_config["type"]],
                )
            except KeyError:
                raise InvalidWidgetError(disable_token=True) from None

            dashlet = dashlet_type(
                graph_dashlet_config,
                dashboard.get("context"),  # dashboard-level base context
            )
            recipes = dashlet.graph_recipes()

            if not recipes:
                raise InvalidWidgetError()

            # Time range and step both come from the stored widget config (server-side).
            # Zoom/pan is disabled on shared dashboards so the step never changes after render.
            start_time, end_time = Timerange.compute_range(graph_dashlet_config["timerange"]).range
            height_in_ex = graph_dashlet_config.get("graph_render_options", {}).get(
                "size", GraphRenderConfigBase.model_fields["size"].default
            )[1]
            graph_data_range = make_graph_data_range((start_time, end_time), height_in_ex)

            render_graph_hover_for_recipe(ctx, recipes[0], graph_data_range)

        return None
