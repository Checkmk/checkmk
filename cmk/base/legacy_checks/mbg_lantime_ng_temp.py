#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.base.config import check_info, factory_settings
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.mbg_lantime import DETECT_MBG_LANTIME_NG

factory_settings["mbg_lantime_ng_temp_default_levels"] = {
    "levels": (80.0, 90.0),  # levels for system temperature
}


def inventory_mbg_lantime_ng_temp(info):
    if info:
        return [("System", {})]
    return []


def check_mbg_lantime_ng_temp(item, params, info):
    return check_temperature(float(info[0][0]), params, "mbg_lantime_ng_temp_%s" % item)


check_info["mbg_lantime_ng_temp"] = LegacyCheckDefinition(
    detect=DETECT_MBG_LANTIME_NG,
    check_function=check_mbg_lantime_ng_temp,
    discovery_function=inventory_mbg_lantime_ng_temp,
    service_name="Temperature %s",
    default_levels_variable="mbg_lantime_ng_temp_default_levels",
    check_ruleset_name="temperature",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.5597.30.0.5.2",
        oids=["1"],
    ),
    check_default_parameters={
        "levels": (80.0, 90.0),  # levels for system temperature
    },
)
