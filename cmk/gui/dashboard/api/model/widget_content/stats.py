#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from abc import ABC
from typing import Literal, override, Self

from cmk.gui.dashboard.type_defs import StatsDashletConfig
from cmk.gui.openapi.framework.model import api_field, api_model

from ..context_filters import (
    AggregateHostContextFilter,
    AggregateServiceContextFilter,
    host_filter_from_internal,
    service_filter_from_internal,
)
from ..contextual_link import (
    AnyContextualLinkSpec,
    contextual_link_from_internal,
    contextual_link_to_internal,
    ContextualLinkSpec,
)
from ._base import BaseWidgetContent


@api_model
class _LinkedStatsContent(BaseWidgetContent, ABC):
    @override
    def to_internal(self) -> StatsDashletConfig:
        config = StatsDashletConfig(type=self.internal_type())
        if (link := contextual_link_to_internal(self.configured_contextual_link())) is not None:
            config["contextual_link"] = link
        return config


@api_model
class HostStatsContent(_LinkedStatsContent):
    type: Literal["host_stats"] = api_field(
        description="Displays statistics about host states as a hexagon and a table."
    )
    contextual_link: ContextualLinkSpec[AggregateHostContextFilter] = api_field(
        description="Where a click on a part leads."
    )

    @classmethod
    @override
    def internal_type(cls) -> str:
        return "hoststats"

    @classmethod
    def from_internal(cls, config: StatsDashletConfig) -> Self:
        return cls(
            type="host_stats",
            contextual_link=contextual_link_from_internal(
                config.get("contextual_link"), host_filter_from_internal
            ),
        )

    @override
    def configured_contextual_link(self) -> AnyContextualLinkSpec:
        return self.contextual_link


@api_model
class ServiceStatsContent(_LinkedStatsContent):
    type: Literal["service_stats"] = api_field(
        description="Displays statistics about service states as a hexagon and a table."
    )
    contextual_link: ContextualLinkSpec[AggregateServiceContextFilter] = api_field(
        description="Where a click on a part leads."
    )

    @classmethod
    @override
    def internal_type(cls) -> str:
        return "servicestats"

    @classmethod
    def from_internal(cls, config: StatsDashletConfig) -> Self:
        return cls(
            type="service_stats",
            contextual_link=contextual_link_from_internal(
                config.get("contextual_link"), service_filter_from_internal
            ),
        )

    @override
    def configured_contextual_link(self) -> AnyContextualLinkSpec:
        return self.contextual_link


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
