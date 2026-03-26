#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    OIDEnd,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.stulz.lib import DETECT_STULZ


def parse_stulz_powerstate(string_table: StringTable) -> StringTable:
    return string_table


def discover_stulz_powerstate(section: StringTable) -> DiscoveryResult:
    yield from (Service(item=line[0]) for line in section)


def check_stulz_powerstate(item: str, section: StringTable) -> CheckResult:
    for line in section:
        if line[0] == item:
            if line[1] != "1":
                message = "Device powered off"
                power_state = 2
            else:
                message = "Device powered on"
                power_state = 6

            yield Result(state=State.OK, summary=message)
            yield Metric("state", power_state)
            return


snmp_section_stulz_powerstate = SimpleSNMPSection(
    name="stulz_powerstate",
    detect=DETECT_STULZ,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.29462.10.2.1.4.1.1.1.1013",
        oids=[OIDEnd(), "1"],
    ),
    parse_function=parse_stulz_powerstate,
)

check_plugin_stulz_powerstate = CheckPlugin(
    name="stulz_powerstate",
    service_name="State %s ",
    discovery_function=discover_stulz_powerstate,
    check_function=check_stulz_powerstate,
)
