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
from cmk.plugins.emc.lib import DETECT_ISILON


def discover_emc_isilon_diskstatus(section: StringTable) -> DiscoveryResult:
    for disk_id, _name, _disk_status, _serial in section:
        yield Service(item=disk_id)


def check_emc_isilon_diskstatus(item: str, section: StringTable) -> CheckResult:
    for disk_id, name, disk_status, serial in section:
        if disk_id == item:
            status = State.OK if disk_status in ["HEALTHY", "L3"] else State.CRIT
            yield Result(
                state=status, summary=f"Disk {name}, serial number {serial} status is {disk_status}"
            )
            return


def parse_emc_isilon_diskstatus(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_emc_isilon_diskstatus = SimpleSNMPSection(
    name="emc_isilon_diskstatus",
    detect=DETECT_ISILON,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12124.2.52.1",
        oids=["1", "4", "5", "7"],
    ),
    parse_function=parse_emc_isilon_diskstatus,
)


check_plugin_emc_isilon_diskstatus = CheckPlugin(
    name="emc_isilon_diskstatus",
    service_name="Disk bay %s Status",
    discovery_function=discover_emc_isilon_diskstatus,
    check_function=check_emc_isilon_diskstatus,
)
