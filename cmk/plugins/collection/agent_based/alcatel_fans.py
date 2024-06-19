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
from cmk.plugins.lib.alcatel import DETECT_ALCATEL, DETECT_ALCATEL_AOS7


def parse_alcatel_fans(string_table: StringTable) -> StringTable:
    return string_table


def discover_alcatel_fans(section: StringTable) -> DiscoveryResult:
    for nr, _value in enumerate(section, 1):
        yield Service(item=str(nr))


def check_alcatel_fans(item: str, section: StringTable) -> CheckResult:
    fan_states = {
        0: "has no status",
        1: "not running",
        2: "running",
    }
    try:
        line = section[int(item) - 1]
        fan_state = int(line[0])
    except (ValueError, IndexError):
        return

    yield Result(
        state=State.OK if fan_state == 2 else State.CRIT,
        summary="Fan " + fan_states.get(fan_state, "unknown (%s)" % fan_state),
    )


snmp_section_alcatel_fans_aos7 = SimpleSNMPSection(
    name="alcatel_fans_aos7",
    detect=DETECT_ALCATEL_AOS7,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.6486.801.1.1.1.3.1.1.11.1",
        oids=["2"],
    ),
    parse_function=parse_alcatel_fans,
)


check_plugin_alcatel_fans_aos7 = CheckPlugin(
    name="alcatel_fans_aos7",
    service_name="Fan %s",
    discovery_function=discover_alcatel_fans,
    check_function=check_alcatel_fans,
)


snmp_section_alcatel_fans = SimpleSNMPSection(
    name="alcatel_fans",
    detect=DETECT_ALCATEL,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.6486.800.1.1.1.3.1.1.11.1",
        oids=["2"],
    ),
    parse_function=parse_alcatel_fans,
)


check_plugin_alcatel_fans = CheckPlugin(
    name="alcatel_fans",
    service_name="Fan %s",
    discovery_function=discover_alcatel_fans,
    check_function=check_alcatel_fans,
)
