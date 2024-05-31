#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

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
from cmk.plugins.lib.cisco_ucs import DETECT, Operability


def parse_cisco_ucs_fan(string_table: StringTable) -> dict[str, Operability]:
    return {
        " ".join(name.split("/")[2:]): Operability(operability)
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


def discover_cisco_ucs_fan(section: Mapping[str, Operability]) -> DiscoveryResult:
    yield from (Service(item=name) for name in section)


def check_cisco_ucs_fan(item: str, section: Mapping[str, Operability]) -> CheckResult:
    if not (operability := section.get(item)):
        return

    yield Result(
        state=operability.monitoring_state(),
        summary=f"Status: {operability.name}",
    )


check_plugin_cisco_ucs_fan = CheckPlugin(
    name="cisco_ucs_fan",
    service_name="Fan %s",
    discovery_function=discover_cisco_ucs_fan,
    check_function=check_cisco_ucs_fan,
)
