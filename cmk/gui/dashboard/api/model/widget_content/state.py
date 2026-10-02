#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from abc import ABC
from collections.abc import Iterable, Mapping
from typing import Literal, override, Self

from pydantic_core import ErrorDetails

from cmk.gui.dashboard.type_defs import StateDashletConfig, StatusDisplay
from cmk.gui.openapi.framework import ApiContext
from cmk.gui.openapi.framework.model import api_field, api_model, ApiOmitted
from cmk.gui.type_defs import DashboardEmbeddedViewSpec

from ..contextual_link import (
    contextual_link_from_internal,
    contextual_link_to_internal,
    ContextualLinkSpec,
    iter_contextual_link_target_errors,
)
from ._base import BaseWidgetContent


@api_model
class StateStatusDisplayBackground:
    type: Literal["background"] = api_field(
        description="Display the state with a background color."
    )
    for_states: Literal["all", "not_ok"] = api_field(
        description="Display all states or only not OK states."
    )


def _status_display_from_internal(
    value: StatusDisplay,
) -> StateStatusDisplayBackground | ApiOmitted:
    match value:
        case None:
            return ApiOmitted()
        case ("background", for_states):
            return StateStatusDisplayBackground(type="background", for_states=for_states)
    # TODO: change to `assert_never` once mypy can handle it correctly
    raise ValueError(f"Invalid status display: {value!r}")


def _status_display_to_internal(
    value: StateStatusDisplayBackground | ApiOmitted,
) -> StatusDisplay:
    if isinstance(value, ApiOmitted):
        return None
    return "background", value.for_states


@api_model
class _BaseStateContent(BaseWidgetContent, ABC):
    status_display: StateStatusDisplayBackground | ApiOmitted = api_field(
        description="Display the status.",
        default_factory=ApiOmitted,
    )
    show_summary: Literal["not_ok"] | ApiOmitted = api_field(
        description="Show a summary of the state.",
        default_factory=ApiOmitted,
    )
    contextual_link: ContextualLinkSpec = api_field(description="Where a click on the state leads.")

    @override
    def configured_contextual_link(self) -> ContextualLinkSpec:
        return self.contextual_link

    @override
    def to_internal(self) -> StateDashletConfig:
        config = StateDashletConfig(
            type=self.internal_type(),
            status_display=_status_display_to_internal(self.status_display),
            show_summary=ApiOmitted.to_optional(self.show_summary),
        )
        if (link := contextual_link_to_internal(self.contextual_link)) is not None:
            config["contextual_link"] = link
        return config

    @override
    def iter_validation_errors(
        self,
        location: tuple[str | int, ...],
        context: ApiContext,
        *,
        embedded_views: Mapping[str, DashboardEmbeddedViewSpec],
    ) -> Iterable[ErrorDetails]:
        return iter_contextual_link_target_errors(
            self.contextual_link,
            location + ("contextual_link",),
            context.config.user_permissions(),
        )


@api_model
class HostStateContent(_BaseStateContent):
    type: Literal["host_state"] = api_field(description="Displays the state of a host.")

    @classmethod
    @override
    def internal_type(cls) -> str:
        return "state_host"

    @classmethod
    def from_internal(cls, config: StateDashletConfig) -> Self:
        return cls(
            type="host_state",
            status_display=_status_display_from_internal(config.get("status_display")),
            show_summary=ApiOmitted.from_optional(config.get("show_summary")),
            contextual_link=contextual_link_from_internal(config.get("contextual_link")),
        )


@api_model
class ServiceStateContent(_BaseStateContent):
    type: Literal["service_state"] = api_field(description="Displays the state of a service.")

    @classmethod
    @override
    def internal_type(cls) -> str:
        return "state_service"

    @classmethod
    def from_internal(cls, config: StateDashletConfig) -> Self:
        return cls(
            type="service_state",
            status_display=_status_display_from_internal(config.get("status_display")),
            show_summary=ApiOmitted.from_optional(config.get("show_summary")),
            contextual_link=contextual_link_from_internal(config.get("contextual_link")),
        )
