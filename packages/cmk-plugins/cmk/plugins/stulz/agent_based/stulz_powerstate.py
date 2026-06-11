#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    OIDEnd,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.stulz.lib import DETECT_STULZ

Section = Mapping[str, str]


def parse_stulz_powerstate(string_table: StringTable) -> Section:
    parsed: dict[str, str] = {}
    for oidend, value in string_table:
        bus, unit = oidend.split(".")[0:2]
        parsed.setdefault(f"{bus}-{unit}", value)
    return parsed


def discover_stulz_powerstate(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_stulz_powerstate(item: str, section: Section) -> CheckResult:
    if item in section:
        if section[item] != "1":
            message = "Device powered off"
            power_state = 2
        else:
            message = "Device powered on"
            power_state = 6

        yield Result(state=State.OK, summary=message)
        yield Metric("state", power_state)


snmp_section_stulz_powerstate = SimpleSNMPSection(
    name="stulz_powerstate",
    detect=DETECT_STULZ,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.29462.10.2.1.4.1.1.1",
        oids=[OIDEnd(), "1013"],
    ),
    parse_function=parse_stulz_powerstate,
)

check_plugin_stulz_powerstate = CheckPlugin(
    name="stulz_powerstate",
    service_name="State %s ",
    discovery_function=discover_stulz_powerstate,
    check_function=check_stulz_powerstate,
)
