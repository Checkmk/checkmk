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
from cmk.plugins.fireeye.lib import DETECT, HEALTH_MAP, STATUS_MAP
from cmk.plugins.lib.temperature import check_temperature, TempParamType

# .1.3.6.1.4.1.25597.11.1.1.4.0 32 --> FE-FIREEYE-MIB::feTemperatureValue.0
# .1.3.6.1.4.1.25597.11.1.1.5.0 Good --> FE-FIREEYE-MIB::feTemperatureStatus.0
# .1.3.6.1.4.1.25597.11.1.1.6.0 1 --> FE-FIREEYE-MIB::feTemperatureIsHealthy.0


def discover_fireeye_temp(section: StringTable) -> DiscoveryResult:
    if section:
        yield Service(item="system")


def check_fireeye_temp(item: str, params: TempParamType, section: StringTable) -> CheckResult:
    reading_str, status, health = section[0]
    dev_status = 0
    dev_status_name = ""

    state, state_readable = STATUS_MAP.get(status.lower(), (2, f"unknown: {status}"))
    dev_status = max(dev_status, state)
    dev_status_name += f"Status: {state_readable}"

    state, state_readable = HEALTH_MAP.get(health, (2, f"unknown: {health}"))
    dev_status = max(dev_status, state)
    dev_status_name += f"Health: {state_readable}"

    yield from check_temperature(
        float(reading_str),
        params,
        unique_name="fireeye_temp_system",
        value_store=get_value_store(),
        dev_status=dev_status,
        dev_status_name=dev_status_name,
    )


def parse_fireeye_temp(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_fireeye_temp = SimpleSNMPSection(
    name="fireeye_temp",
    parse_function=parse_fireeye_temp,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.25597.11.1.1",
        oids=["4", "5", "6"],
    ),
)


check_plugin_fireeye_temp = CheckPlugin(
    name="fireeye_temp",
    service_name="Temperature %s",
    discovery_function=discover_fireeye_temp,
    check_function=check_fireeye_temp,
    check_ruleset_name="temperature",
    check_default_parameters={},
)
