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
    StringTable,
)
from cmk.plugins.hp_proliant.lib import DETECT, sanitize_item, STATUS_MAP

_CPU_STATUS_MAP = {1: "unknown", 2: "ok", 3: "degraded", 4: "failed", 5: "disabled"}


def parse_hp_proliant_cpu(string_table: StringTable) -> StringTable:
    return string_table


def discover_hp_proliant_cpu(section: StringTable) -> DiscoveryResult:
    yield from (Service(item=sanitize_item(line[0])) for line in section)


def check_hp_proliant_cpu(item: str, section: StringTable) -> CheckResult:
    for line in section:
        if sanitize_item(line[0]) != item:
            continue
        index, slot, name, status_str = line
        snmp_status = _CPU_STATUS_MAP[int(status_str)]
        yield Result(
            state=STATUS_MAP[snmp_status],
            summary=f'CPU{index} "{name}" in slot {slot} is in state "{snmp_status}"',
        )
        return


snmp_section_hp_proliant_cpu = SimpleSNMPSection(
    name="hp_proliant_cpu",
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.232.1.2.2.1.1",
        oids=["1", "2", "3", "6"],
    ),
    parse_function=parse_hp_proliant_cpu,
)


check_plugin_hp_proliant_cpu = CheckPlugin(
    name="hp_proliant_cpu",
    service_name="HW CPU %s",
    discovery_function=discover_hp_proliant_cpu,
    check_function=check_hp_proliant_cpu,
)
