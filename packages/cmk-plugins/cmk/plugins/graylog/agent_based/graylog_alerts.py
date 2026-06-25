#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from dataclasses import dataclass
from typing import TypedDict

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    LevelsT,
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


class AlertsParams(TypedDict):
    alerts_upper: LevelsT[int]
    alerts_lower: LevelsT[int]
    alerts_in_range_upper: LevelsT[int]
    alerts_in_range_lower: LevelsT[int]


def parse_graylog_alerts(string_table: StringTable) -> AlertsInfo | None:
    alerts_section = json.loads(string_table[0][0])
    if len(alerts_section) != 1:
        return None

    match alerts_section:
        case {
            "alerts": {
                "num_of_alerts": int(num_of_alerts),
                "has_since_argument": bool(has_since_argument),
                "alerts_since": (int() | None) as alerts_since,
                "num_of_alerts_in_range": int(num_of_alerts_in_range),
            }
        }:
            return AlertsInfo(
                num_of_alerts=num_of_alerts,
                has_since_argument=has_since_argument,
                alerts_since=alerts_since,
                num_of_alerts_in_range=num_of_alerts_in_range,
            )
        case _:
            return None


agent_section_graylog_alerts = AgentSection(
    name="graylog_alerts",
    parse_function=parse_graylog_alerts,
)


def discover_graylog_alerts(section: AlertsInfo) -> DiscoveryResult:
    yield Service(item=None)


def check_graylog_alerts(params: AlertsParams, section: AlertsInfo) -> CheckResult:
    yield from check_levels(
        value=section.num_of_alerts,
        levels_upper=params["alerts_upper"],
        levels_lower=params["alerts_lower"],
        render_func=lambda x: str(int(x)),
        label="Total number of alerts",
    )

    if section.has_since_argument and section.alerts_since:
        yield from check_levels(
            value=section.num_of_alerts_in_range,
            levels_upper=params["alerts_in_range_upper"],
            levels_lower=params["alerts_in_range_lower"],
            render_func=lambda x: str(int(x)),
            label=f"Total number of alerts in the last {render.timespan(section.alerts_since)}",
        )


check_plugin_graylog_alerts = CheckPlugin(
    name="graylog_alerts",
    check_function=check_graylog_alerts,
    discovery_function=discover_graylog_alerts,
    service_name="Graylog Cluster Alerts",
    check_default_parameters={
        "alerts_upper": ("no_levels", None),
        "alerts_lower": ("no_levels", None),
        "alerts_in_range_upper": ("no_levels", None),
        "alerts_in_range_lower": ("no_levels", None),
    },
    check_ruleset_name="graylog_alerts",
)
