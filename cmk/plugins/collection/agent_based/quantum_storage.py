#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any, NamedTuple

from cmk.agent_based.v2 import (
    Attributes,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    exists,
    InventoryPlugin,
    InventoryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)


class Section(NamedTuple):
    manufacturer: str
    product: str
    revision: str
    state: str
    serial: str


def parse_quantum_storage_info(string_table: StringTable) -> Section | None:
    return Section(*string_table[0]) if string_table else None


snmp_section_snmp_quantum_storage_info = SimpleSNMPSection(
    name="snmp_quantum_storage_info",
    parse_function=parse_quantum_storage_info,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2036.2.1.1",  # qSystemInfo
        oids=[
            "4",  # 0 1 qVendorID
            "5",  # 0 2 qProdId
            "6",  # 0 3 qProdRev
            "7",  # qState
            "12",  # 0 4 qSerialNumber
        ],
    ),
    detect=exists(".1.3.6.1.4.1.2036.2.1.1.4.0"),
)

_QUANTUM_DEVICE_STATE: Mapping[str, str] = {
    "1": "Unavailable",
    "2": "Available",
    "3": "Online",
    "4": "Offline",
    "5": "Going online",
    "6": "State not available",
}


def discover_quantum_storage_status(section: Section) -> DiscoveryResult:
    yield Service()


def check_quantum_storage_status(params: Mapping[str, Any], section: Section) -> CheckResult:
    state_txt = _QUANTUM_DEVICE_STATE.get(section.state, f"Unknown [{section.state}]")
    yield Result(
        state=State(params["map_states"].get(state_txt, 3)),
        summary=state_txt,
    )


check_plugin_quantum_storage_status = CheckPlugin(
    name="quantum_storage_status",
    sections=["snmp_quantum_storage_info"],
    service_name="Device status",
    discovery_function=discover_quantum_storage_status,
    check_function=check_quantum_storage_status,
    check_ruleset_name="quantum_storage_status",
    check_default_parameters={
        "map_states": {
            "unavailable": 2,
            "available": 0,
            "online": 0,
            "offline": 2,
            "going online": 1,
            "state not available": 3,
        },
    },
)


def inv_snmp_quantum_storage_info(section: Section) -> InventoryResult:
    yield Attributes(
        path=["hardware", "system"],
        inventory_attributes={
            "manufacturer": section.manufacturer,
            "product": section.product,
            "revision": section.revision,
            "serial": section.serial,
        },
    )


inventory_plugin_snmp_quantum_storage_info = InventoryPlugin(
    name="snmp_quantum_storage_info",
    inventory_function=inv_snmp_quantum_storage_info,
)
