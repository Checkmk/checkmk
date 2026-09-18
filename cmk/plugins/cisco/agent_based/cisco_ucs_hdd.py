#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# comNET GmbH, Fabian Binder - 2018-05-07

from collections.abc import Mapping
from typing import Final, NamedTuple

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.cisco.lib_ucs import DETECT, MAP_OPERABILITY

_HOT_SPARE_VALUES: Final = {3, 4}


class HDD(NamedTuple):
    disk_id: str
    model: str
    state: int
    operability: str
    serial: str
    size: int
    vendor: str
    drive_status: int


Section = Mapping[str, HDD]


def parse_cisco_ucs_hdd(string_table: StringTable) -> Section:
    return {
        disk_id: HDD(
            disk_id,
            model,
            *MAP_OPERABILITY[r_operability],
            serial,
            int(r_size or 0) * 1024**2,
            vendor,
            int(drive_status),
        )
        for disk_id, model, r_operability, serial, r_size, vendor, drive_status in string_table
    }


def discover_cisco_ucs_hdd(section: Section) -> DiscoveryResult:
    yield from (
        Service(item=hdd.disk_id) for hdd in section.values() if hdd.operability != "removed"
    )


def check_cisco_ucs_hdd(item: str, section: Section) -> CheckResult:
    hdd = section.get(item)
    if hdd is None:
        return

    if hdd.drive_status in _HOT_SPARE_VALUES:
        yield Result(state=State.OK, summary=f"Status: {hdd.operability} (hot spare)")
    else:
        yield Result(state=State(hdd.state), summary=f"Status: {hdd.operability}")
    yield Result(state=State.OK, summary=f"Size: {render.disksize(hdd.size)}")
    yield Result(state=State.OK, summary=f"Model: {hdd.model}")
    yield Result(state=State.OK, summary=f"Vendor: {hdd.vendor}")
    yield Result(state=State.OK, summary=f"Serial number: {hdd.serial}")


snmp_section_cisco_ucs_hdd = SimpleSNMPSection(
    name="cisco_ucs_hdd",
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9.9.719.1.45.4.1",
        oids=["6", "7", "9", "12", "13", "14", "18"],
    ),
    parse_function=parse_cisco_ucs_hdd,
)


check_plugin_cisco_ucs_hdd = CheckPlugin(
    name="cisco_ucs_hdd",
    service_name="HDD %s",
    discovery_function=discover_cisco_ucs_hdd,
    check_function=check_cisco_ucs_hdd,
)
