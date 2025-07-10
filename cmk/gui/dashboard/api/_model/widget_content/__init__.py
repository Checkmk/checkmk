#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Annotated, Literal, override, Self

from pydantic import Discriminator, model_validator

from cmk.gui.dashboard import DashletConfig
from cmk.gui.openapi.framework.model import api_field, api_model

from ._base import BaseWidgetContent
from .graph import (
    CombinedGraphContent,
    CustomGraphContent,
    PerformanceGraphContent,
    ProblemGraphContent,
    SingleTimeseriesContent,
)
from .inventory import InventoryContent
from .metric import (
    AverageScatterplotContent,
    BarplotContent,
    GaugeContent,
    SingleMetricContent,
    TopListContent,
)
from .ntop import NtopAlertsContent, NtopFlowsContent, NtopTopTalkersContent
from .overview import AlertOverviewContent, SiteOverviewContent
from .sidebar import SidebarElementContent
from .state import HostStateContent, ServiceStateContent
from .state_summary import HostStateSummaryContent, ServiceStateSummaryContent
from .stats import EventStatsContent, HostStatsContent, ServiceStatsContent
from .text import StaticTextContent
from .timeline import AlertTimelineContent, NotificationTimelineContent
from .url import URLContent
from .user_messages import UserMessagesContent
from .view import EmbeddedViewContent, LinkedViewContent


@api_model
class NotSupportedContent(BaseWidgetContent):
    type: Literal["not_supported"] = api_field(
        description="Content type that is no longer supported."
    )
    original_type: str = api_field(description="Internal name of the unsupported content type.")

    @classmethod
    @override
    def internal_type(cls) -> str:
        raise ValueError("NotSupportedContent does not have an internal type.")

    @override
    @model_validator(mode="after")
    def _validate(self) -> Self:
        # error during create/update requests, this also overwrites the version check
        raise ValueError("Cannot use unsupported content type.")

    @override
    def to_internal(self) -> DashletConfig:
        # this shouldn't happen anyway, since this shouldn't be used for create/update requests
        raise ValueError("NotSupportedContent cannot be converted to internal config.")


type WidgetContent = Annotated[
    StaticTextContent
    | LinkedViewContent
    | EmbeddedViewContent
    | ProblemGraphContent
    | CombinedGraphContent
    | SingleTimeseriesContent
    | CustomGraphContent
    | PerformanceGraphContent
    | BarplotContent
    | GaugeContent
    | SingleMetricContent
    | AverageScatterplotContent
    | TopListContent
    | HostStateContent
    | ServiceStateContent
    | HostStateSummaryContent
    | ServiceStateSummaryContent
    | InventoryContent
    | AlertOverviewContent
    | SiteOverviewContent
    | HostStatsContent
    | ServiceStatsContent
    | EventStatsContent
    | AlertTimelineContent
    | NotificationTimelineContent
    | UserMessagesContent
    | SidebarElementContent
    | URLContent
    | NtopAlertsContent
    | NtopFlowsContent
    | NtopTopTalkersContent
    | NotSupportedContent,
    Discriminator("type"),
]

_CONTENT_TYPES = (
    StaticTextContent,
    LinkedViewContent,
    EmbeddedViewContent,
    ProblemGraphContent,
    CombinedGraphContent,
    SingleTimeseriesContent,
    CustomGraphContent,
    PerformanceGraphContent,
    BarplotContent,
    GaugeContent,
    SingleMetricContent,
    AverageScatterplotContent,
    TopListContent,
    HostStateContent,
    ServiceStateContent,
    HostStateSummaryContent,
    ServiceStateSummaryContent,
    InventoryContent,
    AlertOverviewContent,
    SiteOverviewContent,
    HostStatsContent,
    ServiceStatsContent,
    EventStatsContent,
    AlertTimelineContent,
    NotificationTimelineContent,
    UserMessagesContent,
    SidebarElementContent,
    URLContent,
    NtopAlertsContent,
    NtopFlowsContent,
    NtopTopTalkersContent,
)


def content_from_internal(config: DashletConfig) -> WidgetContent:
    type_ = config["type"]
    for content_type in _CONTENT_TYPES:
        if content_type.internal_type() == type_:
            return content_type.from_internal(config)  # type: ignore[arg-type]

    return NotSupportedContent(type="not_supported", original_type=type_)
