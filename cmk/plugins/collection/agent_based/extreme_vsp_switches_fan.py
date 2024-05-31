#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.fan import check_fan
from cmk.plugins.lib.netextreme import DETECT_NETEXTREME


@dataclass
class VSPSwitchFanInfo:
    description: str
    operational_status: str
    operational_speed: str
    operational_speed_rpm: (
        float | None
    )  # there are cases where this is not present in the walk, because only newer devices have it


VSPSwitchesSection = Mapping[str, VSPSwitchFanInfo]

_MAP_FAN_STATUS = {
    "1": (State.UNKNOWN, "unknown - status can not be determined"),
    "2": (State.OK, "up - present and supplying power"),
    "3": (State.CRIT, "down - present, but failure indicated"),
}

_MAP_FAN_SPEED = {
    "1": "low",
    "2": "medium",
    "3": "high",
}


def parse_vsp_switches_fan(string_table: StringTable) -> VSPSwitchesSection:
    return {
        line[0]: VSPSwitchFanInfo(
            description=line[0],
            operational_status=line[1],
            operational_speed=_MAP_FAN_SPEED.get(line[2], "unknown"),
            operational_speed_rpm=float(line[3]) if line[3] else None,
        )
        for line in string_table
    }


snmp_section_extreme_vsp_switches_fan = SimpleSNMPSection(
    name="extreme_vsp_switches_fan",
    parse_function=parse_vsp_switches_fan,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2272.1.101.1.1.4.1",
        oids=[
            "3",  # rcVossSystemFanInfoDescription
            "4",  # rcVossSystemFanInfoOperStatus
            "5",  # rcVossSystemFanInfoOperSpeed
            "6",  # rcVossSystemFanInfoOperSpeedRpm
        ],
    ),
    detect=DETECT_NETEXTREME,
)


def discover_vsp_switches_fan(section: VSPSwitchesSection) -> DiscoveryResult:
    for vsp_switch in section:
        yield Service(item=vsp_switch)


def check_vsp_switches_fan(
    item: str,
    params: Mapping[str, Any],
    section: VSPSwitchesSection,
) -> CheckResult:
    if (vsp_switch := section.get(item)) is None:
        return

    state, state_readable = _MAP_FAN_STATUS.get(
        vsp_switch.operational_status,
        (State.UNKNOWN, f"Unknown fan status: {vsp_switch.operational_status}"),
    )
    yield Result(
        state=state,
        summary=f"Fan status: {state_readable}; Fan speed: {vsp_switch.operational_speed}",
    )
    if vsp_switch.operational_speed_rpm is not None:
        yield from check_fan(vsp_switch.operational_speed_rpm, params)


check_plugin_extreme_vsp_switches_fan = CheckPlugin(
    name="extreme_vsp_switches_fan",
    service_name="VSP Switch Fan %s",
    discovery_function=discover_vsp_switches_fan,
    check_function=check_vsp_switches_fan,
    check_default_parameters={"lower": (2000, 1000), "upper": (8000, 8400), "output_metrics": True},
    check_ruleset_name="hw_fans",
)
