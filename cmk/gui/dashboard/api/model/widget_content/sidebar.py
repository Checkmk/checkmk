#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Annotated, Literal, override, Self

from pydantic import AfterValidator

from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.framework.model.converter import RegistryConverter
from cmk.gui.sidebar import all_snapins, SnapinDashletConfig

from ._base import BaseWidgetContent


@api_model
class SidebarElementContent(BaseWidgetContent):
    type: Literal["sidebar_element"] = api_field(
        description="Allows you to use a sidebar element in the dashboard."
    )
    name: Annotated[str, AfterValidator(RegistryConverter(all_snapins).validate)] = api_field(
        description="Identifier of the sidebar element."
    )

    @classmethod
    @override
    def internal_type(cls) -> str:
        return "snapin"

    @classmethod
    def from_internal(cls, config: SnapinDashletConfig) -> Self:
        return cls(type="sidebar_element", name=config["snapin"])

    @override
    def to_internal(self) -> SnapinDashletConfig:
        return SnapinDashletConfig(type=self.internal_type(), snapin=self.name)
