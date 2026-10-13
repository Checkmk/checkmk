#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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


def parse_sap_state(string_table: StringTable) -> StringTable:
    return string_table


agent_section_sap_state = AgentSection(
    name="sap_state",
    parse_function=parse_sap_state,
)


def discover_sap_state(section: StringTable) -> DiscoveryResult:
    for line in section:
        if len(line) == 2:
            yield Service(item=line[0])


def check_sap_state(item: str, section: StringTable) -> CheckResult:
    for line in section:
        if line[0] == item:
            value = line[1]
            yield Result(
                state=State.OK if value == "OK" else State.CRIT,
                summary=f"Status: {value}",
            )
            return


check_plugin_sap_state = CheckPlugin(
    name="sap_state",
    service_name="SAP State %s",
    discovery_function=discover_sap_state,
    check_function=check_sap_state,
)
