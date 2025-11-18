#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

import json
from collections.abc import Callable, Mapping
from typing import Annotated, override

from pydantic import Discriminator, TypeAdapter, ValidationError

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
from cmk.gui.dashboard.dashlet.base import T
from cmk.gui.dashboard.dashlet.dashlets.stats import (
    EventStatsDashletDataGenerator,
    HostStatsDashletDataGenerator,
    ServiceStatsDashletDataGenerator,
    StatsDashletConfig,
)
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
from cmk.gui.figures import create_figures_response, FigureResponseData
from cmk.gui.http import Request
from cmk.gui.i18n import _
from cmk.gui.pages import AjaxPage, PageContext, PageResult
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


def get_figure_config(request: Request) -> FigureDashletConfig:
    content_str = request.get_ascii_input_mandatory("content")
    adapter: TypeAdapter[FigureContent] = TypeAdapter(  # nosemgrep: type-adapter-detected
        FigureContent
    )
    try:
        content_model = adapter.validate_json(content_str)
    except ValidationError as e:
        raise MKUserError("content", _("Invalid figure content: %s") % e) from e
    return content_model.to_internal()


GENERATOR_BY_FIGURE_TYPE: Mapping[
    str,
    Callable[..., FigureResponseData],
] = {
    "eventstats": EventStatsDashletDataGenerator.generate_response_data,
    "hoststats": HostStatsDashletDataGenerator.generate_response_data,
    "servicestats": ServiceStatsDashletDataGenerator.generate_response_data,
}


class FigureWidgetPage(AjaxPage):
    @classmethod
    def ident(cls) -> str:
        return "widget_figure"

    def get_response_data_by_figure_type(
        self,
        figure_type_name: str,
        figure_config: T,
        context: VisualContext,
        single_infos: SingleInfos,
    ) -> FigureResponseData:
        if not (generator := GENERATOR_BY_FIGURE_TYPE.get(figure_type_name)):
            raise KeyError(
                _("No data generator found for figure type name '%s'") % figure_type_name
            )
        return generator(figure_config, context, single_infos)

    @override
    def page(self, ctx: PageContext) -> PageResult:
        figure_config: FigureDashletConfig = get_figure_config(ctx.request)
        context: VisualContext = json.loads(ctx.request.get_ascii_input_mandatory("context"))
        single_infos: SingleInfos = json.loads(
            ctx.request.get_ascii_input_mandatory("single_infos")
        )
        general_settings = json.loads(ctx.request.get_ascii_input_mandatory("general_settings"))
        figure_config.update(
            {
                "context": context,
                "single_infos": single_infos,
            }
        )
        if (title := general_settings.get("title")) is not None and title[
            "render_mode"
        ] != "hidden":
            figure_config.update(
                {
                    "title": title["text"],
                    "title_url": title.get("url"),
                }
            )

        return create_figures_response(
            self.get_response_data_by_figure_type(
                figure_config["type"], figure_config, context, single_infos
            )
        )
