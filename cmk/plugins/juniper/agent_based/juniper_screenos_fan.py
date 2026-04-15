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
from cmk.plugins.juniper.lib import DETECT_JUNIPER_SCREENOS

Section = dict[str, str]


def parse_juniper_screenos_fan(string_table: StringTable) -> Section:
    # SNMP outputs "Fan 1". The item is just the numeric suffix, e.g. '1'.
    return {line[0].split()[-1]: line[1] for line in string_table}


def discovery_juniper_screenos_fan(section: Section) -> DiscoveryResult:
    for fan_id in section:
        yield Service(item=fan_id)


def check_juniper_screenos_fan(item: str, section: Section) -> CheckResult:
    if item not in section:
        return
    fan_status = section[item]
    if fan_status == "1":
        yield Result(state=State.OK, summary="status is good")
    elif fan_status == "2":
        yield Result(state=State.CRIT, summary="status is failed")
    else:
        yield Result(state=State.CRIT, summary=f"Unknown fan status {fan_status}")


snmp_section_juniper_screenos_fan = SimpleSNMPSection(
    name="juniper_screenos_fan",
    detect=DETECT_JUNIPER_SCREENOS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3224.21.2.1",
        oids=["3", "2"],
    ),
    parse_function=parse_juniper_screenos_fan,
)

check_plugin_juniper_screenos_fan = CheckPlugin(
    name="juniper_screenos_fan",
    service_name="FAN %s",
    discovery_function=discovery_juniper_screenos_fan,
    check_function=check_juniper_screenos_fan,
)
