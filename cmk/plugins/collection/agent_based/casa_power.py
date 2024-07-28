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
from cmk.plugins.lib.casa import DETECT_CASA


def inventory_casa_power(section: StringTable) -> DiscoveryResult:
    yield from (Service(item=str(idx)) for idx in range(len(section)))


def check_casa_power(item: str, section: StringTable) -> CheckResult:
    unit_nr = int(item)
    if len(section) < unit_nr:
        yield Result(state=State.UNKNOWN, summary="Power Supply %s not found in snmp output" % item)
        return

    try:
        yield {
            "0": Result(state=State.UNKNOWN, summary="Power supply - Unknown status"),
            "1": Result(state=State.OK, summary="Power supply OK"),
            "2": Result(
                state=State.OK, summary="Power supply working under threshold"
            ),  # OK, backup power..
            "3": Result(state=State.WARN, summary="Power supply working over threshold"),
            "4": Result(state=State.CRIT, summary="Power failure"),
        }[section[unit_nr][0]]
    except KeyError:
        pass


def parse_casa_power(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_casa_power = SimpleSNMPSection(
    name="casa_power",
    detect=DETECT_CASA,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.20858.10.33.1.5.1",
        oids=["4"],
    ),
    parse_function=parse_casa_power,
)
check_plugin_casa_power = CheckPlugin(
    name="casa_power",
    service_name="Power %s",
    discovery_function=inventory_casa_power,
    check_function=check_casa_power,
)
