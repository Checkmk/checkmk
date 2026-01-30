#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import (
    LegacyCheckDefinition,
    LegacyDiscoveryResult,
    LegacyResult,
)
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.hp_proliant.lib import DETECT, sanitize_item

check_info = {}


def parse_hp_proliant_cpu(string_table: StringTable) -> StringTable:
    return string_table


hp_proliant_cpu_status_map = {1: "unknown", 2: "ok", 3: "degraded", 4: "failed", 5: "disabled"}
hp_proliant_cpu_status2nagios_map = {
    "unknown": 3,
    "ok": 0,
    "degraded": 2,
    "failed": 2,
    "disabled": 1,
}


def discover_hp_proliant_cpu(info: StringTable) -> LegacyDiscoveryResult:
    yield from ((sanitize_item(line[0]), {}) for line in info)


def check_hp_proliant_cpu(item: str, params: object, info: StringTable) -> LegacyResult:
    for line in info:
        if sanitize_item(line[0]) == item:
            index, slot, name, status_str = line
            snmp_status = hp_proliant_cpu_status_map[int(status_str)]
            nagios_status = hp_proliant_cpu_status2nagios_map[snmp_status]

            return (
                nagios_status,
                f'CPU{index} "{name}" in slot {slot} is in state "{snmp_status}"',
            )
    return (3, "item not found in snmp data")


check_info["hp_proliant_cpu"] = LegacyCheckDefinition(
    name="hp_proliant_cpu",
    parse_function=parse_hp_proliant_cpu,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.232.1.2.2.1.1",
        oids=["1", "2", "3", "6"],
    ),
    service_name="HW CPU %s",
    discovery_function=discover_hp_proliant_cpu,
    check_function=check_hp_proliant_cpu,
)
