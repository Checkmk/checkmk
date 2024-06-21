#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import NewType

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    OIDEnd,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
    StringTable,
)
from cmk.plugins.lib.temperature import check_temperature, TempParamDict

SensorId = NewType("SensorId", str)
TemperatureValue = NewType("TemperatureValue", float)

Section = Mapping[SensorId, TemperatureValue]


def parse(string_table: StringTable) -> Section:
    return {SensorId(entry[0]): TemperatureValue(float(entry[1])) for entry in string_table}


def discover(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check(item: SensorId, params: TempParamDict, section: Section) -> CheckResult:
    if (temperature := section.get(item)) is None:
        return

    yield from check_temperature(
        reading=temperature,
        params=params,
        unique_name=item,
        value_store=get_value_store(),
    )


snmp_section_cisco_ie_temp = SimpleSNMPSection(
    name="cisco_ie_temp",
    parse_function=parse,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9.9.832.1.24.1.3.6.1",  # cie1000SysutilStatusTemperatureMonitorEntry
        oids=[
            OIDEnd(),
            "5",  # cie1000SysutilStatusTemperatureMonitorTemperature
        ],
    ),
    detect=startswith(".1.3.6.1.2.1.1.1.0", "IE1000"),
)

check_plugin_cisco_ie_temp = CheckPlugin(
    name="cisco_ie_temp",
    service_name="Temperature %s",
    discovery_function=discover,
    check_default_parameters={},
    check_function=check,
    check_ruleset_name="temperature",
)
