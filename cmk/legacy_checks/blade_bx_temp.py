#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Metric,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.blade.agent_based.detection import DETECT_BLADE_BX
from cmk.plugins.lib.temperature import check_temperature, TempParamType

_BLADE_BX_STATUS = {
    1: "unknown",
    2: "sensor-disabled",
    3: "ok",
    4: "sensor-failed",
    5: "warning-temp",
    6: "critical-temp",
    7: "not-available",
}


def saveint(i: str) -> int:
    """Tries to cast a string to an integer and return it. In case this
    fails, it returns 0.

    Advice: Please don't use this function in new code. It is understood as
    bad style these days, because in case you get 0 back from this function,
    you can not know whether it is really 0 or something went wrong."""
    try:
        return int(i)
    except (TypeError, ValueError):
        return 0


def parse_blade_bx_temp(string_table: StringTable) -> StringTable:
    return string_table


def discover_blade_bx_temp(section: StringTable) -> DiscoveryResult:
    for line in section:
        if int(line[1]) != 7:
            yield Service(item=line[2])


def check_blade_bx_temp(item: str, params: TempParamType, section: StringTable) -> CheckResult:
    for _index, status_str, descr, level_warn_str, level_crit_str, temp_str, crit_react in section:
        if descr != item:
            continue

        status = saveint(status_str)
        level_warn = saveint(level_warn_str)
        level_crit = saveint(level_crit_str)
        temp = saveint(temp_str)

        if crit_react != "2":
            yield Result(state=State.CRIT, summary="Temperature not present or poweroff")
            yield Metric("temp", float(temp))
            return
        if status != 3:
            yield Result(
                state=State.CRIT,
                summary=f"Status is {_BLADE_BX_STATUS.get(status, 'unknown')}",
            )
            yield Metric("temp", float(temp))
            return

        yield from check_temperature(
            float(temp),
            params,
            unique_name=f"blade_bx_temp_{item}",
            value_store=get_value_store(),
            dev_levels=(float(level_warn), float(level_crit)),
        )
        return

    yield Result(state=State.UNKNOWN, summary=f"Device {item} not found in SNMP data")


snmp_section_blade_bx_temp = SimpleSNMPSection(
    name="blade_bx_temp",
    detect=DETECT_BLADE_BX,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.7244.1.1.1.3.4.1.1",
        oids=["1", "2", "3", "4", "5", "6", "7"],
    ),
    parse_function=parse_blade_bx_temp,
)


check_plugin_blade_bx_temp = CheckPlugin(
    name="blade_bx_temp",
    service_name="Temperature Blade %s",
    discovery_function=discover_blade_bx_temp,
    check_function=check_blade_bx_temp,
    check_ruleset_name="temperature",
    check_default_parameters={},
)
