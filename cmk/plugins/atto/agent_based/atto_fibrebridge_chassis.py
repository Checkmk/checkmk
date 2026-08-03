#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

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
    startswith,
    State,
    StringTable,
)
from cmk.plugins.lib.temperature import check_temperature, TempParamType

Section = dict[str, Any]


def parse_atto_fibrebridge_chassis(string_table: StringTable) -> Section | None:
    if not string_table:
        return None

    parsed: dict[str, Any] = {}

    min_operating_temp = int(string_table[0][0])
    max_operating_temp = int(string_table[0][1])
    chassis_temp = int(string_table[0][2])

    parsed["temperature"] = {
        "dev_levels": (max_operating_temp, max_operating_temp),
        "dev_levels_lower": (min_operating_temp, min_operating_temp),
        "reading": chassis_temp,
    }

    parsed["throughput_status"] = string_table[0][3]

    return parsed


snmp_section_atto_fibrebridge_chassis = SimpleSNMPSection(
    name="atto_fibrebridge_chassis",
    parse_function=parse_atto_fibrebridge_chassis,
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.4547"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.4547.2.3.2",
        oids=["4", "5", "8", "11"],
    ),
)


# .
#   .--Temperature---------------------------------------------------------.
#   |     _____                                   _                        |
#   |    |_   _|__ _ __ ___  _ __   ___ _ __ __ _| |_ _   _ _ __ ___       |
#   |      | |/ _ \ '_ ` _ \| '_ \ / _ \ '__/ _` | __| | | | '__/ _ \      |
#   |      | |  __/ | | | | | |_) |  __/ | | (_| | |_| |_| | | |  __/      |
#   |      |_|\___|_| |_| |_| .__/ \___|_|  \__,_|\__|\__,_|_|  \___|      |
#   |                       |_|                                            |
#   '----------------------------------------------------------------------'


def discover_atto_fibrebridge_chassis_temp(section: Section) -> DiscoveryResult:
    yield Service(item="Chassis")


def check_atto_fibrebridge_chassis_temp(
    item: str, params: TempParamType, section: Section
) -> CheckResult:
    yield from check_temperature(
        params=params,
        unique_name="atto_fibrebridge_chassis_temp",
        value_store=get_value_store(),
        **section["temperature"],
    )


check_plugin_atto_fibrebridge_chassis_temp = CheckPlugin(
    name="atto_fibrebridge_chassis_temp",
    service_name="Temperature %s",
    sections=["atto_fibrebridge_chassis"],
    discovery_function=discover_atto_fibrebridge_chassis_temp,
    check_function=check_atto_fibrebridge_chassis_temp,
    check_ruleset_name="temperature",
    check_default_parameters={},
)

# .
#   .--Throughput Status - Main Check--------------------------------------.
#   |       _____ _                           _                 _          |
#   |      |_   _| |__  _ __ ___  _   _  __ _| |__  _ __  _   _| |_        |
#   |        | | | '_ \| '__/ _ \| | | |/ _` | '_ \| '_ \| | | | __|       |
#   |        | | | | | | | | (_) | |_| | (_| | | | | |_) | |_| | |_        |
#   |        |_| |_| |_|_|  \___/ \__,_|\__, |_| |_| .__/ \__,_|\__|       |
#   |                                   |___/      |_|                     |
#   '----------------------------------------------------------------------'


def discover_atto_fibrebridge_chassis(section: Section) -> DiscoveryResult:
    yield Service()


def check_atto_fibrebridge_chassis(section: Section) -> CheckResult:
    throughput_status = section["throughput_status"]
    if throughput_status == "1":
        yield Result(state=State.OK, summary="Normal")
    elif throughput_status == "2":
        yield Result(state=State.WARN, summary="Warning")


check_plugin_atto_fibrebridge_chassis = CheckPlugin(
    name="atto_fibrebridge_chassis",
    service_name="Throughput Status",
    discovery_function=discover_atto_fibrebridge_chassis,
    check_function=check_atto_fibrebridge_chassis,
)
