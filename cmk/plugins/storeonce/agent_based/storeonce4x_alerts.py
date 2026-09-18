#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Sequence
from dataclasses import dataclass

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


@dataclass(frozen=True)
class Alert:
    cleared: bool
    status: State
    alert_state: str
    description: str


Section = Sequence[Alert]


_STATUS_MAP = {
    "CRITICAL": State.CRIT,
    "WARNING": State.WARN,
    "OK": State.OK,
    "UNKNOWN": State.UNKNOWN,
    "DISABLED": State.UNKNOWN,
}


def parse_storeonce4x_alerts(string_table: StringTable) -> Section:
    return [
        Alert(
            cleared=alert["state"].upper() == "CLEARED",
            status=_STATUS_MAP[alert["status"].upper()],
            alert_state=alert["alertState"],
            description=alert["description"],
        )
        for alert in json.loads(string_table[0][0])["members"]
    ]


agent_section_storeonce4x_alerts = AgentSection(
    name="storeonce4x_alerts",
    parse_function=parse_storeonce4x_alerts,
)


def discover_storeonce4x_alerts(section: Section) -> DiscoveryResult:  # noqa: ARG001
    yield Service()


def check_storeonce4x_alerts(section: Section) -> CheckResult:
    if not section:
        yield Result(state=State.OK, summary="No alerts at all found")
        return

    if all(alert.cleared for alert in section):
        yield Result(state=State.OK, summary="No uncleared alerts found")
        return

    yield from (
        Result(
            state=alert.status,
            summary=f"Alert State: {alert.alert_state}, Description: {alert.description}",
        )
        for alert in section
        if not alert.cleared
    )


check_plugin_storeonce4x_alerts = CheckPlugin(
    name="storeonce4x_alerts",
    service_name="Alerts",
    discovery_function=discover_storeonce4x_alerts,
    check_function=check_storeonce4x_alerts,
)
