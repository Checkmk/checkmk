#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.fujitsu.lib import DETECT_FSC_SC2

_PSU_STATUS = {
    "1": (State.UNKNOWN, "Status is unknown"),
    "2": (State.WARN, "Status is not-present"),
    "3": (State.OK, "Status is ok"),
    "4": (State.CRIT, "Status is failed"),
    "5": (State.CRIT, "Status is ac-fail"),
    "6": (State.CRIT, "Status is dc-fail"),
    "7": (State.CRIT, "Status is critical-temperature"),
    "8": (State.WARN, "Status is not-manageable"),
    "9": (State.WARN, "Status is fan-failure-predicted"),
    "10": (State.CRIT, "Status is fan-failure"),
    "11": (State.WARN, "Status is power-safe-mode"),
    "12": (State.WARN, "Status is non-redundant-dc-fail"),
    "13": (State.WARN, "Status is non-redundant-ac-fail"),
}

# .1.3.6.1.4.1.231.2.10.2.2.10.6.2.1.3.1.1 "PSU1"
# .1.3.6.1.4.1.231.2.10.2.2.10.6.2.1.3.1.2 "PSU2"
# .1.3.6.1.4.1.231.2.10.2.2.10.6.2.1.5.1.1 3
# .1.3.6.1.4.1.231.2.10.2.2.10.6.2.1.5.1.2 3
# .1.3.6.1.4.1.231.2.10.2.2.10.6.2.1.6.1.1 52
# .1.3.6.1.4.1.231.2.10.2.2.10.6.2.1.6.1.2 40
# .1.3.6.1.4.1.231.2.10.2.2.10.6.2.1.7.1.1 448
# .1.3.6.1.4.1.231.2.10.2.2.10.6.2.1.7.1.2 448


def discover_fsc_sc2_psu(section: StringTable) -> DiscoveryResult:
    for line in section:
        if line[1] != "2":
            yield Service(item=line[0])


def check_fsc_sc2_psu(item: str, section: StringTable) -> CheckResult:
    for designation, status, load, nominal in section:
        if designation == item:
            state, state_readable = _PSU_STATUS.get(status, (State.UNKNOWN, "Status is unknown"))
            yield Result(state=state, summary=state_readable)
            if nominal and load:
                yield Result(
                    state=State.OK,
                    summary=f"Nominal load: {nominal} W, Actual load: {load} W",
                )
                yield Metric("power", int(load))
            else:
                yield Result(state=State.OK, summary="Did not receive load data")


def parse_fsc_sc2_psu(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_fsc_sc2_psu = SimpleSNMPSection(
    name="fsc_sc2_psu",
    parse_function=parse_fsc_sc2_psu,
    detect=DETECT_FSC_SC2,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.231.2.10.2.2.10.6.2.1",
        oids=["3", "5", "6", "7"],
    ),
)


check_plugin_fsc_sc2_psu = CheckPlugin(
    name="fsc_sc2_psu",
    service_name="FSC %s",
    discovery_function=discover_fsc_sc2_psu,
    check_function=check_fsc_sc2_psu,
)
