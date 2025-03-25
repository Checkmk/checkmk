#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)
from cmk.plugins.lib.temperature import check_temperature, TempParamDict


@dataclass(frozen=True)
class Section:
    temp: float | None
    status: str


def parse_dell_powerconnect_temp(string_table: StringTable) -> Section | None:
    try:
        temp_str, dev_status = string_table[0]
    except (IndexError, ValueError):
        return None
    try:
        temp = float(temp_str)
    except ValueError:
        temp = None
    return Section(
        temp,
        {
            "1": "OK",
            "2": "unavailable",
            "3": "non operational",
        }.get(dev_status, "unknown[%s]" % dev_status),
    )


snmp_section_dell_powerconnect_temp = SimpleSNMPSection(
    name="dell_powerconnect_temp",
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.674.10895"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.89.53.15.1",
        oids=["9", "10"],
    ),
    parse_function=parse_dell_powerconnect_temp,
)


def check_dell_powerconnect_temp(item: str, params: TempParamDict, section: Section) -> CheckResult:
    if section.status == "OK":
        state = State.OK
    elif section.status == "unavailable":
        state = State.WARN
    elif section.status == "non operational":
        state = State.CRIT
    else:
        state = State.UNKNOWN

    if section.temp is None:
        yield Result(state=state, summary=f"Status: {section.status}")
        return

    yield from check_temperature(
        section.temp,
        params,
        dev_status=state.value,
        dev_status_name=section.status,
    )


def discover_dell_powerconnect_temp(section: Section) -> DiscoveryResult:
    yield Service(item="Ambient")


check_plugin_dell_powerconnect_temp = CheckPlugin(
    name="dell_powerconnect_temp",
    service_name="Temperature %s",
    discovery_function=discover_dell_powerconnect_temp,
    check_function=check_dell_powerconnect_temp,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (35.0, 40.0),
        "device_levels_handling": "dev",
    },
)
