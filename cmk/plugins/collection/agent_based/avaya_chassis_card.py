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
from cmk.plugins.lib.avaya import DETECT_AVAYA

avaya_chassis_card_operstatus_codes = {
    1: (State.OK, "up"),
    2: (State.CRIT, "down"),
    3: (State.OK, "testing"),
    4: (State.UNKNOWN, "unknown"),
    5: (State.OK, "dormant"),
}


def inventory_avaya_chassis_card(section: StringTable) -> DiscoveryResult:
    for line in section:
        yield Service(item=line[0])


def check_avaya_chassis_card(item: str, section: StringTable) -> CheckResult:
    for line in section:
        if line[0] == item:
            status, name = avaya_chassis_card_operstatus_codes[int(line[1])]
            yield Result(state=status, summary="Operational status: %s" % name)
            return


def parse_avaya_chassis_card(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_avaya_chassis_card = SimpleSNMPSection(
    name="avaya_chassis_card",
    detect=DETECT_AVAYA,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2272.1.4.9.1.1",
        oids=["1", "6"],
    ),
    parse_function=parse_avaya_chassis_card,
)
check_plugin_avaya_chassis_card = CheckPlugin(
    name="avaya_chassis_card",
    service_name="Card %s",
    discovery_function=inventory_avaya_chassis_card,
    check_function=check_avaya_chassis_card,
)
