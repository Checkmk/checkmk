#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)

Section = Mapping[str, str]


def parse_avaya_45xx_fan(string_table: StringTable) -> Section:
    return {str(idx): status for idx, (status,) in enumerate(string_table)}


snmp_section_avaya_45xx_fan = SimpleSNMPSection(
    name="avaya_45xx_fan",
    detect=contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.45.3"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.45.1.6.3.3.1.1.10",
        oids=["6"],
    ),
    parse_function=parse_avaya_45xx_fan,
)


def inventory_avaya_45xx_fan(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


STATE_MAP = {
    "1": ("Other", State.UNKNOWN),
    "2": ("Not available", State.UNKNOWN),
    "3": ("Removed", State.OK),
    "4": ("Disabled", State.OK),
    "5": ("Normal", State.OK),
    "6": ("Reset in Progress", State.WARN),
    "7": ("Testing", State.WARN),
    "8": ("Warning", State.WARN),
    "9": ("Non fatal error", State.WARN),
    "10": ("Fatal error", State.CRIT),
    "11": ("Not configured", State.WARN),
    "12": ("Obsoleted", State.OK),
}


def check_avaya_45xx_fan(item: str, section: Section) -> CheckResult:
    if (fan_status := section.get(item)) is None:
        return

    text, state = STATE_MAP.get(fan_status, (f"Unknown fan status: {fan_status!r}", State.UNKNOWN))
    yield Result(state=state, summary=text)


check_plugin_avaya_45xx_fan = CheckPlugin(
    name="avaya_45xx_fan",
    service_name="Fan Chassis %s",
    discovery_function=inventory_avaya_45xx_fan,
    check_function=check_avaya_45xx_fan,
)
