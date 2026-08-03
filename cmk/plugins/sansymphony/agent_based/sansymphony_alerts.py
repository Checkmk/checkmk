#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    StringTable,
)


def parse_sansymphony_alerts(string_table: StringTable) -> StringTable:
    return string_table


agent_section_sansymphony_alerts = AgentSection(
    name="sansymphony_alerts",
    parse_function=parse_sansymphony_alerts,
)


def discover_sansymphony_alerts(section: StringTable) -> DiscoveryResult:
    yield Service()


def check_sansymphony_alerts(params: Mapping[str, Any], section: StringTable) -> CheckResult:
    nr_of_alerts = int(section[0][0])
    warn, crit = params["levels"]
    yield from check_levels(
        nr_of_alerts,
        levels_upper=("fixed", (warn, crit)),
        metric_name="alerts",
        render_func=str,
        label="Unacknowlegded alerts",
    )


check_plugin_sansymphony_alerts = CheckPlugin(
    name="sansymphony_alerts",
    service_name="sansymphony Alerts",
    discovery_function=discover_sansymphony_alerts,
    check_function=check_sansymphony_alerts,
    check_ruleset_name="sansymphony_alerts",
    check_default_parameters={
        "levels": (1, 2),
    },
)
