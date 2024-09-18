#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Service,
    StringTable,
)

# <<<graylog_alerts>>>
# {"alerts": {"num_of_alerts": 0, "has_since_argument": false, "alerts_since": null, "num_of_alerts_in_range": 0}}

# <<<graylog_alerts>>>
# {"alerts": {"num_of_alerts": 5, "has_since_argument": true, "alerts_since": 1800, "num_of_alerts_in_range": 2}}


@dataclass
class AlertsInfo:
    num_of_alerts: int
    has_since_argument: bool
    alerts_since: int | None
    num_of_alerts_in_range: int


def parse_graylog_alerts(string_table: StringTable) -> AlertsInfo | None:
    alerts_section = json.loads(string_table[0][0])
    if len(alerts_section) != 1:
        return None

    alerts_data = alerts_section.get("alerts")

    return AlertsInfo(
        num_of_alerts=alerts_data.get("num_of_alerts"),
        has_since_argument=alerts_data.get("has_since_argument"),
        alerts_since=alerts_data.get("alerts_since"),
        num_of_alerts_in_range=alerts_data.get("num_of_alerts_in_range"),
    )


agent_section_graylog_alerts = AgentSection(
    name="graylog_alerts",
    parse_function=parse_graylog_alerts,
)


def discover_graylog_alerts(section: AlertsInfo) -> DiscoveryResult:
    yield Service(item=None)


def check_graylog_alerts(params: Mapping[str, Any], section: AlertsInfo) -> CheckResult:
    yield from check_levels_v1(
        value=section.num_of_alerts,
        levels_upper=params.get("alerts_upper", (None, None)),
        levels_lower=params.get("alerts_lower", (None, None)),
        render_func=lambda x: str(int(x)),
        label="Total number of alerts",
    )

    if section.has_since_argument and section.alerts_since:
        yield from check_levels_v1(
            value=section.num_of_alerts_in_range,
            levels_upper=params.get("alerts_in_range_upper", (None, None)),
            levels_lower=params.get("alerts_in_range_lower", (None, None)),
            render_func=lambda x: str(int(x)),
            label=f"Total number of alerts in the last {render.timespan(section.alerts_since)}",
        )


check_plugin_graylog_alerts = CheckPlugin(
    name="graylog_alerts",
    check_function=check_graylog_alerts,
    discovery_function=discover_graylog_alerts,
    service_name="Graylog Cluster Alerts",
    check_default_parameters={},
    check_ruleset_name="graylog_alerts",
)
