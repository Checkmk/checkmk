#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import (
    all_of,
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    not_exists,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)


def inventory_cisco_temp(section: StringTable) -> DiscoveryResult:
    for name, state in section:
        if state != "5":
            yield Service(item=name)


def check_cisco_temp(item: str, section: StringTable) -> CheckResult:
    map_states = {
        "1": (State.OK, "OK"),
        "2": (State.WARN, "warning"),
        "3": (State.CRIT, "critical"),
        "4": (State.CRIT, "shutdown"),
        "5": (State.UNKNOWN, "not present"),
        "6": (State.UNKNOWN, "value out of range"),
    }

    for name, dev_state in section:
        if name == item:
            state, state_readable = map_states.get(
                dev_state, (State.UNKNOWN, "unknown[%s]" % dev_state)
            )
            yield Result(state=state, summary="Status: %s" % state_readable)
            return


def parse_cisco_temp(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_cisco_temp = SimpleSNMPSection(
    name="cisco_temp",
    detect=all_of(
        contains(".1.3.6.1.2.1.1.1.0", "cisco"), not_exists(".1.3.6.1.4.1.9.9.13.1.3.1.3.*")
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9.9.13.1.3.1",
        oids=["2", "6"],
    ),
    parse_function=parse_cisco_temp,
)


check_plugin_cisco_temp = CheckPlugin(
    name="cisco_temp",
    service_name="Temperature %s",
    discovery_function=inventory_cisco_temp,
    check_function=check_cisco_temp,
)
