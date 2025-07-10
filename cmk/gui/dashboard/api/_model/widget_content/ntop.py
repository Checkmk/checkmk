#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from abc import ABC
from typing import Literal, override, Self

from cmk.gui.dashboard.type_defs import (
    DashletConfig,
    NtopAlertsDashletConfig,
    NtopFlowsDashletConfig,
    NtopTopTalkersDashletConfig,
)
from cmk.gui.openapi.framework.model import api_field, api_model

from ._base import BaseWidgetContent

type _NtopConfig = NtopAlertsDashletConfig | NtopFlowsDashletConfig | NtopTopTalkersDashletConfig


@api_model
class _BaseNtopContent(BaseWidgetContent, ABC):
    @override
    def to_internal(self) -> _NtopConfig:
        return DashletConfig(type=self.internal_type())


@api_model
class NtopAlertsContent(_BaseNtopContent):
    type: Literal["ntop_alerts"] = api_field(
        description="Display Ntop engaged, past and flow alerts."
    )

    @classmethod
    @override
    def internal_type(cls) -> str:
        return "ntop_alerts"

    @classmethod
    def from_internal(cls, _config: NtopAlertsDashletConfig) -> Self:
        return cls(type="ntop_alerts")


@api_model
class NtopFlowsContent(_BaseNtopContent):
    type: Literal["ntop_flows"] = api_field(description="Display Ntop flow information.")

    @classmethod
    @override
    def internal_type(cls) -> str:
        return "ntop_flows"

    @classmethod
    def from_internal(cls, _config: NtopFlowsDashletConfig) -> Self:
        return cls(type="ntop_flows")


@api_model
class NtopTopTalkersContent(_BaseNtopContent):
    type: Literal["ntop_top_talkers"] = api_field(description="Displays Top Talkers.")

    @classmethod
    @override
    def internal_type(cls) -> str:
        return "ntop_top_talkers"

    @classmethod
    def from_internal(cls, _config: NtopTopTalkersDashletConfig) -> Self:
        return cls(type="ntop_top_talkers")
