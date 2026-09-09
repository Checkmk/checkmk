#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TypedDict

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.memory import check_element, MemoryLevels

# Example output:
# Overall memory
# .1.3.6.1.4.1.3375.2.1.7.1.1.0 8396496896 sysHostMemoryTotal
# .1.3.6.1.4.1.3375.2.1.7.1.2.0 1331092416 sysHostMemoryUsed
#
# TMM (Traffic Management Module) memory
# .1.3.6.1.4.1.3375.2.1.1.2.1.143 0 sysStatMemoryTotalKb
# .1.3.6.1.4.1.3375.2.1.1.2.1.144 0 sysStatMemoryUsedKb


class MemParams(TypedDict, total=False):
    levels: MemoryLevels


@dataclass(frozen=True)
class MemoryUsage:
    total: float
    used: float


Section = Mapping[str, MemoryUsage]


def parse_f5_bigip_mem(string_table: StringTable) -> Section | None:
    if not string_table:
        return None

    total, used, tmm_total, tmm_used = string_table[0]

    # The device leaves the columns of OIDs it does not answer empty, and not every device
    # reports the TMM counters. Every other value is a byte count and has to be a number,
    # so a non-numeric one is left to crash rather than silently monitoring nothing.
    section = {}
    if total and used:
        section["total"] = MemoryUsage(total=float(total), used=float(used))
    if tmm_total and tmm_used:
        section["TMM"] = MemoryUsage(total=float(tmm_total) * 1024, used=float(tmm_used) * 1024)

    return section


def discover_f5_bigip_mem(section: Section) -> DiscoveryResult:
    if "total" in section:
        yield Service(item="total")
    # The TMM counters are reported as 0 on devices that do not provide them.
    if (tmm := section.get("TMM")) is not None and tmm.total > 0:
        yield Service(item="TMM")


def check_f5_bigip_mem(item: str, params: MemParams, section: Section) -> CheckResult:
    if (memory := section.get(item)) is None:
        return

    yield from check_element(
        "Usage",
        memory.used,
        memory.total,
        params.get("levels"),
        metric_name="mem_used",
    )


snmp_section_f5_bigip_mem = SimpleSNMPSection(
    name="f5_bigip_mem",
    # Deliberately broader than the shared F5_BIGIP detect spec, which additionally
    # requires the product name to contain "big-ip".
    detect=contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.3375"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3375.2.1",
        oids=[
            "7.1.1",  # sysHostMemoryTotal
            "7.1.2",  # sysHostMemoryUsed
            "1.2.1.143",  # sysStatMemoryTotalKb
            "1.2.1.144",  # sysStatMemoryUsedKb
        ],
    ),
    parse_function=parse_f5_bigip_mem,
)


check_plugin_f5_bigip_mem = CheckPlugin(
    name="f5_bigip_mem",
    service_name="Memory %s",
    discovery_function=discover_f5_bigip_mem,
    check_function=check_f5_bigip_mem,
    check_ruleset_name="memory_simple",
    check_default_parameters=MemParams(levels=("perc_used", (80.0, 90.0))),
)
