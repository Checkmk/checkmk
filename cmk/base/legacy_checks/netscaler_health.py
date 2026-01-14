#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"

import re

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.fan import check_fan
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.plugins.netscaler.agent_based.lib import SNMP_DETECT

check_info = {}

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


check_info["netscaler_health"] = LegacyCheckDefinition(
    name="netscaler_health",
    parse_function=parse_netscaler_health,
    detect=SNMP_DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.5951.4.1.1.41.7.1",
        oids=["1", "2"],
    ),
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


def discover_netscaler_health_fan(info):
    for name, value in info:
        if name.endswith("Speed") and value != "0":
            yield name[:-5], {}


def check_netscaler_health_fan(item, params, info):
    for name, value in info:
        if name[:-5] == item:
            return check_fan(int(value), params)
    return None


check_info["netscaler_health.fan"] = LegacyCheckDefinition(
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


def discover_netscaler_health_temp(info):
    for name, value in info:
        if name.endswith("Temperature") and value != "0":
            yield name[:-11], {}


def check_netscaler_health_temp(item, params, info):
    for name, value in info:
        if name[:-11] == item and name.endswith("Temperature"):
            temp = int(value)
            return check_temperature(temp, params, "netscaler_health_%s" % item)
    return None


check_info["netscaler_health.temp"] = LegacyCheckDefinition(
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


def discover_netscaler_health_psu(info):
    for name, state in info:
        m = PSU_STATE_PATTERN.match(name)
        if m:
            if int(state) > 0:
                yield m.group(1), None


def check_netscaler_health_psu(item, _no_params, info):
    psu_status_map = (
        (3, "not supported"),  # 0
        (2, "not present"),  # 1
        (2, "failed"),  # 2
        (0, "normal"),  # 3
    )

    for name, state in info:
        if name.startswith("PowerSupply" + item) and (
            name.endswith("Status") or name.endswith("FailureStatus")
        ):
            return psu_status_map[int(state)]
    return None


check_info["netscaler_health.psu"] = LegacyCheckDefinition(
    name="netscaler_health_psu",
    service_name="Power Supply %s",
    sections=["netscaler_health"],
    discovery_function=discover_netscaler_health_psu,
    check_function=check_netscaler_health_psu,
)
