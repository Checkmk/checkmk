#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.juniper.lib import DETECT_JUNIPER_SCREENOS
from cmk.plugins.lib.temperature import check_temperature, TempParamType

Section = Mapping[str, int]


def parse_juniper_screenos_temp(string_table: StringTable) -> Section:
    section: dict[str, int] = {}
    for name, temp_str in string_table:
        if name.endswith("Temperature"):
            name = name.rsplit(None, 1)[0]
        try:
            section[name] = int(temp_str)
        except ValueError:
            pass
    return section


def discover_juniper_screenos_temp(section: Section) -> DiscoveryResult:
    for name in section:
        yield Service(item=name)


def check_juniper_screenos_temp(item: str, params: TempParamType, section: Section) -> CheckResult:
    if item not in section:
        return
    yield from check_temperature(
        reading=float(section[item]),
        params=params,
        unique_name=f"juniper_screenos_temp_{item}",
        value_store=get_value_store(),
    )


snmp_section_juniper_screenos_temp = SimpleSNMPSection(
    name="juniper_screenos_temp",
    detect=DETECT_JUNIPER_SCREENOS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3224.21.4.1",
        oids=["4", "3"],
    ),
    parse_function=parse_juniper_screenos_temp,
)

check_plugin_juniper_screenos_temp = CheckPlugin(
    name="juniper_screenos_temp",
    service_name="Temperature %s",
    discovery_function=discover_juniper_screenos_temp,
    check_function=check_juniper_screenos_temp,
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (70.0, 80.0)},
)
