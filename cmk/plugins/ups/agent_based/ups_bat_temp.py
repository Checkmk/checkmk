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
from cmk.plugins.lib.temperature import check_temperature, TempParamType
from cmk.plugins.ups.lib import DETECT_UPS_GENERIC


def format_item_ups_bat_temp(name: str, new_format: bool) -> str:
    if new_format:
        return "Battery %s" % name
    return name


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


def parse_ups_bat_temp(string_table: StringTable) -> StringTable:
    return string_table


def discover_ups_bat_temp(section: StringTable) -> DiscoveryResult:
    # 2nd condition is needed to catch some UPS devices which do not have
    # any temperature sensor but report a 0 as upsBatteryTemperature. Skip those lines
    if section and saveint(section[0][1]) != 0:
        yield from (Service(item=format_item_ups_bat_temp(line[0], True)) for line in section)


def check_ups_bat_temp(item: str, params: TempParamType, section: StringTable) -> CheckResult:
    for line in section:
        name = format_item_ups_bat_temp(line[0], "Battery" in item)
        if name == item:
            yield from check_temperature(
                int(line[1]),
                params,
                unique_name="ups_bat_temp_%s" % item,
                value_store=get_value_store(),
            )
            return


snmp_section_ups_bat_temp = SimpleSNMPSection(
    name="ups_bat_temp",
    detect=DETECT_UPS_GENERIC,
    fetch=SNMPTree(
        base=".1.3.6.1.2.1.33.1",
        oids=["1.5", "2.7"],
    ),
    parse_function=parse_ups_bat_temp,
)


check_plugin_ups_bat_temp = CheckPlugin(
    name="ups_bat_temp",
    service_name="Temperature %s",
    discovery_function=discover_ups_bat_temp,
    check_function=check_ups_bat_temp,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (40.0, 50.0),
    },
)
