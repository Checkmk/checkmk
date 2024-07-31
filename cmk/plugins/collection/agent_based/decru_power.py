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
from cmk.plugins.lib.decru import DETECT_DECRU


def inventory_decru_power(section: StringTable) -> DiscoveryResult:
    yield from [Service(item=l[0]) for l in section]


def check_decru_power(item: str, section: StringTable) -> CheckResult:
    for power in section:
        if power[0] == item:
            if power[1] != "1":
                yield Result(state=State.CRIT, summary="power supply in state %s" % power[1])
                return
            yield Result(state=State.OK, summary="power supply ok")
            return

    yield Result(state=State.UNKNOWN, summary="power supply not found")
    return


def parse_decru_power(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_decru_power = SimpleSNMPSection(
    name="decru_power",
    detect=DETECT_DECRU,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12962.1.2.6.1",
        oids=["2", "3"],
    ),
    parse_function=parse_decru_power,
)
check_plugin_decru_power = CheckPlugin(
    name="decru_power",
    service_name="POWER %s",
    discovery_function=inventory_decru_power,
    check_function=check_decru_power,
)
