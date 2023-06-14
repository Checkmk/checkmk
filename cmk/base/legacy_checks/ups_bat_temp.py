#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition, saveint
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.ups import DETECT_UPS_GENERIC


def format_item_ups_bat_temp(name, new_format):
    if new_format:
        return "Battery %s" % name
    return name


def inventory_ups_bat_temp(info):
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


check_info["ups_bat_temp"] = LegacyCheckDefinition(
    detect=DETECT_UPS_GENERIC,
    discovery_function=inventory_ups_bat_temp,
    check_function=check_ups_bat_temp,
    service_name="Temperature %s",
    check_ruleset_name="temperature",
    fetch=SNMPTree(
        base=".1.3.6.1.2.1.33.1",
        oids=["1.5", "2.7"],
    ),
    check_default_parameters={
        "levels": (40.0, 50.0),
    },
)
