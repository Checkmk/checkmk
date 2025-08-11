#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Literal, override, Self

from cmk.gui.dashboard.dashlet import StatsDashletConfig
from cmk.gui.openapi.framework.model import api_field, api_model

from ._base import BaseWidgetContent


@api_model
class HostStatsContent(BaseWidgetContent):
    type: Literal["host_stats"] = api_field(
        description="Displays statistics about host states as a hexagon and a table."
    )

    @classmethod
    @override
    def internal_type(cls) -> str:
        return "hoststats"

    @classmethod
    def from_internal(cls, _config: StatsDashletConfig) -> Self:
        return cls(type="host_stats")

    @override
    def to_internal(self) -> StatsDashletConfig:
        return StatsDashletConfig(type=self.internal_type())


@api_model
class ServiceStatsContent(BaseWidgetContent):
    type: Literal["service_stats"] = api_field(
        description="Displays statistics about service states as a hexagon and a table."
    )

    @classmethod
    @override
    def internal_type(cls) -> str:
        return "servicestats"

    @classmethod
    def from_internal(cls, _config: StatsDashletConfig) -> Self:
        return cls(type="service_stats")

    @override
    def to_internal(self) -> StatsDashletConfig:
        return StatsDashletConfig(type=self.internal_type())


@api_model
class EventStatsContent(BaseWidgetContent):
    # NOTE: internally "eventstats", must be used in `to_internal`
    type: Literal["event_stats"] = api_field(
        description="Displays statistics about events as a hexagon and a table."
    )

    @classmethod
    @override
    def internal_type(cls) -> str:
        return "eventstats"

    @classmethod
    def from_internal(cls, _config: StatsDashletConfig) -> Self:
        return cls(type="event_stats")

    @override
    def to_internal(self) -> StatsDashletConfig:
        return StatsDashletConfig(type=self.internal_type())
