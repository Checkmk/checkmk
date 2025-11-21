#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

###################################################################################################
### All contents of this file are only used by non-api code. As long as we depend on AJAX calls
### that get api model instances as part of their request, we need to parse these to internal
### representations.
### TODO: Remove this module once we got rid of those AJAX calls.
###################################################################################################

from dataclasses import dataclass
from typing import Annotated, NotRequired, TypedDict

from pydantic import BaseModel, Discriminator, Json, ValidationError

from cmk.gui.dashboard.dashlet.dashlets.stats import StatsDashletConfig
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
from cmk.gui.i18n import _
from cmk.gui.openapi.framework.model import ApiOmitted
from cmk.gui.pages import PageContext
from cmk.gui.type_defs import SingleInfos, VisualContext

from .model.widget import WidgetGeneralSettings
from .model.widget_content.inventory import InventoryContent
from .model.widget_content.metric import (
    AverageScatterplotContent,
    BarplotContent,
    GaugeContent,
    SingleMetricContent,
)
from .model.widget_content.overview import AlertOverviewContent, SiteOverviewContent
from .model.widget_content.state import HostStateContent, ServiceStateContent
from .model.widget_content.state_summary import HostStateSummaryContent, ServiceStateSummaryContent
from .model.widget_content.stats import EventStatsContent, HostStatsContent, ServiceStatsContent
from .model.widget_content.timeline import AlertTimelineContent, NotificationTimelineContent

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


class _WidgetTitleInternal(TypedDict, total=True):
    text: str
    url: NotRequired[str]
    render_mode: str


class _WidgetGeneralSettingsInternal(TypedDict, total=True):
    title: NotRequired[_WidgetTitleInternal]
    render_background: bool


def _general_settings_to_internal(
    gs_api: WidgetGeneralSettings,
) -> _WidgetGeneralSettingsInternal:
    if not isinstance(gs_api.title, ApiOmitted):
        if not isinstance(gs_api.title.url, ApiOmitted):
            title = _WidgetTitleInternal(
                text=gs_api.title.text,
                render_mode=gs_api.title.render_mode,
                url=gs_api.title.url,
            )
        else:
            title = _WidgetTitleInternal(
                text=gs_api.title.text,
                render_mode=gs_api.title.render_mode,
            )

        return _WidgetGeneralSettingsInternal(
            title=title,
            render_background=gs_api.render_background,
        )

    return _WidgetGeneralSettingsInternal(
        render_background=gs_api.render_background,
    )


@dataclass
class FigureRequestInternal:
    figure_config: FigureDashletConfig
    context: VisualContext
    single_infos: SingleInfos
    general_settings: _WidgetGeneralSettingsInternal


class _FigureRequest(BaseModel, frozen=True):
    content: Annotated[FigureContent, Json]
    context: Annotated[VisualContext, Json]
    single_infos: Annotated[SingleInfos, Json]
    general_settings: Annotated[WidgetGeneralSettings, Json]

    def to_internal(self) -> FigureRequestInternal:
        return FigureRequestInternal(
            figure_config=self.content.to_internal(),
            context=self.context,
            single_infos=self.single_infos,
            general_settings=_general_settings_to_internal(self.general_settings),
        )


def get_validated_internal_figure_request(
    ctx: PageContext,
) -> FigureRequestInternal:
    request_dict = {}
    for key in ["content", "context", "single_infos", "general_settings"]:
        val = ctx.request.get_str_input(key)
        if val is None:
            raise MKUserError(key, _("Missing request variable '%s'") % key)
        request_dict[key] = val

    try:
        return _FigureRequest.model_validate(request_dict).to_internal()
    except ValidationError as exc:
        raise MKUserError("figure_request_validation", str(exc))
