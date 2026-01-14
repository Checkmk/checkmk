#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.plugins.ups.lib import DETECT_UPS_GENERIC

check_info = {}


def format_item_ups_bat_temp(name, new_format):
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


def discover_ups_bat_temp(info):
    # 2nd condition is needed to catch some UPS devices which do not have
    # any temperature sensor but report a 0 as upsBatteryTemperature. Skip those lines
    if len(info) > 0 and saveint(info[0][1]) != 0:
        return [(format_item_ups_bat_temp(line[0], True), {}) for line in info]
    return []


def check_ups_bat_temp(item, params, info):
    for line in info:
        name = format_item_ups_bat_temp(line[0], "Battery" in item)
        if name == item:
            status, infotext, perfdata = check_temperature(
                int(line[1]), params, "ups_bat_temp_%s" % item
            )
            perfdatanew = [perfdata[0] + (80,)]
            return status, infotext, perfdatanew
    return None


def parse_ups_bat_temp(string_table: StringTable) -> StringTable:
    return string_table


check_info["ups_bat_temp"] = LegacyCheckDefinition(
    name="ups_bat_temp",
    parse_function=parse_ups_bat_temp,
    detect=DETECT_UPS_GENERIC,
    fetch=SNMPTree(
        base=".1.3.6.1.2.1.33.1",
        oids=["1.5", "2.7"],
    ),
    service_name="Temperature %s",
    discovery_function=discover_ups_bat_temp,
    check_function=check_ups_bat_temp,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (40.0, 50.0),
    },
)
