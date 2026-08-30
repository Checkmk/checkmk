#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.fireeye.lib import DETECT, HEALTH_MAP, STATUS_MAP

# .1.3.6.1.4.1.25597.11.3.1.1.0 Good --> FE-FIREEYE-MIB::fePowerSupplyOverallStatus.0
# .1.3.6.1.4.1.25597.11.3.1.2.0 1 --> FE-FIREEYE-MIB::fePowerSupplyOverallIsHealthy.0


def check_fireeye_powersupplies(section: StringTable) -> CheckResult:
    status, health = section[0]
    state, state_readable = STATUS_MAP.get(status.lower(), (2, f"unknown: {status}"))
    yield Result(state=State(state), summary=f"Status: {state_readable}")
    state, state_readable = HEALTH_MAP.get(health, (2, f"unknown: {health}"))
    yield Result(state=State(state), summary=f"Health: {state_readable}")


def parse_fireeye_powersupplies(string_table: StringTable) -> StringTable:
    return string_table


def discover_fireeye_powersupplies(section: StringTable) -> DiscoveryResult:
    if section:
        yield Service()


snmp_section_fireeye_powersupplies = SimpleSNMPSection(
    name="fireeye_powersupplies",
    parse_function=parse_fireeye_powersupplies,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.25597.11.3.1",
        oids=["1", "2"],
    ),
)


check_plugin_fireeye_powersupplies = CheckPlugin(
    name="fireeye_powersupplies",
    service_name="Power supplies summary",
    discovery_function=discover_fireeye_powersupplies,
    check_function=check_fireeye_powersupplies,
)
