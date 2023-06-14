#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.avaya import DETECT_AVAYA


def inventory_avaya_chassis_temp(info):
    if info:
        return [("Chassis", {})]
    return []


def check_avaya_chassis_temp(item, params, info):
    return check_temperature(int(info[0][0]), params, "avaya_chassis_temp_%s" % item)


check_info["avaya_chassis_temp"] = LegacyCheckDefinition(
    detect=DETECT_AVAYA,
    check_function=check_avaya_chassis_temp,
    discovery_function=inventory_avaya_chassis_temp,
    service_name="Temperature %s",
    check_ruleset_name="temperature",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2272.1.100.1",
        oids=["2"],
    ),
    check_default_parameters={
        "levels": (55.0, 60.0),
    },
)
