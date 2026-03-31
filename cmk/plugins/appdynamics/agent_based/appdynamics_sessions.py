#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<appdynamics_sessions:sep(124)>>>
# Hans|/hans|rejectedSessions:0|sessionAverageAliveTime:1800|sessionCounter:13377|expiredSessions:13371|processingTime:1044|maxActive:7|activeSessions:6|sessionMaxAliveTime:4153


import time
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_rate,
    get_value_store,
    Result,
    Service,
    State,
    StringTable,
)


def discover_appdynamics_sessions(section: StringTable) -> DiscoveryResult:
    for line in section:
        yield Service(item=" ".join(line[0:2]))


def check_appdynamics_sessions(
    item: str, params: Mapping[str, Any], section: StringTable
) -> CheckResult:
    for line in section:
        if item == " ".join(line[0:2]):
            values = {}
            for metric in line[2:]:
                name, value = metric.split(":")
                values[name] = int(value)

            active = values["activeSessions"]
            rejected = values["rejectedSessions"]
            max_active = values["maxActive"]
            counter = values["sessionCounter"]

            now = time.time()
            rate_id = f"appdynamics_sessions.{item.lower().replace(' ', '_')}.counter"
            counter_rate = get_rate(get_value_store(), rate_id, now, counter, raise_overflow=True)

            yield from check_levels(
                active,
                metric_name="running_sessions",
                levels_upper=params.get("levels_upper"),
                levels_lower=params.get("levels_lower"),
                render_func=str,
                label="Running sessions",
            )

            yield from check_levels(
                counter_rate,
                render_func=lambda x: f"{x}/sec",
            )

            yield from check_levels(
                rejected,
                metric_name="rejected_sessions",
                render_func=str,
                label="Rejected",
            )

            yield Result(state=State.OK, summary=f"Maximum active: {max_active}")


def parse_appdynamics_sessions(string_table: StringTable) -> StringTable:
    return string_table


agent_section_appdynamics_sessions = AgentSection(
    name="appdynamics_sessions",
    parse_function=parse_appdynamics_sessions,
)


check_plugin_appdynamics_sessions = CheckPlugin(
    name="appdynamics_sessions",
    service_name="AppDynamics Sessions %s",
    discovery_function=discover_appdynamics_sessions,
    check_function=check_appdynamics_sessions,
    check_ruleset_name="jvm_sessions",
    check_default_parameters={
        "levels_lower": ("no_levels", None),
        "levels_upper": ("no_levels", None),
    },
)
