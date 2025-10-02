#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import Annotated, cast, override

from pydantic import Discriminator, TypeAdapter, ValidationError

import cmk.gui.pages
from cmk.ccc.user import UserId
from cmk.gui.config import Config
from cmk.gui.dashboard.api.model.widget_content.graph import (
    CombinedGraphContent,
    CustomGraphContent,
    PerformanceGraphContent,
    ProblemGraphContent,
    SingleTimeseriesContent,
)
from cmk.gui.dashboard.dashlet.dashlets.graph import (
    ABCGraphDashlet,
    TemplateGraphDashletConfig,
)
from cmk.gui.dashboard.dashlet.registry import dashlet_registry
from cmk.gui.dashboard.type_defs import (
    CombinedGraphDashletConfig,
    CustomGraphDashletConfig,
    DashboardConfig,
    ProblemsGraphDashletConfig,
    SingleTimeseriesDashletConfig,
)
from cmk.gui.exceptions import MKUserError
from cmk.gui.graphing._from_api import graphs_from_api, metrics_from_api
from cmk.gui.graphing._graph_render_config import GraphRenderConfig
from cmk.gui.graphing._html_render import host_service_graph_dashlet_cmk
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.permissions import permission_registry
from cmk.gui.theme.current_theme import theme
from cmk.gui.type_defs import SingleInfos, VisualContext
from cmk.gui.utils.roles import UserPermissions

__all__ = ["GraphWidgetPage"]


type GraphContent = Annotated[
    CombinedGraphContent
    | CustomGraphContent
    | PerformanceGraphContent
    | ProblemGraphContent
    | SingleTimeseriesContent,
    Discriminator("type"),
]

type GraphDashletConfig = (
    CombinedGraphDashletConfig
    | CustomGraphDashletConfig
    | ProblemsGraphDashletConfig
    | SingleTimeseriesDashletConfig
    | TemplateGraphDashletConfig  # corresponds to PerformanceGraphContent ("pnpgraph")
)


def _get_graph_config() -> GraphDashletConfig:
    content_str = request.get_ascii_input_mandatory("content")
    adapter: TypeAdapter[GraphContent] = TypeAdapter(  # nosemgrep: type-adapter-detected
        GraphContent
    )
    try:
        content_model = adapter.validate_json(content_str)
    except ValidationError as e:
        raise MKUserError("content", _("Invalid graph content: %s") % e) from e
    return content_model.to_internal()


class GraphWidgetPage(cmk.gui.pages.Page):
    @override
    def page(self, config: Config) -> None:
        widget_id = request.get_str_input_mandatory("widget_id")
        graph_config: GraphDashletConfig = _get_graph_config()

        dashlet_type = cast(type[ABCGraphDashlet], dashlet_registry[graph_config["type"]])

        context: VisualContext = json.loads(request.get_ascii_input_mandatory("context"))
        single_infos: SingleInfos = json.loads(request.get_ascii_input_mandatory("single_infos"))

        graph_config["context"] = context
        graph_config["single_infos"] = single_infos

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
            dashlets=[graph_config],
            show_title=True,
            mandatory_context_filters=[],
        )

        graph_dashlet = dashlet_type(
            dashboard["name"], dashboard["owner"], dashboard, 0, graph_config
        )

        # TODO: try to build the type-specific (graph_config["type"]) graph_spec without the need to
        #       create dashboard and dashlet instances here. find a way to do so more directly with
        #       the given http request variables
        graph_spec = graph_dashlet.graph_specification(context)

        try:
            html.write_html(
                host_service_graph_dashlet_cmk(
                    graph_spec,
                    GraphRenderConfig.model_validate(
                        graph_config["graph_render_options"]
                        | {
                            "foreground_color": (
                                "#ffffff" if theme.get() == "modern-dark" else "#000000"
                            )
                        }
                    ),
                    metrics_from_api,
                    graphs_from_api,
                    UserPermissions.from_config(config, permission_registry),
                    debug=config.debug,
                    graph_timeranges=config.graph_timeranges,
                    graph_display_id=widget_id,
                    time_range=graph_config["timerange"],
                )
            )
        except Exception as e:
            html.write_html(html.render_message(str(e)))
