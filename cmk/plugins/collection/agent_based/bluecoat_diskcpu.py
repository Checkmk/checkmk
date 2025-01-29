#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Self

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)


@dataclass
class CPU:
    name: str
    reading: float
    is_ok: bool

    @classmethod
    def from_line(cls, raw: Sequence[str]) -> Self:
        return cls(name=raw[0], reading=float(raw[1]), is_ok=raw[2] == "1")


Section = Mapping[str, CPU]


def parse_bluecoat_diskcpu(string_table: StringTable) -> Section:
    return {cpu.name: cpu for line in string_table for cpu in [CPU.from_line(line)]}


snmp_section_bluecoat_diskcpu = SimpleSNMPSection(
    name="bluecoat_diskcpu",
    detect=contains(".1.3.6.1.2.1.1.2.0", "1.3.6.1.4.1.3417.1.1"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3417.2.4.1.1.1",
        oids=["3", "4", "6"],
    ),
    parse_function=parse_bluecoat_diskcpu,
)


def inventory_bluecoat_diskcpu(section: Section) -> DiscoveryResult:
    yield from (Service(item=name) for name in section)


def check_bluecoat_diskcpu(item: str, section: Section) -> CheckResult:
    if (cpu := section.get(item)) is None:
        return

    # This is stupid.
    yield Metric("value", cpu.reading)
    yield Result(
        state=State.OK if cpu.is_ok else State.CRIT,
        summary=f"{cpu.reading:.0f}",  # also stupid.
    )


check_plugin_bluecoat_diskcpu = CheckPlugin(
    name="bluecoat_diskcpu",
    service_name="%s",  # will be "Disk" or "CPU" :-(
    discovery_function=inventory_bluecoat_diskcpu,
    check_function=check_bluecoat_diskcpu,
)
