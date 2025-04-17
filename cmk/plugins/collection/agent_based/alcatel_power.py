#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import NamedTuple

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    OIDEnd,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.alcatel import DETECT_ALCATEL

alcatel_power_operstate_map = {
    "1": "up",
    "2": "down",
    "3": "testing",
    "4": "unknown",
    "5": "secondary",
    "6": "not present",
    "7": "unpowered",
    "9": "master",
}

alcatel_power_no_power_supply_info = "no power supply"

alcatel_power_type_map = {
    "0": alcatel_power_no_power_supply_info,
    "1": "AC",
    "2": "DC",
}


class AlcatelPowerEntry(NamedTuple):
    oper_state_readable: str
    power_type: str


Section = Mapping[str, AlcatelPowerEntry]


def parse_alcatel_power(string_table: StringTable) -> Section:
    return {
        oidend: AlcatelPowerEntry(
            alcatel_power_operstate_map.get(status, "unknown[%s]" % status),
            alcatel_power_type_map.get(power_type, alcatel_power_no_power_supply_info),
        )
        for oidend, status, power_type in reversed(string_table)
    }


def discover_alcatel_power(section: Section) -> DiscoveryResult:
    yield from (
        Service(item=item)
        for item, device in section.items()
        if (
            device.power_type != alcatel_power_no_power_supply_info
            and device.oper_state_readable != "not present"
        )
    )


def check_alcatel_power(item: str, section: Section) -> CheckResult:
    if not (device := section.get(item)):
        return
    yield Result(
        state=State.OK if device.oper_state_readable == "up" else State.CRIT,
        summary=f"[{device.power_type}] Operational status: {device.oper_state_readable}",
    )


snmp_section_alcatel_power = SimpleSNMPSection(
    name="alcatel_power",
    detect=DETECT_ALCATEL,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.6486.800.1.1.1.1.1.1.1",
        oids=[OIDEnd(), "2", "36"],
    ),
    parse_function=parse_alcatel_power,
)
check_plugin_alcatel_power = CheckPlugin(
    name="alcatel_power",
    service_name="Power Supply %s",
    discovery_function=discover_alcatel_power,
    check_function=check_alcatel_power,
)
