#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Literal, override, Self

from cmk.gui.dashboard.type_defs import InventoryDashletConfig
from cmk.gui.openapi.framework.model import api_field, api_model, ApiOmitted

from ._base import ApiVisualLink, BaseWidgetContent


@api_model
class InventoryContent(BaseWidgetContent):
    type: Literal["inventory"] = api_field(description="Displays inventory data of a Host.")
    path: str = api_field(
        description="The path to the inventory data to display.",
        example=".software.os.type",
    )
    link_spec: ApiVisualLink | ApiOmitted = api_field(
        description="Changes the link of the rendered inventory data.",
        default_factory=ApiOmitted,
    )

    @classmethod
    @override
    def internal_type(cls) -> str:
        return "inventory"

    @classmethod
    def from_internal(cls, config: InventoryDashletConfig) -> Self:
        return cls(
            type="inventory",
            path=config["inventory_path"],
            link_spec=ApiVisualLink.from_raw_internal(config.get("link_spec")),
        )

    @override
    def to_internal(self) -> InventoryDashletConfig:
        config = InventoryDashletConfig(
            type=self.internal_type(),
            inventory_path=self.path,
        )
        if not isinstance(self.link_spec, ApiOmitted):
            config["link_spec"] = self.link_spec.to_raw_internal()
        return config
