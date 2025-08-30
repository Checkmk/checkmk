#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from abc import ABC
from typing import Annotated, cast, Literal, override, Self

from pydantic import Discriminator

from cmk.gui.dashboard.type_defs import (
    EventBarChartDashletConfig,
    EventBarChartRenderBarChart,
    EventBarChartRenderMode,
    EventBarChartRenderSimpleNumber,
)
from cmk.gui.fields.attributes import MappingConverter
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.framework.model.common_fields import timerange_from_internal, TimerangeModel

from ._base import BaseWidgetContent

type TimeResolution = Literal["hour", "day"]
_RESOLUTION_CONVERTER = MappingConverter[TimeResolution, Literal["h", "d"]](
    {
        "hour": "h",
        "day": "d",
    }
)


@api_model
class BarChartRenderMode:
    type: Literal["bar_chart"] = api_field(description="Renders a bar chart.")
    time_range: TimerangeModel = api_field(description="The time range for the bar chart.")
    time_resolution: TimeResolution = api_field(
        description="Select a time period over which the alerts or notifications are added up"
    )

    @classmethod
    def from_internal(cls, config: EventBarChartRenderBarChart) -> Self:
        return cls(
            type="bar_chart",
            time_range=timerange_from_internal(config["time_range"]),
            time_resolution=_RESOLUTION_CONVERTER.from_checkmk(config["time_resolution"]),
        )

    def to_internal(self) -> EventBarChartRenderMode:
        return (
            "bar_chart",
            EventBarChartRenderBarChart(
                time_range=self.time_range.to_internal(),
                time_resolution=_RESOLUTION_CONVERTER.to_checkmk(self.time_resolution),
            ),
        )


@api_model
class SimpleNumberRenderMode:
    type: Literal["simple_number"] = api_field(description="Renders a simple number.")
    time_range: TimerangeModel = api_field(description="The time range for the simple number.")

    def to_internal(self) -> EventBarChartRenderMode:
        return (
            "simple_number",
            EventBarChartRenderSimpleNumber(
                time_range=self.time_range.to_internal(),
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
            # mypy can't handle the type narrowing here
            return BarChartRenderMode.from_internal(cast(EventBarChartRenderBarChart, config))
        case ("simple_number", config):
            # mypy can't handle the type narrowing here
            config = cast(EventBarChartRenderSimpleNumber, config)
            return SimpleNumberRenderMode(
                type="simple_number",
                time_range=timerange_from_internal(config["time_range"]),
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
