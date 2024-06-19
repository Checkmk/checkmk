#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import NamedTuple

from cmk.agent_based.v2 import (
    Attributes,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    InventoryPlugin,
    InventoryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib import fireeye


class Section(NamedTuple):
    status: str
    model: str
    serial: str


def parse_fireeye_sys_status(string_table: StringTable) -> Section | None:
    for line in string_table:
        return Section(*line)
    return None


snmp_section_fireeye_sys_status = SimpleSNMPSection(
    name="fireeye_sys_status",
    parse_function=parse_fireeye_sys_status,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.25597.11.1.1",
        oids=[
            "1",  # FE-FIREEYE-MIB::feSystemStatus
            "2",  # FE-FIREEYE-MIB::feHardwareModel
            "3",  # FE-FIREEYE-MIB::feSerialNumber
        ],
    ),
    detect=fireeye.DETECT,
)


def discover_fireeye_sys_status(section: Section) -> DiscoveryResult:
    yield Service()


def check_fireeye_sys_status(section: Section) -> CheckResult:
    yield Result(
        state=State.OK if section.status.lower() in {"good", "ok"} else State.CRIT,
        summary=f"Status: {section.status.lower()}",
    )


check_plugin_fireeye_sys_status = CheckPlugin(
    name="fireeye_sys_status",
    service_name="System status",
    discovery_function=discover_fireeye_sys_status,
    check_function=check_fireeye_sys_status,
)


def inventory_fireeye_sys_status(section: Section) -> InventoryResult:
    yield Attributes(
        path=["hardware", "system"],
        inventory_attributes={
            "serial": section.serial,
            "model": section.model,
        },
    )


inventory_plugin_fireeye_sys_status = InventoryPlugin(
    name="fireeye_sys_status",
    inventory_function=inventory_fireeye_sys_status,
)
