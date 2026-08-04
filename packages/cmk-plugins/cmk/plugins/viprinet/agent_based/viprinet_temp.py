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
from cmk.plugins.lib.temperature import check_temperature, TempParamType
from cmk.plugins.viprinet.lib import DETECT_VIPRINET


def parse_viprinet_temp(string_table: StringTable) -> StringTable:
    return string_table


def discover_viprinet_temp(section: StringTable) -> DiscoveryResult:
    if section:
        yield Service(item="CPU")
        yield Service(item="System")


def check_viprinet_temp(item: str, params: TempParamType, section: StringTable) -> CheckResult:
    reading = int(section[0][item == "System"])
    yield from check_temperature(
        reading=reading,
        params=params,
        unique_name=f"viprinet_temp_{item}",
        value_store=get_value_store(),
    )


snmp_section_viprinet_temp = SimpleSNMPSection(
    name="viprinet_temp",
    detect=DETECT_VIPRINET,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.35424.1.2",
        oids=["3", "4"],
    ),
    parse_function=parse_viprinet_temp,
)


check_plugin_viprinet_temp = CheckPlugin(
    name="viprinet_temp",
    service_name="Temperature %s",
    discovery_function=discover_viprinet_temp,
    check_function=check_viprinet_temp,
    check_ruleset_name="temperature",
    check_default_parameters={},
)
