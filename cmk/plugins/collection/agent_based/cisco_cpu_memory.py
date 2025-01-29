#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence
from typing import Any, TypedDict

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    OIDEnd,
    Service,
    SNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.cisco_mem import check_cisco_mem_sub, DETECT_MULTIITEM


class MemInfo(TypedDict):
    mem_used: int
    mem_free: int
    mem_reserved: int


Section = Mapping[str, MemInfo]


def _to_bytes(raw: str) -> int:
    return int(float(raw) * 1024)


def parse_cisco_cpu_memory_multiitem(string_table: Sequence[StringTable]) -> Section:
    ph_idx_to_desc = {
        idx: desc[4:] if desc.lower().startswith("cpu ") else desc for idx, desc in string_table[1]
    }

    parsed: dict[str, MemInfo] = {}
    for idx, used, free, reserved in string_table[0]:
        if used == "0" and free == "0":
            continue

        name = ph_idx_to_desc.get(idx, idx)
        try:
            parsed[name] = {
                "mem_used": _to_bytes(used),
                "mem_free": _to_bytes(free),
                "mem_reserved": _to_bytes(reserved),
            }
        except ValueError:
            pass
    return parsed


snmp_section_cisco_cpu_memory = SNMPSection(
    name="cisco_cpu_memory",
    parse_function=parse_cisco_cpu_memory_multiitem,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.9.9.109.1.1.1.1",
            oids=[
                "2",  # cpmCPUTotalPhysicalIndex
                "12",  # cpmCPUMemoryUsed
                "13",  # cpmCPUMemoryFree
                "14",  # cpmCPUMemoryKernelReserved
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.2.1.47.1.1.1",
            oids=[
                OIDEnd(),  # OID index
                "1.7",  # entPhysicalName
            ],
        ),
    ],
    detect=DETECT_MULTIITEM,
)


def discover_cisco_cpu_memory_multiitem(section: Section) -> DiscoveryResult:
    yield from (Service(item=key) for key in section)


def check_cisco_cpu_memory_multiitem(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if (data := section.get(item)) is None:
        return
    mem_used = data["mem_used"]
    mem_free = data["mem_free"]
    mem_reserved = data["mem_reserved"]
    mem_occupied = mem_used + mem_reserved
    mem_total = mem_used + mem_free
    yield from check_cisco_mem_sub(get_value_store(), item, params, mem_occupied, mem_total)


check_plugin_cisco_cpu_memory = CheckPlugin(
    name="cisco_cpu_memory",
    service_name="CPU Memory utilization %s",
    discovery_function=discover_cisco_cpu_memory_multiitem,
    check_function=check_cisco_cpu_memory_multiitem,
    check_ruleset_name="cisco_cpu_memory",
    check_default_parameters={},
)
