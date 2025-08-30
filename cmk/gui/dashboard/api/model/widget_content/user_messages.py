#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Literal, override, Self

from cmk.gui.dashboard.dashlet.dashlets.user_messages import MessageUsersDashletConfig
from cmk.gui.openapi.framework.model import api_field, api_model

from ._base import BaseWidgetContent


@api_model
class UserMessagesContent(BaseWidgetContent):
    type: Literal["user_messages"] = api_field(description="Display GUI messages sent to users.")

    @classmethod
    @override
    def internal_type(cls) -> str:
        return "user_messages"

    @classmethod
    def from_internal(cls, _config: MessageUsersDashletConfig) -> Self:
        return cls(type="user_messages")

    @override
    def to_internal(self) -> MessageUsersDashletConfig:
        return MessageUsersDashletConfig(type=self.internal_type())
