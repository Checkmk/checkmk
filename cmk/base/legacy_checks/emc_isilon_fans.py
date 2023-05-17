#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.fan import check_fan
from cmk.base.config import check_info, factory_settings
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.emc import DETECT_ISILON

factory_settings["emc_isilon_fan_default_levels"] = {"lower": (3000, 2500)}


# Examples for sensor names:
# Chassis Fan1 (ISI F1) --> Chassis 1
# Chassis Fan2 (ISI F2)
# Chassis Fan3 (ISI F3)
# Power Supply 1 Fan1 --> Power Supply 1 1
# Power Supply 2 Fan1
def isilon_fan_item_name(sensor_name):
    return sensor_name.replace("Fan", "").split("(")[0].strip()


def inventory_emc_isilon_fans(info):
    for fan_name, _value in info:
        yield isilon_fan_item_name(fan_name), {}


def check_emc_isilon_fans(item, params, info):
    for fan_name, value in info:
        if item == isilon_fan_item_name(fan_name):
            return check_fan(float(value), params)
    return None


check_info["emc_isilon_fans"] = LegacyCheckDefinition(
    detect=DETECT_ISILON,
    check_function=check_emc_isilon_fans,
    discovery_function=inventory_emc_isilon_fans,
    service_name="Fan %s",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12124.2.53.1",
        oids=["3", "4"],
    ),
    check_ruleset_name="hw_fans",
    default_levels_variable="emc_isilon_fan_default_levels",
    check_default_parameters={"lower": (3000, 2500)},
)
