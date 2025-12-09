#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from typing import cast, override

import cmk.gui.pages
from cmk.ccc.user import UserId
from cmk.ccc.version import edition
from cmk.gui.dashboard.api import (
    get_validated_internal_graph_request,
    GraphDashletConfig,
    GraphRequestInternal,
)
from cmk.gui.dashboard.dashlet.dashlets.graph import ABCGraphDashlet
from cmk.gui.dashboard.dashlet.registry import dashlet_registry
from cmk.gui.dashboard.token_util import (
    DashboardTokenAuthenticatedPage,
    get_dashboard_widget_by_id,
    impersonate_dashboard_token_issuer,
    InvalidWidgetError,
)
from cmk.gui.dashboard.type_defs import DashboardConfig
from cmk.gui.graphing import (
    get_temperature_unit,
    GraphRenderConfig,
    graphs_from_api,
    host_service_graph_dashlet_cmk,
    metric_backend_registry,
    metrics_from_api,
)
from cmk.gui.htmllib.html import html
from cmk.gui.logged_in import user
from cmk.gui.pages import PageContext
from cmk.gui.permissions import permission_registry
from cmk.gui.theme.current_theme import theme
from cmk.gui.token_auth import AuthToken, DashboardToken
from cmk.gui.utils.roles import UserPermissions
from cmk.utils import paths

__all__ = ["GraphWidgetPage"]


def render_graph_widget_content(
    ctx: PageContext,
    dashlet_config: GraphDashletConfig,
    widget_id: str,
) -> None:
    dashlet_type = cast(type[ABCGraphDashlet], dashlet_registry[dashlet_config["type"]])

    # create a dummy dashboard, so that we can create the dashlet instance
    dashboard = DashboardConfig(
        owner=UserId.builtin(),
        name="dummy-dashboard",
        context={},
        single_infos=[],
        add_context_to_title=False,
        title="Dummy Dashboard",
        description="",
        topic="",
        sort_index=0,
        is_show_more=False,
        icon=None,
        hidden=False,
        hidebutton=False,
        public=False,
        packaged=False,
        link_from={},
        main_menu_search_terms=[],
        mtime=0,
        dashlets=[dashlet_config],
        show_title=True,
        mandatory_context_filters=[],
        embedded_views={},
    )

    graph_dashlet = dashlet_type(
        dashboard["name"], dashboard["owner"], dashboard, 0, dashlet_config
    )

    # TODO: try to build the type-specific (dashlet_config["type"]) graph_spec without the need to
    #       create dashboard and dashlet instances here. find a way to do so more directly with
    #       the given http request variables
    graph_spec = graph_dashlet.graph_specification(dashlet_config["context"])

    html.write_html(
        host_service_graph_dashlet_cmk(
            # TODO: try replacing this passing on of ctx.request by adding it to
            #       get_validated_internal_graph_request.
            #       for that we need to adapt host_service_graph_dashlet_cmk and its call sites
            ctx.request,
            graph_spec,
            GraphRenderConfig.model_validate(
                dashlet_config["graph_render_options"]
                | {"foreground_color": ("#ffffff" if theme.get() == "modern-dark" else "#000000")}
            ),
            metrics_from_api,
            graphs_from_api,
            UserPermissions.from_config(ctx.config, permission_registry),
            debug=ctx.config.debug,
            graph_timeranges=ctx.config.graph_timeranges,
            temperature_unit=get_temperature_unit(user, ctx.config.default_temperature_unit),
            backend_time_series_fetcher=metric_backend_registry[
                str(edition(paths.omd_root))
            ].get_time_series_fetcher(ctx.config),
            graph_display_id=widget_id,
            time_range=dashlet_config["timerange"],
        )
    )


class GraphWidgetPage(cmk.gui.pages.Page):
    @override
    def page(self, ctx: PageContext) -> None:
        try:
            request_data: GraphRequestInternal = get_validated_internal_graph_request(ctx)
            dashlet_config: GraphDashletConfig = request_data.dashlet_config
            dashlet_config.update(
                {
                    "context": request_data.context,
                    "single_infos": request_data.single_infos,
                }
            )

            render_graph_widget_content(ctx, dashlet_config, request_data.widget_id)
        except Exception as e:
            html.write_html(html.render_message(str(e)))


class GraphWidgetTokenAuthPage(DashboardTokenAuthenticatedPage):
    @classmethod
    def ident(cls) -> str:
        return "widget_graph_token_auth"

    @override
    def _post(self, token: AuthToken, token_details: DashboardToken, ctx: PageContext) -> None:
        widget_id = ctx.request.get_str_input_mandatory("widget_id")
        user_permissions = UserPermissions.from_config(ctx.config, permission_registry)
        with impersonate_dashboard_token_issuer(
            token.issuer, token_details, user_permissions
        ) as issuer:
            dashboard = issuer.load_dashboard()
            widget_config = get_dashboard_widget_by_id(dashboard, widget_id)
            if widget_config["type"] not in (
                "combined_graph",
                "custom_graph",
                "performance_graph",
                "problem_graph",
                "single_timeseries",
            ):
                raise InvalidWidgetError()

            try:
                # this also requires the impersonation context
                render_graph_widget_content(ctx, cast(GraphDashletConfig, widget_config), widget_id)
            except KeyError:
                # likely an edition downgrade where the graph type is not available anymore
                raise InvalidWidgetError(disable_token=True) from None
