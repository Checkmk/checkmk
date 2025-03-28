#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""
Kuhn & Rueß GmbH
Consulting and Development
https://kuhn-ruess.de

"""

from collections.abc import Mapping
from json import loads
from typing import Any, NamedTuple

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    StringTable,
)

# <<<graylog_alerts>>>
# {"alerts": {"num_of_events": 547, "num_of_alerts": 4}}

# <<<graylog_alerts>>>
# {"alerts": {"num_of_events": 5, "num_of_alerts": 0}}


class AlertsInfo(NamedTuple):
    num_of_events: int
    num_of_alerts: int


def parse_graylog_alerts(string_table: StringTable) -> AlertsInfo | None:
    """
    Parse JSON data to AlertsInfo
    """
    alerts_section = loads(string_table[0][0])

    if len(alerts_section) != 1:
        return None

    alerts_data = alerts_section.get("alerts")

    return AlertsInfo(
        num_of_events=alerts_data.get("num_of_events"),
        num_of_alerts=alerts_data.get("num_of_alerts"),
    )


agent_section_graylog_alerts = AgentSection(
    name="graylog_alerts",
    parse_function=parse_graylog_alerts,
)


def discover_graylog_alerts(section: AlertsInfo) -> DiscoveryResult:
    """
    Discover one service
    """
    if section:
        yield Service(item=None)


def check_graylog_alerts(params: Mapping[str, Any], section: AlertsInfo) -> CheckResult:
    for which in ["alerts", "events"]:
        yield from check_levels(
            value=(section._asdict())[f"num_of_{which}"],
            levels_upper=params.get(f"{which}_upper", None),
            levels_lower=params.get(f"{which}_lower", None),
            metric_name=f"graylog_{which}",
            render_func=lambda x: str(int(x)),
            label=f"Total number of {which}",
        )


check_plugin_graylog_alerts = CheckPlugin(
    name="graylog_alerts",
    sections=["graylog_alerts"],
    service_name="Graylog Cluster Alerts",
    discovery_function=discover_graylog_alerts,
    check_function=check_graylog_alerts,
    check_default_parameters={},
    check_ruleset_name="graylog_alerts",
)
