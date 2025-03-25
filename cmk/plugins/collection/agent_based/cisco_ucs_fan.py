#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.cisco_ucs import check_cisco_fault, DETECT, Fault, Operability


@dataclass(frozen=True, kw_only=True)
class FanModule:
    operability: Operability
    id: str


def parse_cisco_ucs_fan(string_table: StringTable) -> dict[str, FanModule]:
    return {
        " ".join(name.split("/")[2:]): FanModule(operability=Operability(operability), id=name)
        for name, operability in string_table
    }


snmp_section_cisco_ucs_fan = SimpleSNMPSection(
    name="cisco_ucs_fan",
    parse_function=parse_cisco_ucs_fan,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9.9.719.1.15.12.1",
        oids=[
            "2",  # .1.3.6.1.4.1.9.9.719.1.15.12.1.2  cucsEquipmentFanDn
            "10",  # .1.3.6.1.4.1.9.9.719.1.15.12.1.10 cucsEquipmentFanOperability
        ],
    ),
    detect=DETECT,
)


def discover_cisco_ucs_fan(
    section_cisco_ucs_fan: Mapping[str, FanModule] | None,
    section_cisco_ucs_fault: Mapping[str, Sequence[Fault]] | None,
) -> DiscoveryResult:
    if not section_cisco_ucs_fan:
        return
    yield from (Service(item=name) for name in section_cisco_ucs_fan)


def check_cisco_ucs_fan(
    item: str,
    section_cisco_ucs_fan: Mapping[str, FanModule] | None,
    section_cisco_ucs_fault: Mapping[str, Sequence[Fault]] | None,
) -> CheckResult:
    if not (fan_module := (section_cisco_ucs_fan or {}).get(item)):
        return

    yield Result(
        state=fan_module.operability.monitoring_state(),
        summary=f"Status: {fan_module.operability.name}",
    )

    yield from check_cisco_fault((section_cisco_ucs_fault or {}).get(fan_module.id, []))


check_plugin_cisco_ucs_fan = CheckPlugin(
    name="cisco_ucs_fan",
    service_name="Fan %s",
    sections=["cisco_ucs_fan", "cisco_ucs_fault"],
    discovery_function=discover_cisco_ucs_fan,
    check_function=check_cisco_ucs_fan,
)
