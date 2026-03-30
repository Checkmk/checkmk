#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.temperature import check_temperature, TempParamType
from cmk.plugins.rittal.lib.cmciii import DETECT_CMCIII_LCP

# Note: The CMCIII checks for Water IN/OUT and similar stuff are
# deep and fundamentally broken (such as the implementation of
# Rittal). Need to rewrite an make *one* check with subchecks.

# [['Fan Unit'],
#  ['V09.005'],
#  ['V0000'],
#  ['OK'],
#  ['2'],
#  ['Air-Temperatures'],
#  ['19.8 \xb0C'],
#  ['19.0 \xb0C'],
#  ['18.2 \xb0C'],
#  ['19.9 \xb0C'],
#  ['18.9 \xb0C'],
#  ...
#  ['Water Unit'],
#  ['V09.002'],
#  ['V0000'],
#  ['OK'],
#  ['2'],
#  ['Water-In'],
#  ['18.2 \xb0C'],
#  ['50.0 \xb0C'],
#  ['40.0 \xb0C'],
#  ...
# ]]


Section = list[str]


def parse_cmciii_lcp_water(string_table: StringTable) -> Section:
    units = {}
    unit_lines: list[str] | None = None
    for line in string_table:
        if line[0].endswith(" Unit"):
            unit_name = line[0].split(" ")[0]
            unit_lines = []
            units[unit_name] = unit_lines
        elif unit_lines is not None:
            unit_lines.append(line[0])

    if "Water" in units:
        return units["Water"]

    return []


def discover_cmciii_lcp_water(section: Section) -> DiscoveryResult:
    if section:
        yield Service(item="IN")
        yield Service(item="OUT")


def _parse_status(status_name: str) -> State:
    match status_name.lower():
        case "ok":
            return State.OK
        case "warning":
            return State.WARN
        case _:
            return State.CRIT


def check_cmciii_lcp_water(item: str, params: TempParamType, section: Section) -> CheckResult:
    if not section:
        return

    unit_status_name = section[2]
    yield Result(state=_parse_status(unit_status_name), summary=f"Unit: {unit_status_name}")

    if item == "IN":
        lines = section[5:12]
    else:
        lines = section[14:21]

    # ['18.2 \xb0C', '50.0 \xb0C', '40.0 \xb0C', '13.0 \xb0C', '10.0 \xb0C', '3 %', 'OK']

    temperatures = [float(x.split()[0]) for x in lines[0:5]]
    temp = temperatures[0]
    limits = temperatures[1:]
    status = _parse_status(lines[-1])

    yield from check_temperature(
        temp,
        params,
        unique_name=f"cmciii_lcp_water_{item}",
        value_store=get_value_store(),
        dev_levels=(limits[1], limits[0]),
        dev_levels_lower=(limits[2], limits[3]),
        dev_status=status.value,
        dev_status_name=status.name,
    )


snmp_section_cmciii_lcp_water = SimpleSNMPSection(
    name="cmciii_lcp_water",
    detect=DETECT_CMCIII_LCP,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2606.7.4.2.2.1.10",
        oids=["2"],
    ),
    parse_function=parse_cmciii_lcp_water,
)


check_plugin_cmciii_lcp_water = CheckPlugin(
    name="cmciii_lcp_water",
    service_name="Temperature Water LCP %s",
    discovery_function=discover_cmciii_lcp_water,
    check_function=check_cmciii_lcp_water,
    check_ruleset_name="temperature",
    check_default_parameters={},
)
