#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

import json
from typing import Annotated, cast, override

from pydantic import Discriminator, TypeAdapter, ValidationError

from cmk.ccc.user import UserId
from cmk.gui.config import Config
from cmk.gui.dashboard import DashboardConfig
from cmk.gui.dashboard.api.model.widget_content.inventory import InventoryContent
from cmk.gui.dashboard.api.model.widget_content.metric import (
    AverageScatterplotContent,
    BarplotContent,
    GaugeContent,
    SingleMetricContent,
)
from cmk.gui.dashboard.api.model.widget_content.overview import (
    AlertOverviewContent,
    SiteOverviewContent,
)
from cmk.gui.dashboard.api.model.widget_content.state import HostStateContent, ServiceStateContent
from cmk.gui.dashboard.api.model.widget_content.state_summary import (
    HostStateSummaryContent,
    ServiceStateSummaryContent,
)
from cmk.gui.dashboard.api.model.widget_content.stats import (
    EventStatsContent,
    HostStatsContent,
    ServiceStatsContent,
)
from cmk.gui.dashboard.api.model.widget_content.timeline import (
    AlertTimelineContent,
    NotificationTimelineContent,
)
from cmk.gui.dashboard.dashlet.dashlets.stats import StatsDashletConfig
from cmk.gui.dashboard.dashlet.figure_dashlet import ABCFigureDashlet
from cmk.gui.dashboard.dashlet.registry import dashlet_registry
from cmk.gui.dashboard.type_defs import (
    AlertOverviewDashletConfig,
    AverageScatterplotDashletConfig,
    BarplotDashletConfig,
    EventBarChartDashletConfig,
    GaugeDashletConfig,
    HostStateSummaryDashletConfig,
    InventoryDashletConfig,
    ServiceStateSummaryDashletConfig,
    SingleMetricDashletConfig,
    SiteOverviewDashletConfig,
    StateDashletConfig,
)
from cmk.gui.exceptions import MKUserError
from cmk.gui.figures import create_figures_response
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.pages import AjaxPage, PageResult
from cmk.gui.type_defs import SingleInfos, VisualContext

__all__ = ["FigureWidgetPage"]

type FigureContent = Annotated[
    AlertOverviewContent
    | AlertTimelineContent
    | AverageScatterplotContent
    | BarplotContent
    | EventStatsContent
    | GaugeContent
    | HostStateContent
    | HostStateSummaryContent
    | HostStatsContent
    | InventoryContent
    | NotificationTimelineContent
    | ServiceStateContent
    | ServiceStateSummaryContent
    | ServiceStatsContent
    | SingleMetricContent
    | SiteOverviewContent,
    Discriminator("type"),
]

type FigureDashletConfig = (
    AlertOverviewDashletConfig
    | AverageScatterplotDashletConfig
    | BarplotDashletConfig
    | EventBarChartDashletConfig
    | GaugeDashletConfig
    | StateDashletConfig
    | HostStateSummaryDashletConfig
    | InventoryDashletConfig
    | ServiceStateSummaryDashletConfig
    | SingleMetricDashletConfig
    | SiteOverviewDashletConfig
    | StatsDashletConfig
)


def _get_figure_config() -> FigureDashletConfig:
    content_str = request.get_ascii_input_mandatory("content")
    adapter: TypeAdapter[FigureContent] = TypeAdapter(  # nosemgrep: type-adapter-detected
        FigureContent
    )
    try:
        content_model = adapter.validate_json(content_str)
    except ValidationError as e:
        raise MKUserError("content", _("Invalid figure content: %s") % e) from e
    return content_model.to_internal()


class FigureWidgetPage(AjaxPage):
    @override
    def page(self, config: Config) -> PageResult:
        figure_config: FigureDashletConfig = _get_figure_config()
        dashlet_type = cast(type[ABCFigureDashlet], dashlet_registry[figure_config["type"]])

        # Get context from the AJAX request body (not simply from the dashboard config) to include
        # potential dashboard context given via HTTP request variables
        context: VisualContext = json.loads(request.get_ascii_input_mandatory("context"))
        single_infos: SingleInfos = json.loads(request.get_ascii_input_mandatory("single_infos"))

        figure_config["context"] = context
        figure_config["single_infos"] = single_infos

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
            dashlets=[figure_config],
            show_title=True,
            mandatory_context_filters=[],
        )

        dashlet = dashlet_type(dashboard["name"], dashboard["owner"], dashboard, 0, figure_config)

        # TODO: try to make generate_response_data a classmethod so we do not need to create
        #       dashboard and dashlet instances here, but can call that function directly with the
        #       necessary params
        return create_figures_response(dashlet.generate_response_data())
