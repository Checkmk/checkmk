#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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
from cmk.plugins.decru.lib import DETECT_DECRU
from cmk.plugins.lib.temperature import check_temperature, fahrenheit_to_celsius, TempParamType


def parse_decru_temps(string_table: StringTable) -> StringTable:
    return string_table


def discover_decru_temps(section: StringTable) -> DiscoveryResult:
    for name, rawtemp in section:
        # device doesn't provide warning/critical levels
        # instead, this uses the temperature at inventory-time +4/+8
        temp_c = int(fahrenheit_to_celsius(float(rawtemp)))
        yield Service(item=name, parameters={"levels": (temp_c + 4, temp_c + 8)})


def check_decru_temps(item: str, params: TempParamType, section: StringTable) -> CheckResult:
    for name, rawtemp in section:
        if name == item:
            yield from check_temperature(
                fahrenheit_to_celsius(float(rawtemp)),
                params,
                unique_name=f"decru_temps_{item}",
                value_store=get_value_store(),
            )
            return


snmp_section_decru_temps = SimpleSNMPSection(
    name="decru_temps",
    detect=DETECT_DECRU,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12962.1.2.4.1",
        oids=["2", "3"],
    ),
    parse_function=parse_decru_temps,
)


check_plugin_decru_temps = CheckPlugin(
    name="decru_temps",
    service_name="Temperature %s",
    discovery_function=discover_decru_temps,
    check_function=check_decru_temps,
    check_ruleset_name="temperature",
    check_default_parameters={},
)
