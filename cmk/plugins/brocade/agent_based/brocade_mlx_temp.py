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
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.brocade.lib import DETECT_MLX
from cmk.plugins.lib.temperature import check_temperature, TempParamType

Section = Mapping[str, float]


def parse_brocade_mlx_temp(string_table: StringTable) -> Section:
    parsed: dict[str, float] = {}
    for temp_descr, temp_value in string_table:
        if temp_value and temp_value != "0":
            item = (
                temp_descr.replace("temperature", "")
                .replace("module", "Module")
                .replace("sensor", "Sensor")
                .replace(",", "")
                .strip()
            )
            parsed[item] = float(temp_value) * 0.5
    return parsed


def discover_brocade_mlx_temp(section: Section) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def check_brocade_mlx_temp(item: str, params: TempParamType, section: Section) -> CheckResult:
    if item in section:
        yield from check_temperature(
            section[item],
            params,
            unique_name=f"brocade_mlx_temp_{item}",
            value_store=get_value_store(),
        )
        return
    if "Module" in item and "Sensor" not in item:
        # item discovered in 1.2.6 had the sensor-id stripped and module id replaced
        # so it's impossible to look by that name
        yield Result(
            state=State.UNKNOWN,
            summary="check had an incompatible change, please re-discover this host",
        )


snmp_section_brocade_mlx_temp = SimpleSNMPSection(
    name="brocade_mlx_temp",
    detect=DETECT_MLX,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1991.1.1.2.13.1.1",
        oids=["3", "4"],
    ),
    parse_function=parse_brocade_mlx_temp,
)


check_plugin_brocade_mlx_temp = CheckPlugin(
    name="brocade_mlx_temp",
    service_name="Temperature %s",
    discovery_function=discover_brocade_mlx_temp,
    check_function=check_brocade_mlx_temp,
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (105.0, 110.0)},
)
