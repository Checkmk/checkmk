#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Literal, override, Self

from cmk.gui.dashboard.dashlet.dashlets.custom_url import URLDashletConfig
from cmk.gui.openapi.framework.model import api_field, api_model

from ._base import BaseWidgetContent


@api_model
class URLContent(BaseWidgetContent):
    type: Literal["url"] = api_field(description="Displays the content of a custom website.")
    # NOTE: can't use pydantic's URL types, since this might not even contain a scheme
    url: str = api_field(description="URL of the website.")

    @classmethod
    @override
    def internal_type(cls) -> str:
        return "url"

    @classmethod
    def from_internal(cls, config: URLDashletConfig) -> Self:
        return cls(type="url", url=config["url"])

    @override
    def to_internal(self) -> URLDashletConfig:
        return URLDashletConfig(type=self.internal_type(), url=self.url)
