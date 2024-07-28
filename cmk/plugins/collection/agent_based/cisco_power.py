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

# .1.3.6.1.4.1.9.9.13.1.5.1.2.1 "removed"
# .1.3.6.1.4.1.9.9.13.1.5.1.2.2 "AC Power Supply"
# .1.3.6.1.4.1.9.9.13.1.5.1.3.1 5
# .1.3.6.1.4.1.9.9.13.1.5.1.3.2 1
# .1.3.6.1.4.1.9.9.13.1.5.1.4.1 1
# .1.3.6.1.4.1.9.9.13.1.5.1.4.2 2

cisco_power_states = (
    "",
    "normal",
    "warning",
    "critical",
    "shutdown",
    "not present",
    "not functioning",
)

cisco_power_sources = (
    "",
    "unknown",
    "AC",
    "DC",
    "external power supply",
    "internal redundant",
)


def inventory_cisco_power(section: StringTable) -> DiscoveryResult:
    # Note: the name of the power supply is not unique. We have seen
    # a Cisco with four entries in the MIB. So we force uniqueness
    # by appending a "/4" for ID 4 if the name is not unique
    discovered: dict[str, list[str]] = {}
    for sid, textinfo, state, _source in section:
        if state != "5":
            name = cisco_sensor_item(textinfo, sid)
            discovered.setdefault(name, []).append(sid)

    for name, entries in discovered.items():
        if len(entries) == 1:
            yield Service(item=name)
        else:
            for entry in entries:
                yield Service(item=f"{name} {entry}")


def check_cisco_power(item: str, section: StringTable) -> CheckResult:
    for sid, textinfo, r_state, r_source in section:
        if (
            cisco_sensor_item(textinfo, sid) == item
            or cisco_sensor_item(textinfo, sid) + " " + sid == item
            or cisco_sensor_item(textinfo, sid) + "/" + sid == item
        ):
            state = int(r_state)
            source = int(r_source)
            yield Result(
                state={1: State.OK, 2: State.WARN}.get(state, State.CRIT),
                summary="Status: {}, Source: {}".format(
                    cisco_power_states[state],
                    cisco_power_sources[source],
                ),
            )


def parse_cisco_power(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_cisco_power = SimpleSNMPSection(
    name="cisco_power",
    detect=DETECT_CISCO,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9.9.13.1.5.1",
        oids=[OIDEnd(), "2", "3", "4"],
    ),
    parse_function=parse_cisco_power,
)
check_plugin_cisco_power = CheckPlugin(
    name="cisco_power",
    service_name="Power %s",
    discovery_function=inventory_cisco_power,
    check_function=check_cisco_power,
)
