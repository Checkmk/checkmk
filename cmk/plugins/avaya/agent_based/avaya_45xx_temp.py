#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    get_value_store,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.temperature import check_temperature, TempParamType


def parse_avaya_45xx_temp(string_table: StringTable) -> StringTable:
    return string_table


def discover_avaya_45xx_temp(section: StringTable) -> DiscoveryResult:
    for idx, _line in enumerate(section):
        yield Service(item=str(idx))


def check_avaya_45xx_temp(item: str, params: TempParamType, section: StringTable) -> CheckResult:
    for idx, temp in enumerate(section):
        if str(idx) == item:
            yield from check_temperature(
                float(temp[0]) / 2.0,
                params,
                unique_name=f"avaya_45xx_temp_{item}",
                value_store=get_value_store(),
            )
            return


snmp_section_avaya_45xx_temp = SimpleSNMPSection(
    name="avaya_45xx_temp",
    detect=contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.45.3"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.45.1.6.3.7.1.1.5",
        oids=["5"],
    ),
    parse_function=parse_avaya_45xx_temp,
)


check_plugin_avaya_45xx_temp = CheckPlugin(
    name="avaya_45xx_temp",
    service_name="Temperature Chassis %s",
    discovery_function=discover_avaya_45xx_temp,
    check_function=check_avaya_45xx_temp,
    check_ruleset_name="temperature",
    # S5-CHASSIS-MIB::s5ChasTmpSnrTmpValue
    # The current temperature value of the temperature
    # sensor. This is measured in units of a half degree
    # centigrade, e.g. a value of 121 indicates a temperature
    # of 60.5 degrees C.,
    check_default_parameters={
        "levels": (55.0, 60.0),
    },
)
