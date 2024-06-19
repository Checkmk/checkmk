#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum

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
from cmk.plugins.lib.cisco_ucs import check_cisco_fault, DETECT, Fault, Operability, Presence


class MemoryType(Enum):
    undiscovered = "0"
    other = "1"
    unknown = "2"
    dram = "3"
    edram = "4"
    vram = "5"
    sram = "6"
    ram = "7"
    rom = "8"
    flash = "9"
    eeprom = "10"
    feprom = "11"
    eprom = "12"
    cdram = "13"
    n3DRAM = "14"
    sdram = "15"
    sgram = "16"
    rdram = "17"
    ddr = "18"
    ddr2 = "19"
    ddr2FbDimm = "20"
    ddr3 = "24"
    fbd2 = "25"
    ddr4 = "26"

    def monitoring_state(self) -> State:
        return State.OK


@dataclass(frozen=True, kw_only=True)
class MemoryModule:
    serial: str
    capacity: str
    memtype: MemoryType
    operability: Operability
    presence: Presence
    id: str


def parse_cisco_ucs_mem(string_table: StringTable) -> dict[str, MemoryModule]:
    return {
        name: MemoryModule(
            serial=serial,
            capacity=capacity,
            memtype=MemoryType(memtype),
            operability=Operability(operability),
            presence=Presence(presence),
            id=id,
        )
        for name, serial, memtype, capacity, operability, presence, id in string_table
    }


snmp_section_cisco_ucs_mem = SimpleSNMPSection(
    name="cisco_ucs_mem",
    parse_function=parse_cisco_ucs_mem,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9.9.719.1.30.11.1",
        oids=[
            "3",  # .1.3.6.1.4.1.9.9.719.1.30.11.1.3  cucsMemoryUnitRn
            "19",  # .1.3.6.1.4.1.9.9.719.1.30.11.1.19 cucsMemoryUnitSerial
            "23",  # .1.3.6.1.4.1.9.9.719.1.30.11.1.23 cucsMemoryUnitType
            "6",  # .1.3.6.1.4.1.9.9.719.1.30.11.1.6  cucsMemoryUnitCapacity
            "14",  # .1.3.6.1.4.1.9.9.719.1.30.11.1.14 cucsMemoryUnitOperability
            "17",  # .1.3.6.1.4.1.9.9.719.1.30.11.1.17 cucsMemoryUnitPresence
            "2",  # .1.3.6.1.4.1.9.9.719.1.30.11.1.2  cucsMemoryUnitDn
        ],
    ),
    detect=DETECT,
)


def discover_cisco_ucs_mem(
    section_cisco_ucs_mem: Mapping[str, MemoryModule] | None,
    section_cisco_ucs_fault: Mapping[str, Sequence[Fault]] | None,
) -> DiscoveryResult:
    if not section_cisco_ucs_mem:
        return

    yield from (
        Service(item=name)
        for name, memory_module in section_cisco_ucs_mem.items()
        if memory_module.presence is not Presence.missing
    )


def check_cisco_ucs_mem(
    item: str,
    section_cisco_ucs_mem: Mapping[str, MemoryModule] | None,
    section_cisco_ucs_fault: Mapping[str, Sequence[Fault]] | None,
) -> CheckResult:
    if not (memory_module := (section_cisco_ucs_mem or {}).get(item)):
        return

    yield Result(
        state=memory_module.operability.monitoring_state(),
        summary=f"Status: {memory_module.operability.name}",
    )
    yield Result(
        state=memory_module.presence.monitoring_state(),
        summary=f"Presence: {memory_module.presence.name}",
    )
    yield Result(state=State.OK, summary=f"Type: {memory_module.memtype.name}")
    yield Result(
        state=State.OK, summary=f"Size: {memory_module.capacity} MB, SN: {memory_module.serial}"
    )

    yield from check_cisco_fault((section_cisco_ucs_fault or {}).get(memory_module.id, []))


check_plugin_cisco_ucs_mem = CheckPlugin(
    name="cisco_ucs_mem",
    service_name="Memory %s",
    sections=["cisco_ucs_mem", "cisco_ucs_fault"],
    discovery_function=discover_cisco_ucs_mem,
    check_function=check_cisco_ucs_mem,
)
