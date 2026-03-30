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
from cmk.plugins.lib.temperature import check_temperature, TempParamType
from cmk.plugins.pulse_secure import lib as pulse_secure


def parse_pulse_secure_temp(string_table: StringTable) -> Mapping[str, int] | None:
    return pulse_secure.parse_pulse_secure(string_table, "IVE")


# no get_parsed_item_data because the temperature can be exactly 0 for some devices, which would
# result in "UNKN - Item not found in SNMP data", because parsed[item] evaluates to False
def check_pulse_secure_temp(
    item: str, params: TempParamType, section: Mapping[str, int]
) -> CheckResult:
    if not section:
        return

    yield from check_temperature(
        reading=float(section[item]),
        params=params,
        unique_name=f"pulse_secure_ive_temperature_{item}",
        value_store=get_value_store(),
    )


def discover_pulse_secure_temp(section: Mapping[str, int]) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


snmp_section_pulse_secure_temp = SimpleSNMPSection(
    name="pulse_secure_temp",
    detect=pulse_secure.DETECT_PULSE_SECURE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12532",
        oids=["42"],
    ),
    parse_function=parse_pulse_secure_temp,
)


check_plugin_pulse_secure_temp = CheckPlugin(
    name="pulse_secure_temp",
    service_name="Pulse Secure %s Temperature",
    discovery_function=discover_pulse_secure_temp,
    check_function=check_pulse_secure_temp,
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (70.0, 75.0)},
)
