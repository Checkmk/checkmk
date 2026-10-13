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
from cmk.plugins.fireeye.lib import DETECT, HEALTH_MAP, STATUS_MAP

# .1.3.6.1.4.1.25597.11.4.1.3.1.1.1 1 --> FE-FIREEYE-MIB::feFanIndex.1
# .1.3.6.1.4.1.25597.11.4.1.3.1.1.2 2 --> FE-FIREEYE-MIB::feFanIndex.2
# .1.3.6.1.4.1.25597.11.4.1.3.1.1.3 3 --> FE-FIREEYE-MIB::feFanIndex.3
# .1.3.6.1.4.1.25597.11.4.1.3.1.1.4 4 --> FE-FIREEYE-MIB::feFanIndex.4
# .1.3.6.1.4.1.25597.11.4.1.3.1.1.5 5 --> FE-FIREEYE-MIB::feFanIndex.5
# .1.3.6.1.4.1.25597.11.4.1.3.1.1.6 6 --> FE-FIREEYE-MIB::feFanIndex.6
# .1.3.6.1.4.1.25597.11.4.1.3.1.1.7 7 --> FE-FIREEYE-MIB::feFanIndex.7
# .1.3.6.1.4.1.25597.11.4.1.3.1.1.8 8 --> FE-FIREEYE-MIB::feFanIndex.8
# .1.3.6.1.4.1.25597.11.4.1.3.1.2.1 Ok --> FE-FIREEYE-MIB::feFanStatus.1
# .1.3.6.1.4.1.25597.11.4.1.3.1.2.2 Ok --> FE-FIREEYE-MIB::feFanStatus.2
# .1.3.6.1.4.1.25597.11.4.1.3.1.2.3 Ok --> FE-FIREEYE-MIB::feFanStatus.3
# .1.3.6.1.4.1.25597.11.4.1.3.1.2.4 Ok --> FE-FIREEYE-MIB::feFanStatus.4
# .1.3.6.1.4.1.25597.11.4.1.3.1.2.5 Ok --> FE-FIREEYE-MIB::feFanStatus.5
# .1.3.6.1.4.1.25597.11.4.1.3.1.2.6 Ok --> FE-FIREEYE-MIB::feFanStatus.6
# .1.3.6.1.4.1.25597.11.4.1.3.1.2.7 Ok --> FE-FIREEYE-MIB::feFanStatus.7
# .1.3.6.1.4.1.25597.11.4.1.3.1.2.8 Ok --> FE-FIREEYE-MIB::feFanStatus.8
# .1.3.6.1.4.1.25597.11.4.1.3.1.3.1 1 --> FE-FIREEYE-MIB::feFanIsHealthy.1
# .1.3.6.1.4.1.25597.11.4.1.3.1.3.2 1 --> FE-FIREEYE-MIB::feFanIsHealthy.2
# .1.3.6.1.4.1.25597.11.4.1.3.1.3.3 1 --> FE-FIREEYE-MIB::feFanIsHealthy.3
# .1.3.6.1.4.1.25597.11.4.1.3.1.3.4 1 --> FE-FIREEYE-MIB::feFanIsHealthy.4
# .1.3.6.1.4.1.25597.11.4.1.3.1.3.5 1 --> FE-FIREEYE-MIB::feFanIsHealthy.5
# .1.3.6.1.4.1.25597.11.4.1.3.1.3.6 1 --> FE-FIREEYE-MIB::feFanIsHealthy.6
# .1.3.6.1.4.1.25597.11.4.1.3.1.3.7 1 --> FE-FIREEYE-MIB::feFanIsHealthy.7
# .1.3.6.1.4.1.25597.11.4.1.3.1.3.8 1 --> FE-FIREEYE-MIB::feFanIsHealthy.8
# .1.3.6.1.4.1.25597.11.4.1.3.1.4.1 8281 --> FE-FIREEYE-MIB::feFanSpeed.1
# .1.3.6.1.4.1.25597.11.4.1.3.1.4.2 8281 --> FE-FIREEYE-MIB::feFanSpeed.2
# .1.3.6.1.4.1.25597.11.4.1.3.1.4.3 8281 --> FE-FIREEYE-MIB::feFanSpeed.3
# .1.3.6.1.4.1.25597.11.4.1.3.1.4.4 8281 --> FE-FIREEYE-MIB::feFanSpeed.4
# .1.3.6.1.4.1.25597.11.4.1.3.1.4.5 8281 --> FE-FIREEYE-MIB::feFanSpeed.5
# .1.3.6.1.4.1.25597.11.4.1.3.1.4.6 8281 --> FE-FIREEYE-MIB::feFanSpeed.6
# .1.3.6.1.4.1.25597.11.4.1.3.1.4.7 8281 --> FE-FIREEYE-MIB::feFanSpeed.7
# .1.3.6.1.4.1.25597.11.4.1.3.1.4.8 8281 --> FE-FIREEYE-MIB::feFanSpeed.8


def check_fireeye_fans(item: str, section: StringTable) -> CheckResult:
    for index, status, health, speed_str in section:
        if index == item:
            state, state_readable = STATUS_MAP.get(status.lower(), (2, f"unknown: {status}"))
            yield Result(state=State(state), summary=f"Status: {state_readable}")
            state, state_readable = HEALTH_MAP.get(health, (2, f"unknown: {health}"))
            yield Result(state=State(state), summary=f"Health: {state_readable}")

            yield Result(state=State.OK, summary=f"Speed: {speed_str} RPM")


def parse_fireeye_fans(string_table: StringTable) -> StringTable:
    return string_table


def discover_fireeye_fans(section: StringTable) -> DiscoveryResult:
    for line in section:
        yield Service(item=line[0])


snmp_section_fireeye_fans = SimpleSNMPSection(
    name="fireeye_fans",
    parse_function=parse_fireeye_fans,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.25597.11.4.1.3.1",
        oids=["1", "2", "3", "4"],
    ),
)


check_plugin_fireeye_fans = CheckPlugin(
    name="fireeye_fans",
    service_name="Fan %s",
    discovery_function=discover_fireeye_fans,
    check_function=check_fireeye_fans,
)
