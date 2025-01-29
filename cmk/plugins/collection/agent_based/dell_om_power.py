#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.dell import DETECT_OPENMANAGE

# example output
# .1.3.6.1.4.1.674.10892.1.600.10.1.2.1.1 1
# .1.3.6.1.4.1.674.10892.1.600.10.1.5.1.1 3
# .1.3.6.1.4.1.674.10892.1.600.10.1.6.1.1 0
# .1.3.6.1.4.1.674.10892.1.600.12.1.2.1.1 1
# .1.3.6.1.4.1.674.10892.1.600.12.1.2.1.2 2
# .1.3.6.1.4.1.674.10892.1.600.12.1.5.1.1 3
# .1.3.6.1.4.1.674.10892.1.600.12.1.5.1.2 3
# .1.3.6.1.4.1.674.10892.1.600.12.1.7.1.1 9
# .1.3.6.1.4.1.674.10892.1.600.12.1.7.1.2 9
# .1.3.6.1.4.1.674.10892.1.600.12.1.8.1.1 PS1 Status
# .1.3.6.1.4.1.674.10892.1.600.12.1.8.1.2 PS2 Status


def inventory_dell_om_power(section: Sequence[StringTable]) -> DiscoveryResult:
    for index, _status, _count in section[0]:
        yield Service(item=index)


def check_dell_om_power(item: str, section: Sequence[StringTable]) -> CheckResult:
    translate_status = {
        "1": (State.UNKNOWN, "other"),
        "2": (State.UNKNOWN, "unknown"),
        "3": (State.OK, "full"),
        "4": (State.WARN, "degraded"),
        "5": (State.CRIT, "lost"),
        "6": (State.OK, "not redundant"),
        "7": (State.WARN, "redundancy offline"),
    }

    for index, status, _count in section[0]:
        if index == item:
            state, state_readable = translate_status[status]
            yield Result(state=state, summary="Redundancy status: %s" % state_readable)


def parse_dell_om_power(string_table: Sequence[StringTable]) -> Sequence[StringTable]:
    return string_table


snmp_section_dell_om_power = SNMPSection(
    name="dell_om_power",
    detect=DETECT_OPENMANAGE,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.674.10892.1.600.10.1",
            oids=["2", "5", "6"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.674.10892.1.600.12.1",
            oids=["2", "5", "7", "8"],
        ),
    ],
    parse_function=parse_dell_om_power,
)
check_plugin_dell_om_power = CheckPlugin(
    name="dell_om_power",
    service_name="Power Supply Redundancy %s",
    discovery_function=inventory_dell_om_power,
    check_function=check_dell_om_power,
)


def inventory_dell_om_power_unit(section: Sequence[StringTable]) -> DiscoveryResult:
    for line in section[1]:
        yield Service(item=line[0])


def check_dell_om_power_unit(item: str, section: Sequence[StringTable]) -> CheckResult:
    translate_status = {
        "1": (State.UNKNOWN, "OTHER"),
        "2": (State.UNKNOWN, "UNKNOWN"),
        "3": (State.OK, "OK"),
        "4": (State.WARN, "NONCRITICAL"),
        "5": (State.CRIT, "CRITICAL"),
        "6": (State.CRIT, "NONRECOVERABLE"),
    }

    translate_type = {
        "1": "OTHER",
        "2": "UNKNOWN",
        "3": "LINEAR",
        "4": "SWITCHING",
        "5": "BATTERY",
        "6": "UPS",
        "7": "CONVERTER",
        "8": "REGULATOR",
        "9": "AC",
        "10": "DC",
        "11": "VRM",
    }

    for index, status, psu_type, location in section[1]:
        if index == item:
            state, state_readable = translate_status[status]
            psu_type_readable = translate_type[psu_type]
            yield Result(
                state=state,
                summary=f"Status: {state_readable}, Type: {psu_type_readable}, Name: {location}",
            )


check_plugin_dell_om_power_unit = CheckPlugin(
    name="dell_om_power_unit",
    service_name="Power Supply %s",
    sections=["dell_om_power"],
    discovery_function=inventory_dell_om_power_unit,
    check_function=check_dell_om_power_unit,
)
