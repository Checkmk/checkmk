#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.emc import DETECT_ISILON

check_info = {}


def inventory_emc_isilon_diskstatus(info):
    for disk_id, _name, _disk_status, _serial in info:
        yield disk_id, None


def check_emc_isilon_diskstatus(item, _no_params, info):
    for disk_id, name, disk_status, serial in info:
        if disk_id == item:
            message = f"Disk {name}, serial number {serial} status is {disk_status}"
            if disk_status in ["HEALTHY", "L3"]:
                status = 0
            else:
                status = 2
            return status, message
    return None


def parse_emc_isilon_diskstatus(string_table: StringTable) -> StringTable:
    return string_table


check_info["emc_isilon_diskstatus"] = LegacyCheckDefinition(
    name="emc_isilon_diskstatus",
    parse_function=parse_emc_isilon_diskstatus,
    detect=DETECT_ISILON,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12124.2.52.1",
        oids=["1", "4", "5", "7"],
    ),
    service_name="Disk bay %s Status",
    discovery_function=inventory_emc_isilon_diskstatus,
    check_function=check_emc_isilon_diskstatus,
)
