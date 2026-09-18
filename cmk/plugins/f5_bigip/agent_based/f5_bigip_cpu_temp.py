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
from cmk.plugins.f5_bigip.lib import F5_BIGIP
from cmk.plugins.lib.temperature import check_temperature, TempParamDict

Section = Mapping[str, int]


def parse_f5_bigip_cpu_temp(string_table: StringTable) -> Section:
    return {name: int(temp) for name, temp in string_table}


def discover_f5_bigip_cpu_temp(section: Section) -> DiscoveryResult:
    yield from (Service(item=name) for name in section)


def check_f5_bigip_cpu_temp(item: str, params: TempParamDict, section: Section) -> CheckResult:
    if (temp := section.get(item)) is None:
        return

    yield from check_temperature(
        temp,
        params,
        unique_name=f"f5_bigip_cpu_temp_{item}",
        value_store=get_value_store(),
    )


snmp_section_f5_bigip_cpu_temp = SimpleSNMPSection(
    name="f5_bigip_cpu_temp",
    detect=F5_BIGIP,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3375.2.1.3.6.2.1",
        oids=[
            "4",  # F5-BIGIP-SYSTEM-MIB::sysCpuSensorName
            "2",  # F5-BIGIP-SYSTEM-MIB::sysCpuSensorTemperature
        ],
    ),
    parse_function=parse_f5_bigip_cpu_temp,
)


check_plugin_f5_bigip_cpu_temp = CheckPlugin(
    name="f5_bigip_cpu_temp",
    service_name="Temperature CPU %s",
    discovery_function=discover_f5_bigip_cpu_temp,
    check_function=check_f5_bigip_cpu_temp,
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (60.0, 80.0)},
)
