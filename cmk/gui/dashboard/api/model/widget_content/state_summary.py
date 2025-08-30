#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Literal, override, Self

from cmk.gui.dashboard.type_defs import (
    HostStateSummaryDashletConfig,
    ServiceStateSummaryDashletConfig,
)
from cmk.gui.fields.attributes import MappingConverter
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.valuespec.definitions import HostStateValue, MonitoringStateValue

from ._base import BaseWidgetContent

type HostState = Literal["UP", "DOWN", "UNREACHABLE"]
_HOST_STATE_CONVERTER = MappingConverter[HostState, HostStateValue](
    {
        "UP": 0,
        "DOWN": 1,
        "UNREACHABLE": 2,
    }
)
type MonitoringState = Literal["OK", "WARNING", "CRITICAL", "UNKNOWN"]
_MONITORING_STATE_CONVERTER = MappingConverter[MonitoringState, MonitoringStateValue](
    {
        "OK": 0,
        "WARNING": 1,
        "CRITICAL": 2,
        "UNKNOWN": 3,
    }
)


@api_model
class HostStateSummaryContent(BaseWidgetContent):
    type: Literal["host_state_summary"] = api_field(
        description="Displays amount of hosts in a selected state.",
    )
    state: HostState = api_field(description="The state of the hosts to be displayed.")

    @classmethod
    @override
    def internal_type(cls) -> str:
        return "host_state_summary"

    @classmethod
    def from_internal(cls, config: HostStateSummaryDashletConfig) -> Self:
        return cls(
            type="host_state_summary",
            state=_HOST_STATE_CONVERTER.from_checkmk(config["state"]),
        )

    @override
    def to_internal(self) -> HostStateSummaryDashletConfig:
        return HostStateSummaryDashletConfig(
            type=self.internal_type(),
            state=_HOST_STATE_CONVERTER.to_checkmk(self.state),
        )


@api_model
class ServiceStateSummaryContent(BaseWidgetContent):
    type: Literal["service_state_summary"] = api_field(
        description="Displays amount of services in a selected state.",
    )
    state: MonitoringState = api_field(
        description="The state of the services to be displayed.",
    )

    @classmethod
    @override
    def internal_type(cls) -> str:
        return "service_state_summary"

    @classmethod
    def from_internal(cls, config: ServiceStateSummaryDashletConfig) -> Self:
        return cls(
            type="service_state_summary",
            state=_MONITORING_STATE_CONVERTER.from_checkmk(config["state"]),
        )

    @override
    def to_internal(self) -> ServiceStateSummaryDashletConfig:
        return ServiceStateSummaryDashletConfig(
            type=self.internal_type(),
            state=_MONITORING_STATE_CONVERTER.to_checkmk(self.state),
        )
