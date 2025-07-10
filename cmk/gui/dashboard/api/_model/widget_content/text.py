#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Literal, override, Self

from cmk.gui.dashboard import StaticTextDashletConfig
from cmk.gui.openapi.framework.model import api_field, api_model

from ._base import BaseWidgetContent


@api_model
class StaticTextContent(BaseWidgetContent):
    type: Literal["static_text"] = api_field(description="Displays static text.")
    text: str = api_field(description="The static text to be displayed.")

    @classmethod
    @override
    def internal_type(cls) -> str:
        return "nodata"

    @classmethod
    def from_internal(cls, config: StaticTextDashletConfig) -> Self:
        return cls(
            type="static_text",
            text=config["text"],
        )

    @override
    def to_internal(self) -> StaticTextDashletConfig:
        return StaticTextDashletConfig(
            type=self.internal_type(),
            text=self.text,
        )
