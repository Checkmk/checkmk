#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Sequence
from enum import StrEnum

from pydantic import BaseModel

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)


class AlertSeverity(StrEnum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class Alert(BaseModel, frozen=True):
    description: str
    severity: AlertSeverity


class InternalAlerts(BaseModel, frozen=True):
    critical_alerts: Sequence[str]
    warning_alerts: Sequence[str]
    info_alerts: Sequence[str]


def parse_alerts(string_table: StringTable) -> InternalAlerts:
    json_data = json.loads(string_table[0][0])
    alerts = [Alert.model_validate(item) for item in json_data.get("items", [])]

    return InternalAlerts(
        critical_alerts=[a.description for a in alerts if a.severity == AlertSeverity.CRITICAL],
        warning_alerts=[a.description for a in alerts if a.severity == AlertSeverity.WARNING],
        info_alerts=[a.description for a in alerts if a.severity == AlertSeverity.INFO],
    )


agent_section_pure_storage_fa_alerts = AgentSection(
    name="pure_storage_fa_alerts",
    parse_function=parse_alerts,
)


def discover_internal_alerts(section: InternalAlerts) -> DiscoveryResult:
    yield Service()


def check_internal_alerts(section: InternalAlerts) -> CheckResult:
    yield Result(
        state=State.CRIT if section.critical_alerts else State.OK,
        summary=f"Critical: {len(section.critical_alerts)}",
    )
    if section.critical_alerts:
        yield Result(
            state=State.OK, notice=f"Critical alerts: {', '.join(section.critical_alerts)}"
        )

    yield Result(
        state=State.WARN if section.warning_alerts else State.OK,
        summary=f"Warning: {len(section.warning_alerts)}",
    )
    if section.warning_alerts:
        yield Result(state=State.OK, notice=f"Warning alerts: {', '.join(section.warning_alerts)}")

    yield Result(state=State.OK, summary=f"Info: {len(section.info_alerts)}")
    if section.info_alerts:
        yield Result(state=State.OK, notice=f"Info alerts: {', '.join(section.info_alerts)}")


check_plugin_pure_storage_fa_alerts = CheckPlugin(
    name="pure_storage_fa_alerts",
    service_name="Internal Alerts",
    discovery_function=discover_internal_alerts,
    check_function=check_internal_alerts,
)
