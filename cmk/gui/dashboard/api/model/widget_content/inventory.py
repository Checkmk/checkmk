#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterable, Mapping
from typing import Literal, override, Self

from pydantic_core import ErrorDetails

from cmk.gui.dashboard.type_defs import InventoryDashletConfig
from cmk.gui.openapi.framework import ApiContext
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.type_defs import DashboardEmbeddedViewSpec

from ..context_filters import AggregateHostContextFilter, host_filter_from_internal
from ..contextual_link import (
    AnyContextualLinkSpec,
    contextual_link_from_internal,
    contextual_link_to_internal,
    ContextualLinkSpec,
    iter_contextual_link_errors,
)
from ._base import BaseWidgetContent


@api_model
class InventoryContent(BaseWidgetContent):
    type: Literal["inventory"] = api_field(description="Displays inventory data of a Host.")
    path: str = api_field(
        description="The path to the inventory data to display.",
        example=".software.os.type",
    )
    contextual_link: ContextualLinkSpec[AggregateHostContextFilter] = api_field(
        description="Where a click on the inventory data leads."
    )

    @classmethod
    @override
    def internal_type(cls) -> str:
        return "inventory"

    @override
    def configured_contextual_link(self) -> AnyContextualLinkSpec:
        return self.contextual_link

    @classmethod
    def from_internal(cls, config: InventoryDashletConfig) -> Self:
        return cls(
            type="inventory",
            path=config["inventory_path"],
            contextual_link=contextual_link_from_internal(
                config.get("contextual_link"), host_filter_from_internal
            ),
        )

    @override
    def to_internal(self) -> InventoryDashletConfig:
        config = InventoryDashletConfig(
            type=self.internal_type(),
            inventory_path=self.path,
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
        return iter_contextual_link_errors(
            self.contextual_link,
            location + ("contextual_link",),
            context.config.user_permissions(),
        )
