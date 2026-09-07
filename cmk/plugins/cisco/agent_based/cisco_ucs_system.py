#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# comNET GmbH, Fabian Binder - 2018-05-07

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
from cmk.plugins.cisco.lib_ucs import DETECT, MAP_OPERABILITY


def parse_cisco_ucs_system(string_table: StringTable) -> StringTable | None:
    return string_table or None


def discover_cisco_ucs_system(section: StringTable) -> DiscoveryResult:  # noqa: ARG001
    yield Service()


def check_cisco_ucs_system(section: StringTable) -> CheckResult:
    model, serial, status = section[0]
    state, state_readable = MAP_OPERABILITY.get(status, (3, "Unknown, status code %s" % status))
    yield Result(
        state=State(state), summary=f"Status: {state_readable}, Model: {model}, SN: {serial}"
    )


snmp_section_cisco_ucs_system = SimpleSNMPSection(
    name="cisco_ucs_system",
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9.9.719.1.9.35.1",
        oids=["32", "47", "43"],
    ),
    parse_function=parse_cisco_ucs_system,
)

check_plugin_cisco_ucs_system = CheckPlugin(
    name="cisco_ucs_system",
    service_name="System health",
    discovery_function=discover_cisco_ucs_system,
    check_function=check_cisco_ucs_system,
)
