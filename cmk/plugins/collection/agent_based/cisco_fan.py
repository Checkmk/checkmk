#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    OIDEnd,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.cisco import DETECT_CISCO
from cmk.plugins.lib.cisco_sensor_item import cisco_sensor_item

cisco_fan_state_mapping = {
    "1": (State.OK, "normal"),
    "2": (State.WARN, "warning"),
    "3": (State.CRIT, "critical"),
    "4": (State.CRIT, "shutdown"),
    "5": (State.UNKNOWN, "not present"),
    "6": (State.CRIT, "not functioning"),
}


def inventory_cisco_fan(section: StringTable) -> DiscoveryResult:
    yield from [
        Service(item=cisco_sensor_item(line[0], line[-1]))
        for line in section
        if line[1] in ["1", "2", "3", "4", "6"]
    ]


def check_cisco_fan(item: str, section: StringTable) -> CheckResult:
    for statustext, dev_state, oid_end in section:
        if cisco_sensor_item(statustext, oid_end) == item:
            state, state_readable = cisco_fan_state_mapping.get(
                dev_state, (State.UNKNOWN, "unknown[%s]" % dev_state)
            )
            yield Result(state=state, summary="Status: %s" % state_readable)


def parse_cisco_fan(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_cisco_fan = SimpleSNMPSection(
    name="cisco_fan",
    detect=DETECT_CISCO,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9.9.13.1.4.1",
        oids=["2", "3", OIDEnd()],
    ),
    parse_function=parse_cisco_fan,
)


check_plugin_cisco_fan = CheckPlugin(
    name="cisco_fan",
    service_name="FAN %s",
    discovery_function=inventory_cisco_fan,
    check_function=check_cisco_fan,
)
