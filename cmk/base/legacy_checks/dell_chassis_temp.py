#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.base.config import check_info, factory_settings
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.dell import DETECT_CHASSIS

factory_settings["dell_chassis_temp_default_levels"] = {"levels": (60.0, 80.0)}


def inventory_dell_chassis_temp(info):
    if info and len(info[0]) == 3:
        yield "Front Panel", {}
        yield "CMC Ambient", {}
        yield "CMC Processor", {}


def check_dell_chassis_temp(item, params, info):
    items = {
        "Front Panel": 0,
        "CMC Ambient": 1,
        "CMC Processor": 2,
    }

    if item in items:
        item_id = items[item]

        temp = float(info[0][item_id])
        return check_temperature(temp, params, "dell_chassis_temp_%s" % item)

    return 3, "Sensor not found in SNMP data"


check_info["dell_chassis_temp"] = LegacyCheckDefinition(
    detect=DETECT_CHASSIS,
    check_function=check_dell_chassis_temp,
    discovery_function=inventory_dell_chassis_temp,
    service_name="Temperature %s",
    check_ruleset_name="temperature",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.674.10892.2.3.1",
        oids=["10", "11", "12"],
    ),
    default_levels_variable="dell_chassis_temp_default_levels",
    check_default_parameters={"levels": (60.0, 80.0)},
)
