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
from cmk.plugins.emc.lib import DETECT_ISILON
from cmk.plugins.lib.temperature import check_temperature, TempParamType


# Expected sensor names:
# "Temp Until CPU Throttle (CPU 0)"
# "Temp Until CPU Throttle (CPU 1)"
# "Temp Chassis 1 (ISI T1)"
# "Temp Front Panel"
# "Temp Power Supply 1"
# "Temp Power Supply 2"
# "Temp System"
def _isilon_temp_item_name(sensor_name: str) -> str:
    if "CPU Throttle" in sensor_name:
        return sensor_name.split("(")[1].split(")", maxsplit=1)[0]  # "CPU 1"
    return sensor_name[5:]  # "Front Panel"


def parse_emc_isilon_temp(string_table: StringTable) -> StringTable:
    return string_table


def _check_isilon_temp(item: str, params: TempParamType, section: StringTable) -> CheckResult:
    for sensor_name, value in section:
        if item == _isilon_temp_item_name(sensor_name):
            yield from check_temperature(
                float(value),
                params,
                unique_name=f"isilon_{item}",
                value_store=get_value_store(),
            )
            return


def _discover_isilon_temp(section: StringTable, is_cpu: bool) -> DiscoveryResult:
    for sensor_name, _value in section:
        item_name = _isilon_temp_item_name(sensor_name)
        if is_cpu == item_name.startswith("CPU"):
            yield Service(item=item_name)


def discover_emc_isilon_temp(section: StringTable) -> DiscoveryResult:
    yield from _discover_isilon_temp(section, is_cpu=False)


def discover_emc_isilon_temp_cpu(section: StringTable) -> DiscoveryResult:
    yield from _discover_isilon_temp(section, is_cpu=True)


snmp_section_emc_isilon_temp = SimpleSNMPSection(
    name="emc_isilon_temp",
    parse_function=parse_emc_isilon_temp,
    detect=DETECT_ISILON,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12124.2.54.1",
        oids=["3", "4"],
    ),
)


check_plugin_emc_isilon_temp = CheckPlugin(
    name="emc_isilon_temp",
    service_name="Temperature %s",
    discovery_function=discover_emc_isilon_temp,
    check_function=_check_isilon_temp,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (28.0, 33.0),  # assumed useful levels for ambient / air temperature
    },
)


check_plugin_emc_isilon_temp_cpu = CheckPlugin(
    name="emc_isilon_temp_cpu",
    service_name="Temperature %s",
    sections=["emc_isilon_temp"],
    discovery_function=discover_emc_isilon_temp_cpu,
    check_function=_check_isilon_temp,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (75.0, 85.0),
    },
)
