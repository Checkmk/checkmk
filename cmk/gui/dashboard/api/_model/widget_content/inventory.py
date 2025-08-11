#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Literal, override, Self

from cmk.gui.dashboard.type_defs import InventoryDashletConfig
from cmk.gui.openapi.framework.model import api_field, api_model

from ._base import BaseWidgetContent


@api_model
class InventoryContent(BaseWidgetContent):
    type: Literal["inventory"] = api_field(description="Displays inventory data of a Host.")
    path: str = api_field(
        description="The path to the inventory data to display.",
        example=".software.os.type",
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
        )

    @override
    def to_internal(self) -> InventoryDashletConfig:
        return InventoryDashletConfig(
            type=self.internal_type(),
            inventory_path=self.path,
        )
