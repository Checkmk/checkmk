#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from abc import ABC
from collections.abc import Iterable, Mapping
from typing import Annotated, Literal, override, Self

from pydantic import Discriminator
from pydantic_core import ErrorDetails

from cmk.gui.dashboard.event_bar_chart_window import exceeds_event_bar_chart_span
from cmk.gui.dashboard.type_defs import (
    DashboardWindow,
    EventBarChartDashletConfig,
    EventBarChartRenderBarChart,
    EventBarChartRenderMode,
    EventBarChartRenderSimpleNumber,
    FixedWindow,
)
from cmk.gui.fields.attributes import MappingConverter
from cmk.gui.openapi.framework import ApiContext
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.framework.model.common_fields import timerange_from_internal, TimerangeModel
from cmk.gui.type_defs import DashboardEmbeddedViewSpec
from cmk.gui.valuespec import Timerange

from ._base import BaseWidgetContent

type TimeResolution = Literal["hour", "day"]
type TimelineWindow = Literal["dashboard"] | TimerangeModel
_RESOLUTION_CONVERTER = MappingConverter[TimeResolution, Literal["h", "d"]](
    {
        "hour": "h",
        "day": "d",
    }
)

TIMELINE_SPAN_ERROR = "The time range must not span more than two years."


_WINDOW_DESCRIPTION = "The time range to count over, or `dashboard` to follow the dashboard."


def _window_to_internal(window: TimelineWindow) -> DashboardWindow | FixedWindow:
    if window == "dashboard":
        return DashboardWindow(type="dashboard")
    return FixedWindow(type="range", window=window.to_internal())


def _window_from_internal(window: DashboardWindow | FixedWindow) -> TimelineWindow:
    if window["type"] == "dashboard":
        return "dashboard"
    return timerange_from_internal(window["window"])


@api_model
class BarChartRenderMode:
    type: Literal["bar_chart"] = api_field(description="Renders a bar chart.")
    time_range: TimelineWindow = api_field(description=_WINDOW_DESCRIPTION)
    time_resolution: TimeResolution = api_field(
        description="Select a time period over which the alerts or notifications are added up"
    )

    @classmethod
    def from_internal(cls, config: EventBarChartRenderBarChart) -> Self:
        return cls(
            type="bar_chart",
            time_range=_window_from_internal(config["time_range"]),
            time_resolution=_RESOLUTION_CONVERTER.from_checkmk(config["time_resolution"]),
        )

    def to_internal(self) -> EventBarChartRenderMode:
        return (
            "bar_chart",
            EventBarChartRenderBarChart(
                time_range=_window_to_internal(self.time_range),
                time_resolution=_RESOLUTION_CONVERTER.to_checkmk(self.time_resolution),
            ),
        )


@api_model
class SimpleNumberRenderMode:
    type: Literal["simple_number"] = api_field(description="Renders a simple number.")
    time_range: TimelineWindow = api_field(description=_WINDOW_DESCRIPTION)

    def to_internal(self) -> EventBarChartRenderMode:
        return (
            "simple_number",
            EventBarChartRenderSimpleNumber(
                time_range=_window_to_internal(self.time_range),
            ),
        )


type RenderMode = Annotated[
    BarChartRenderMode | SimpleNumberRenderMode,
    Discriminator("type"),
]


def _render_mode_from_internal(
    value: EventBarChartRenderMode,
) -> RenderMode:
    match value:
        case ("bar_chart", config):
            return BarChartRenderMode.from_internal(config)
        case ("simple_number", config):
            return SimpleNumberRenderMode(
                type="simple_number",
                time_range=_window_from_internal(config["time_range"]),
            )
        case x:
            # TODO: change to `assert_never` once mypy can handle it correctly
            raise ValueError(f"Invalid render mode: {x!r}")


@api_model
class _BaseTimelineContent(BaseWidgetContent, ABC):
    render_mode: RenderMode = api_field(
        description="Defines how the timeline should be rendered.",
    )
    log_target: Literal["both", "host", "service"] = api_field(
        description="Defines which log target to use for the timeline.",
    )

    @override
    def iter_validation_errors(
        self,
        location: tuple[str | int, ...],
        context: ApiContext,
        *,
        embedded_views: Mapping[str, DashboardEmbeddedViewSpec],
    ) -> Iterable[ErrorDetails]:
        window = self.render_mode.time_range
        if window == "dashboard":
            return
        stored = window.to_internal()
        start, end = Timerange.compute_range(stored).range
        if exceeds_event_bar_chart_span(start, end):
            yield ErrorDetails(
                type="value_error",
                msg=TIMELINE_SPAN_ERROR,
                loc=location + ("render_mode", "time_range"),
                input=stored,
            )

    @override
    def to_internal(self) -> EventBarChartDashletConfig:
        return EventBarChartDashletConfig(
            type=self.internal_type(),
            render_mode=self.render_mode.to_internal(),
            log_target=self.log_target,
        )


@api_model
class AlertTimelineContent(_BaseTimelineContent):
    type: Literal["alert_timeline"] = api_field(description="Displays host and service alerts.")

    @classmethod
    @override
    def internal_type(cls) -> str:
        return "alerts_bar_chart"

    @classmethod
    def from_internal(cls, config: EventBarChartDashletConfig) -> Self:
        return cls(
            type="alert_timeline",
            render_mode=_render_mode_from_internal(config["render_mode"]),
            log_target=config["log_target"],
        )


@api_model
class NotificationTimelineContent(_BaseTimelineContent):
    type: Literal["notification_timeline"] = api_field(
        description="Displays host and service notifications.",
    )

    @classmethod
    @override
    def internal_type(cls) -> str:
        return "notifications_bar_chart"

    @classmethod
    def from_internal(cls, config: EventBarChartDashletConfig) -> Self:
        return cls(
            type="notification_timeline",
            render_mode=_render_mode_from_internal(config["render_mode"]),
            log_target=config["log_target"],
        )
