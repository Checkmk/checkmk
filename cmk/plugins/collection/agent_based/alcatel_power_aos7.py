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
from cmk.plugins.lib.alcatel import DETECT_ALCATEL_AOS7

alcatel_power_aos7_operability_to_status_mapping = {
    "1": "up",
    "2": "down",
    "3": "testing",
    "4": "unknown",
    "5": "secondary",
    "6": "not present",  # no check status required
    "7": "unpowered",
    "8": "master",
    "9": "idle",
    "10": "power save",
}

alcatel_power_aos7_no_power_supply = "no power supply"

alcatel_power_aos7_power_type_mapping = {
    "0": alcatel_power_aos7_no_power_supply,
    "1": "AC",
    "2": "DC",
}


class PowerSupplyEntry(NamedTuple):
    status_readable: str
    power_supply_type: str


Section = Mapping[str, PowerSupplyEntry]


def parse_alcatel_power_aos7(string_table: StringTable) -> Section:
    return {
        item: PowerSupplyEntry(
            alcatel_power_aos7_operability_to_status_mapping[operability_status],
            alcatel_power_aos7_power_type_mapping.get(
                power_supply_type,
                alcatel_power_aos7_no_power_supply,
            ),
        )
        for (item, operability_status, power_supply_type) in string_table
    }


def discover_alcatel_power_aos7(section: Section) -> DiscoveryResult:
    yield from (
        Service(item=item)
        for item, device in section.items()
        if (
            device.power_supply_type != alcatel_power_aos7_no_power_supply
            and device.status_readable != "not present"
        )
    )


def check_alcatel_power_aos7(item: str, section: Section) -> CheckResult:
    if not (device := section.get(item)):
        return
    yield Result(
        state=State.OK if device.status_readable == "up" else State.CRIT,
        summary=f"[{device.power_supply_type}] Status: {device.status_readable}",
    )


snmp_section_alcatel_power_aos7 = SimpleSNMPSection(
    name="alcatel_power_aos7",
    detect=DETECT_ALCATEL_AOS7,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.6486.801.1.1.1.1.1.1.1",
        oids=[OIDEnd(), "2", "35"],
    ),
    parse_function=parse_alcatel_power_aos7,
)
check_plugin_alcatel_power_aos7 = CheckPlugin(
    name="alcatel_power_aos7",
    service_name="Power Supply %s",
    discovery_function=discover_alcatel_power_aos7,
    check_function=check_alcatel_power_aos7,
)
