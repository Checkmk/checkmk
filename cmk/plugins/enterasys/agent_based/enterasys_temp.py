#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


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
from cmk.plugins.enterasys.lib import DETECT_ENTERASYS
from cmk.plugins.lib.temperature import check_temperature, TempParamType


def parse_enterasys_temp(string_table: StringTable) -> StringTable:
    return string_table


def discover_enterasys_temp(section: StringTable) -> DiscoveryResult:
    if section and section[0][0] != "0":
        yield Service(item="Ambient")


def check_enterasys_temp(item: str, params: TempParamType, section: StringTable) -> CheckResult:
    # info for MIB: The ambient temperature of the room in which the chassis
    # is located. If this sensor is broken or not supported, then
    # this object will be set to zero. The value of this object
    # is the actual temperature in degrees Fahrenheit * 10.
    if section[0][0] == "0":
        yield Result(state=State.UNKNOWN, summary="Sensor broken or not supported")
        return

    yield from check_temperature(
        int(section[0][0]) / 10.0,
        params,
        unique_name=f"enterasys_temp_{item}",
        value_store=get_value_store(),
        dev_unit="f",
    )


snmp_section_enterasys_temp = SimpleSNMPSection(
    name="enterasys_temp",
    detect=DETECT_ENTERASYS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.52.4.1.1.8.1",
        oids=["1"],
    ),
    parse_function=parse_enterasys_temp,
)


check_plugin_enterasys_temp = CheckPlugin(
    name="enterasys_temp",
    service_name="Temperature %s",
    discovery_function=discover_enterasys_temp,
    check_function=check_enterasys_temp,
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (30.0, 35.0)},
)
