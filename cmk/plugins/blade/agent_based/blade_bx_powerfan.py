#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)

from .detection import DETECT_BLADE_BX

_BLADE_BX_STATUS = {
    "1": "unknown",
    "2": "disabled",
    "3": "ok",
    "4": "fail",
    "5": "prefailure-predicted",
    "6": "redundant-fan-failed",
    "7": "not-manageable",
    "8": "not-present",
    "9": "not-available",
}

Params = Mapping[str, tuple[float, float]]


def parse_blade_bx_powerfan(string_table: StringTable) -> StringTable:
    return string_table


def discover_blade_bx_powerfan(section: StringTable) -> DiscoveryResult:
    for status, descr, _rpm, _max_speed, _speed, _ctrlstate in section:
        if status != "8":
            yield Service(item=descr)


def check_blade_bx_powerfan(item: str, params: Params, section: StringTable) -> CheckResult:
    for status, descr, rpm, max_speed, _speed, ctrlstate in section:
        if descr != item:
            continue

        speed_perc = float(rpm) * 100 / float(max_speed)

        if ctrlstate != "2":
            yield Result(state=State.CRIT, summary="Fan not present or poweroff")
            yield Metric("perc", speed_perc, boundaries=(0, 100))
            yield Metric("rpm", float(rpm))
            return

        if status != "3":
            yield Result(state=State.CRIT, summary=f"Status: {_BLADE_BX_STATUS[status]}")
            yield Metric("perc", speed_perc, boundaries=(0, 100))
            yield Metric("rpm", float(rpm))
            return

        yield from check_levels_v1(
            speed_perc,
            levels_lower=params["levels_lower"],
            levels_upper=params.get("levels"),
            metric_name="perc",
            render_func=lambda v: f"{v:.1f}%",
            label=f"Speed at {rpm} RPM",
            boundaries=(0, 100),
        )
        yield Metric("rpm", float(rpm))
        return


snmp_section_blade_bx_powerfan = SimpleSNMPSection(
    name="blade_bx_powerfan",
    detect=DETECT_BLADE_BX,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.7244.1.1.1.3.3.1.1",
        oids=["2", "3", "4", "5", "6", "7"],
    ),
    parse_function=parse_blade_bx_powerfan,
)


check_plugin_blade_bx_powerfan = CheckPlugin(
    name="blade_bx_powerfan",
    service_name="Blade Cooling %s",
    discovery_function=discover_blade_bx_powerfan,
    check_function=check_blade_bx_powerfan,
    check_ruleset_name="hw_fans_perc",
    check_default_parameters={
        "levels_lower": (20.0, 10.0),
        "levels": (80.0, 90.0),
    },
)
