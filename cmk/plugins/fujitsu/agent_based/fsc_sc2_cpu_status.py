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

_CPU_STATUS = {
    "1": (State.UNKNOWN, "unknown"),
    "2": (State.UNKNOWN, "not-present"),
    "3": (State.OK, "ok"),
    "4": (State.OK, "disabled"),
    "5": (State.CRIT, "error"),
    "6": (State.CRIT, "failed"),
    "7": (State.WARN, "missing-termination"),
    "8": (State.WARN, "prefailure-warning"),
}


def parse_fsc_sc2_cpu_status(string_table: StringTable) -> StringTable:
    return string_table


# .1.3.6.1.4.1.231.2.10.2.2.10.6.4.1.3.1.1 "CPU1"
# .1.3.6.1.4.1.231.2.10.2.2.10.6.4.1.3.1.2 "CPU2"
# .1.3.6.1.4.1.231.2.10.2.2.10.6.4.1.4.1.1 3
# .1.3.6.1.4.1.231.2.10.2.2.10.6.4.1.4.1.2 2
# .1.3.6.1.4.1.231.2.10.2.2.10.6.4.1.5.1.1 "Intel(R) Xeon(R) CPU E5-2620 v2 @ 2.10GHz"
# .1.3.6.1.4.1.231.2.10.2.2.10.6.4.1.5.1.2 ""
# .1.3.6.1.4.1.231.2.10.2.2.10.6.4.1.8.1.1 2100
# .1.3.6.1.4.1.231.2.10.2.2.10.6.4.1.8.1.2 0
# .1.3.6.1.4.1.231.2.10.2.2.10.6.4.1.13.1.1 6
# .1.3.6.1.4.1.231.2.10.2.2.10.6.4.1.13.1.2 0


def discover_fsc_sc2_cpu_status(section: StringTable) -> DiscoveryResult:
    for line in section:
        if line[1] != "2":
            yield Service(item=line[0])


def check_fsc_sc2_cpu_status(item: str, section: StringTable) -> CheckResult:
    for designation, status, model, speed, cores in section:
        if designation == item:
            status_state, status_txt = _CPU_STATUS.get(status, (State.UNKNOWN, "unknown"))
            yield Result(
                state=status_state,
                summary=f"Status is {status_txt}, {model}, {cores} cores @ {speed} MHz",
            )
            return


snmp_section_fsc_sc2_cpu_status = SimpleSNMPSection(
    name="fsc_sc2_cpu_status",
    parse_function=parse_fsc_sc2_cpu_status,
    detect=DETECT_FSC_SC2,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.231.2.10.2.2.10.6.4.1",
        oids=["3", "4", "5", "8", "13"],
    ),
)


check_plugin_fsc_sc2_cpu_status = CheckPlugin(
    name="fsc_sc2_cpu_status",
    service_name="FSC %s",
    discovery_function=discover_fsc_sc2_cpu_status,
    check_function=check_fsc_sc2_cpu_status,
)
