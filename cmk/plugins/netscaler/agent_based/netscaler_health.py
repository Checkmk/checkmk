#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import re
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.fan import check_fan
from cmk.plugins.lib.temperature import check_temperature, TempParamType
from cmk.plugins.netscaler.agent_based.lib import SNMP_DETECT

#
# Based on contribution by Karsten Schöke <karsten.schoeke@geobasis-bb.de>
#
# Example Output:
# .1.3.6.1.4.1.5951.4.1.1.41.7.1.1.12.1 "CPUFan0Speed"
# .1.3.6.1.4.1.5951.4.1.1.41.7.1.1.12.2 "CPUFan1Speed"
# .1.3.6.1.4.1.5951.4.1.1.41.7.1.1.14.2 "SystemFanSpeed"
# .1.3.6.1.4.1.5951.4.1.1.41.7.1.1.14.3 "CPU0Temperature"
# .1.3.6.1.4.1.5951.4.1.1.41.7.1.1.14.4 "CPU1Temperature"
# .1.3.6.1.4.1.5951.4.1.1.41.7.1.1.19.3 "InternalTemperature"
# .1.3.6.1.4.1.5951.4.1.1.41.7.1.1.25.2 "PowerSupply1FailureStatus"
# .1.3.6.1.4.1.5951.4.1.1.41.7.1.1.25.7 "PowerSupply2FailureStatus"
# .1.3.6.1.4.1.5951.4.1.1.41.7.1.2.12.1 9975
# .1.3.6.1.4.1.5951.4.1.1.41.7.1.2.12.2 9750
# .1.3.6.1.4.1.5951.4.1.1.41.7.1.2.14.2 9825
# .1.3.6.1.4.1.5951.4.1.1.41.7.1.2.14.3 60
# .1.3.6.1.4.1.5951.4.1.1.41.7.1.2.14.4 72
# .1.3.6.1.4.1.5951.4.1.1.41.7.1.2.19.3 32
# .1.3.6.1.4.1.5951.4.1.1.41.7.1.2.25.2 0
# .1.3.6.1.4.1.5951.4.1.1.41.7.1.2.25.7 9900


def parse_netscaler_health(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_netscaler_health = SimpleSNMPSection(
    name="netscaler_health",
    detect=SNMP_DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.5951.4.1.1.41.7.1",
        oids=["1", "2"],
    ),
    parse_function=parse_netscaler_health,
)

# .
#   .--fan-----------------------------------------------------------------.
#   |                            __                                        |
#   |                           / _| __ _ _ __                             |
#   |                          | |_ / _` | '_ \                            |
#   |                          |  _| (_| | | | |                           |
#   |                          |_|  \__,_|_| |_|                           |
#   |                                                                      |
#   +----------------------------------------------------------------------+


def discover_netscaler_health_fan(section: StringTable) -> DiscoveryResult:
    for name, value in section:
        if name.endswith("Speed") and value != "0":
            yield Service(item=name[:-5])


def check_netscaler_health_fan(
    item: str, params: Mapping[str, Any], section: StringTable
) -> CheckResult:
    for name, value in section:
        if name[:-5] == item:
            yield from check_fan(int(value), params)
            return


check_plugin_netscaler_health_fan = CheckPlugin(
    name="netscaler_health_fan",
    service_name="FAN %s",
    sections=["netscaler_health"],
    discovery_function=discover_netscaler_health_fan,
    check_function=check_netscaler_health_fan,
    check_ruleset_name="hw_fans",
    check_default_parameters={
        "lower": (3500, 3000),
    },
)
# .
#   .--temp----------------------------------------------------------------.
#   |                       _                                              |
#   |                      | |_ ___ _ __ ___  _ __                         |
#   |                      | __/ _ \ '_ ` _ \| '_ \                        |
#   |                      | ||  __/ | | | | | |_) |                       |
#   |                       \__\___|_| |_| |_| .__/                        |
#   |                                        |_|                           |
#   +----------------------------------------------------------------------+


def discover_netscaler_health_temp(section: StringTable) -> DiscoveryResult:
    for name, value in section:
        if name.endswith("Temperature") and value != "0":
            yield Service(item=name[:-11])


def check_netscaler_health_temp(
    item: str, params: TempParamType, section: StringTable
) -> CheckResult:
    for name, value in section:
        if name[:-11] == item and name.endswith("Temperature"):
            yield from check_temperature(
                reading=int(value),
                params=params,
                unique_name=f"netscaler_health_{item}",
                value_store=get_value_store(),
            )
            return


check_plugin_netscaler_health_temp = CheckPlugin(
    name="netscaler_health_temp",
    service_name="Temperature %s",
    sections=["netscaler_health"],
    discovery_function=discover_netscaler_health_temp,
    check_function=check_netscaler_health_temp,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (80.0, 90.0),
    },
)

# .
#   .--psu-----------------------------------------------------------------.
#   |                                                                      |
#   |                           _ __  ___ _   _                            |
#   |                          | '_ \/ __| | | |                           |
#   |                          | |_) \__ \ |_| |                           |
#   |                          | .__/|___/\__,_|                           |
#   |                          |_|                                         |
#   +----------------------------------------------------------------------+

PSU_STATE_PATTERN = re.compile(r"PowerSupply([\d])(Failure|)Status")


def discover_netscaler_health_psu(section: StringTable) -> DiscoveryResult:
    for name, state in section:
        m = PSU_STATE_PATTERN.match(name)
        if m and int(state) > 0:
            yield Service(item=m.group(1))


def check_netscaler_health_psu(item: str, section: StringTable) -> CheckResult:
    psu_status_map = (
        (State.UNKNOWN, "not supported"),  # 0
        (State.CRIT, "not present"),  # 1
        (State.CRIT, "failed"),  # 2
        (State.OK, "normal"),  # 3
    )

    for name, state in section:
        if name.startswith("PowerSupply" + item) and name.endswith(("Status", "FailureStatus")):
            psu_state, psu_text = psu_status_map[int(state)]
            yield Result(state=psu_state, summary=psu_text)
            return


check_plugin_netscaler_health_psu = CheckPlugin(
    name="netscaler_health_psu",
    service_name="Power Supply %s",
    sections=["netscaler_health"],
    discovery_function=discover_netscaler_health_psu,
    check_function=check_netscaler_health_psu,
)
