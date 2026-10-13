#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    all_of,
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    equals,
    get_value_store,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.temperature import check_temperature, TempParamType

# .1.3.6.1.4.1.31560.3.1.1.1.48 33 --> ARTEC-MIB::hddTemperature

# suggested by customer


def parse_artec_temp(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_artec_temp = SimpleSNMPSection(
    name="artec_temp",
    parse_function=parse_artec_temp,
    detect=all_of(
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.8072.3.2.10"),
        contains(".1.3.6.1.2.1.1.1.0", "version"),
        contains(".1.3.6.1.2.1.1.1.0", "serial"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.31560.3.1.1.1",
        oids=["48"],
    ),
)


def discover_artec_temp(section: StringTable) -> DiscoveryResult:  # noqa: ARG001
    yield Service(item="Disk")


def check_artec_temp(item: str, params: TempParamType, section: StringTable) -> CheckResult:
    yield from check_temperature(
        reading=int(section[0][0]),
        params=params,
        unique_name=f"artec_{item}",
        value_store=get_value_store(),
    )


check_plugin_artec_temp = CheckPlugin(
    name="artec_temp",
    service_name="Temperature %s",
    discovery_function=discover_artec_temp,
    check_function=check_artec_temp,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (36.0, 40.0),
    },
)
