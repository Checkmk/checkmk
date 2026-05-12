#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<heartbeat_rscstatus>>>
# all
#
# Status can be "local", "foreign", "all" or "none"

from collections.abc import Mapping
from typing import Any

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


def parse_heartbeat_rscstatus(string_table: StringTable) -> str | None:
    try:
        return string_table[0][0]
    except IndexError:
        return None


def discover_heartbeat_rscstatus(section: str | None) -> DiscoveryResult:
    if section is not None:
        yield Service(parameters={"discovered_state": section})


def check_heartbeat_rscstatus(params: Mapping[str, Any], section: str | None) -> CheckResult:
    if section is None:
        return

    if not isinstance(params, dict):
        # old params comes styled with double quotes
        params = {"discovered_state": str(params).replace('"', "")}

    expected_state = params.get("discovered_state")
    if "expected_state" in params:
        expected_state = params["expected_state"]

    if expected_state == section:
        yield Result(state=State.OK, summary=f"Current state: {section}")
    else:
        yield Result(
            state=State.CRIT,
            summary=f"Current state: {section} (Expected: {expected_state})",
        )


agent_section_heartbeat_rscstatus = AgentSection(
    name="heartbeat_rscstatus",
    parse_function=parse_heartbeat_rscstatus,
)

check_plugin_heartbeat_rscstatus = CheckPlugin(
    name="heartbeat_rscstatus",
    service_name="Heartbeat Ressource Status",
    discovery_function=discover_heartbeat_rscstatus,
    check_function=check_heartbeat_rscstatus,
    check_ruleset_name="heartbeat_rscstatus",
    check_default_parameters={},
)
