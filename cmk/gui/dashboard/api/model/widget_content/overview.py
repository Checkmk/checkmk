#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterable, Mapping
from typing import Literal, override, Self

from pydantic_core import ErrorDetails

from cmk.gui.dashboard.type_defs import (
    AlertOverviewDashletConfig,
    DashboardWindow,
    FixedWindow,
    SiteOverviewDashletConfig,
)
from cmk.gui.openapi.framework import ApiContext
from cmk.gui.openapi.framework.model import api_field, api_model, ApiOmitted
from cmk.gui.openapi.framework.model.common_fields import timerange_from_internal, TimerangeModel
from cmk.gui.type_defs import DashboardEmbeddedViewSpec

from ..contextual_link import (
    contextual_link_from_internal,
    contextual_link_to_internal,
    ContextualLinkSpec,
    iter_contextual_link_target_errors,
)
from ._base import BaseWidgetContent


@api_model
class AlertOverviewContent(BaseWidgetContent):
    type: Literal["alert_overview"] = api_field(
        description="Displays hosts and services producing the most notifications"
    )
    time_range: Literal["dashboard"] | TimerangeModel = api_field(
        description=(
            "The time range for which the alert overview is displayed, or `dashboard` to follow"
            " the dashboard."
        ),
    )
    limit_objects: int | ApiOmitted = api_field(
        description="The maximum number of objects to display in the alert overview.",
        default_factory=ApiOmitted,
    )

    @classmethod
    @override
    def internal_type(cls) -> str:
        return "alert_overview"

    @classmethod
    def from_internal(cls, config: AlertOverviewDashletConfig) -> Self:
        window = config["time_range"]
        return cls(
            type="alert_overview",
            time_range=(
                "dashboard"
                if window["type"] == "dashboard"
                else timerange_from_internal(window["window"])
            ),
            limit_objects=config.get("limit_objects", ApiOmitted()),
        )

    @override
    def to_internal(self) -> AlertOverviewDashletConfig:
        config = AlertOverviewDashletConfig(
            type=self.internal_type(),
            time_range=(
                DashboardWindow(type="dashboard")
                if self.time_range == "dashboard"
                else FixedWindow(type="range", window=self.time_range.to_internal())
            ),
        )
        if not isinstance(self.limit_objects, ApiOmitted):
            config["limit_objects"] = self.limit_objects
        return config


@api_model
class SiteOverviewContent(BaseWidgetContent):
    type: Literal["site_overview"] = api_field(
        description="Displays either sites and states or hosts and states of a site."
    )
    dataset: Literal["via_context", "sites", "hosts"] = api_field(
        description=(
            "Defines whether the widget shows sites and their states or hosts and their states. "
            "If 'via_context', the dataset is determined by the active filters and site setup."
        ),
    )
    hexagon_size: Literal["default", "large"] = api_field(
        description="Defines the size of the hexagons in the widget.",
    )
    contextual_link: ContextualLinkSpec = api_field(
        description="Where a click on a site or a host leads."
    )

    @classmethod
    @override
    def internal_type(cls) -> str:
        return "site_overview"

    @override
    def configured_contextual_link(self) -> ContextualLinkSpec:
        return self.contextual_link

    @classmethod
    def from_internal(cls, config: SiteOverviewDashletConfig) -> Self:
        return cls(
            type="site_overview",
            dataset=config.get("dataset") or "via_context",
            hexagon_size=config.get("box_scale") or "default",
            contextual_link=contextual_link_from_internal(config.get("contextual_link")),
        )

    @override
    def to_internal(self) -> SiteOverviewDashletConfig:
        config = SiteOverviewDashletConfig(
            type=self.internal_type(),
            box_scale=self.hexagon_size,
        )
        if self.dataset != "via_context":
            config["dataset"] = self.dataset
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
