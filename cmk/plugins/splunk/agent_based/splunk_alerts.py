#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<splunk_alerts>>>
# 5

from typing import NewType, NotRequired, TypeAlias, TypedDict

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    FixedLevelsT,
    Service,
    StringTable,
)

AlertCount = NewType("AlertCount", int)


def parse_splunk_alerts(string_table: StringTable) -> AlertCount | None:
    """Parse splunk alerts from agent output."""
    try:
        count = int(string_table[0][0])
    except (IndexError, ValueError):
        return None

    return AlertCount(count)


def discover_splunk_alerts(section: AlertCount | None) -> DiscoveryResult:
    """Runs empty discovery since there is only a single service."""
    yield Service()


IntLevels: TypeAlias = FixedLevelsT[int]
"""Fixed warn and critical integer threshold."""


class CheckParams(TypedDict):
    """Parameters passed to plugin via ruleset (see defaults)."""

    alerts: NotRequired[IntLevels]


def check_splunk_alerts(params: CheckParams, section: AlertCount | None) -> CheckResult:
    """Checks the splunk alerts section returning valid checkmk results."""
    if section is None:
        return

    yield from check_levels(
        section,
        metric_name="fired_alerts",
        levels_upper=params.get("alerts"),
        render_func=lambda value: f"{value:.0f}",
        label="Number of fired alerts",
    )


agent_section_splunk_alerts = AgentSection(
    name="splunk_alerts",
    parse_function=parse_splunk_alerts,
)

check_plugin_splunk_alerts = CheckPlugin(
    name="splunk_alerts",
    service_name="Splunk Alerts",
    discovery_function=discover_splunk_alerts,
    check_function=check_splunk_alerts,
    check_ruleset_name="splunk_alerts",
    check_default_parameters=CheckParams(),
)
