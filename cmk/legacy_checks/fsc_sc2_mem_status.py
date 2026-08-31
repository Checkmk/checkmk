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
from cmk.plugins.fujitsu.lib import DETECT_FSC_SC2

_MEM_STATUS = {
    "1": (State.UNKNOWN, "unknown"),
    "2": (State.UNKNOWN, "not-present"),
    "3": (State.OK, "ok"),
    "4": (State.OK, "disabled"),
    "5": (State.CRIT, "error"),
    "6": (State.CRIT, "failed"),
    "7": (State.WARN, "prefailure-predicted"),
    "11": (State.OK, "hidden"),
}


def parse_fsc_sc2_mem_status(string_table: StringTable) -> StringTable:
    return string_table


# .1.3.6.1.4.1.231.2.10.2.2.10.6.5.1.3.1.1 "DIMM-1A"
# .1.3.6.1.4.1.231.2.10.2.2.10.6.5.1.3.1.2 "DIMM-2A"
# .1.3.6.1.4.1.231.2.10.2.2.10.6.5.1.3.1.3 "DIMM-3A"
# .1.3.6.1.4.1.231.2.10.2.2.10.6.5.1.3.1.4 "DIMM-1B"
# .1.3.6.1.4.1.231.2.10.2.2.10.6.5.1.3.1.5 "DIMM-2B"
# .1.3.6.1.4.1.231.2.10.2.2.10.6.5.1.3.1.6 "DIMM-3B"
# .1.3.6.1.4.1.231.2.10.2.2.10.6.5.1.3.1.7 "DIMM-1C"
# .1.3.6.1.4.1.231.2.10.2.2.10.6.5.1.3.1.8 "DIMM-2C"
# .1.3.6.1.4.1.231.2.10.2.2.10.6.5.1.3.1.9 "DIMM-3C"
# .1.3.6.1.4.1.231.2.10.2.2.10.6.5.1.4.1.1 3
# .1.3.6.1.4.1.231.2.10.2.2.10.6.5.1.4.1.2 2
# .1.3.6.1.4.1.231.2.10.2.2.10.6.5.1.4.1.3 2
# .1.3.6.1.4.1.231.2.10.2.2.10.6.5.1.4.1.4 3
# .1.3.6.1.4.1.231.2.10.2.2.10.6.5.1.4.1.5 2
# .1.3.6.1.4.1.231.2.10.2.2.10.6.5.1.4.1.6 2
# .1.3.6.1.4.1.231.2.10.2.2.10.6.5.1.4.1.7 3
# .1.3.6.1.4.1.231.2.10.2.2.10.6.5.1.4.1.8 2
# .1.3.6.1.4.1.231.2.10.2.2.10.6.5.1.4.1.9 2
# .1.3.6.1.4.1.231.2.10.2.2.10.6.5.1.6.1.1 4096
# .1.3.6.1.4.1.231.2.10.2.2.10.6.5.1.6.1.2 -1
# .1.3.6.1.4.1.231.2.10.2.2.10.6.5.1.6.1.3 -1
# .1.3.6.1.4.1.231.2.10.2.2.10.6.5.1.6.1.4 4096
# .1.3.6.1.4.1.231.2.10.2.2.10.6.5.1.6.1.5 -1
# .1.3.6.1.4.1.231.2.10.2.2.10.6.5.1.6.1.6 -1
# .1.3.6.1.4.1.231.2.10.2.2.10.6.5.1.6.1.7 4096
# .1.3.6.1.4.1.231.2.10.2.2.10.6.5.1.6.1.8 -1
# .1.3.6.1.4.1.231.2.10.2.2.10.6.5.1.6.1.9 -1


def discover_fsc_sc2_mem_status(section: StringTable) -> DiscoveryResult:
    for line in section:
        if line[1] != "2":
            yield Service(item=line[0])


def check_fsc_sc2_mem_status(item: str, section: StringTable) -> CheckResult:
    for designation, status, capacity in section:
        if designation == item:
            status_state, status_txt = _MEM_STATUS.get(status, (State.UNKNOWN, "unknown"))
            yield Result(state=status_state, summary=f"Status is {status_txt}, Size {capacity} MB")
            return


snmp_section_fsc_sc2_mem_status = SimpleSNMPSection(
    name="fsc_sc2_mem_status",
    parse_function=parse_fsc_sc2_mem_status,
    detect=DETECT_FSC_SC2,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.231.2.10.2.2.10.6.5.1",
        oids=["3", "4", "6"],
    ),
)


check_plugin_fsc_sc2_mem_status = CheckPlugin(
    name="fsc_sc2_mem_status",
    service_name="FSC %s",
    discovery_function=discover_fsc_sc2_mem_status,
    check_function=check_fsc_sc2_mem_status,
)
