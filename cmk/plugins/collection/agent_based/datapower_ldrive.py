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
from cmk.plugins.lib.datapower import DETECT


def inventory_datapower_ldrive(section: StringTable) -> DiscoveryResult:
    for controller, ldrive, _raid_level, _num_drives, _status in section:
        item = f"{controller}-{ldrive}"
        yield Service(item=item)


def check_datapower_ldrive(item: str, section: StringTable) -> CheckResult:
    datapower_ldrive_status = {
        "1": (State.CRIT, "offline"),
        "2": (State.CRIT, "partially degraded"),
        "3": (State.CRIT, "degraded"),
        "4": (State.OK, "optimal"),
        "5": (State.WARN, "unknown"),
    }
    datapower_ldrive_raid = {
        "1": "0",
        "2": "1",
        "3": "1E",
        "4": "5",
        "5": "6",
        "6": "10",
        "7": "50",
        "8": "60",
        "9": "undefined",
    }
    for controller, ldrive, raid_level, num_drives, status in section:
        if item == f"{controller}-{ldrive}":
            state, state_txt = datapower_ldrive_status[status]
            raid_level = datapower_ldrive_raid[raid_level]
            infotext = (
                f"Status: {state_txt}, RAID Level: {raid_level}, Number of Drives: {num_drives}"
            )
            yield Result(state=state, summary=infotext)
            return


def parse_datapower_ldrive(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_datapower_ldrive = SimpleSNMPSection(
    name="datapower_ldrive",
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.14685.3.1.259.1",
        oids=["1", "2", "4", "5", "6"],
    ),
    parse_function=parse_datapower_ldrive,
)
check_plugin_datapower_ldrive = CheckPlugin(
    name="datapower_ldrive",
    service_name="Logical Drive %s",
    discovery_function=inventory_datapower_ldrive,
    check_function=check_datapower_ldrive,
)
