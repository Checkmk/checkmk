#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Author: Lars Michelsen <lm@mathias-kettner.de>
# Modified for Dell Sensors By: Chris Bowlby <cbowlby@tenthpowertech.com>

# Tested with Dell PowerConnect 5448 and 5424 models.
# Relevant SNMP OIDs:
# .1.3.6.1.4.1.674.10895.3000.1.2.110.7.1.1.1.67109249 = INTEGER: 67109249
# .1.3.6.1.4.1.674.10895.3000.1.2.110.7.1.1.1.67109250 = INTEGER: 67109250
# .1.3.6.1.4.1.674.10895.3000.1.2.110.7.1.1.1.67109251 = INTEGER: 67109251
# .1.3.6.1.4.1.674.10895.3000.1.2.110.7.1.1.2.67109249 = STRING: "fan1_unit1"
# .1.3.6.1.4.1.674.10895.3000.1.2.110.7.1.1.2.67109250 = STRING: "fan2_unit1"
# .1.3.6.1.4.1.674.10895.3000.1.2.110.7.1.1.2.67109251 = STRING: "fan3_unit1"
# .1.3.6.1.4.1.674.10895.3000.1.2.110.7.1.1.3.67109249 = INTEGER: 1
# .1.3.6.1.4.1.674.10895.3000.1.2.110.7.1.1.3.67109250 = INTEGER: 1
# .1.3.6.1.4.1.674.10895.3000.1.2.110.7.1.1.3.67109251 = INTEGER: 1

# Status codes:
# 1 => normal,
# 2 => warning,
# 3 => critical,
# 4 => shutdown,
# 5 => notPresent,
# 6 => notFunctioning

# GENERAL MAPS:


from cmk.agent_based.v2 import (
    any_of,
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)

dell_powerconnect_fans_status_map = {
    "1": "normal",
    "2": "warning",
    "3": "critical",
    "4": "shutdown",
    "5": "notPresent",
    "6": "notFunctioning",
}
dell_powerconnect_fans_status2nagios_map = {
    "normal": State.OK,
    "warning": State.WARN,
    "critical": State.CRIT,
    "shutdown": State.UNKNOWN,
    "notPresent": State.WARN,
    "notFunctioning": State.CRIT,
}


# Discovery of all fan related elements
def inventory_dell_powerconnect_fans(section: StringTable) -> DiscoveryResult:
    inventory = []
    for _device_id, name, state in section:
        if dell_powerconnect_fans_status_map[state] != "notPresent":
            inventory.append((name, None))
    yield from [Service(item=item, parameters=parameters) for (item, parameters) in inventory]


# The check for the states and details of each fan
def check_dell_powerconnect_fans(item: str, section: StringTable) -> CheckResult:
    for _device_id, name, state in section:
        if name == item:
            dell_powerconnect_status = dell_powerconnect_fans_status_map[state]
            status = dell_powerconnect_fans_status2nagios_map[dell_powerconnect_status]

            yield Result(
                state=status, summary=f'Condition of FAN "{name}" is {dell_powerconnect_status}'
            )
            return


# Auto-detection of fan related details.


def parse_dell_powerconnect_fans(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_dell_powerconnect_fans = SimpleSNMPSection(
    name="dell_powerconnect_fans",
    detect=any_of(
        contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.674.10895"),
        contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.6027.1.3.22"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.674.10895.3000.1.2.110.7.1.1",
        oids=["1", "2", "3"],
    ),
    parse_function=parse_dell_powerconnect_fans,
)
check_plugin_dell_powerconnect_fans = CheckPlugin(
    name="dell_powerconnect_fans",
    service_name="Sensor %s",
    discovery_function=inventory_dell_powerconnect_fans,
    check_function=check_dell_powerconnect_fans,
)
