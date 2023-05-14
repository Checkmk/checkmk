#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.f5_bigip import DETECT
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree

f5_bigip_chassis_temp_default_params = (35, 40)


def inventory_f5_bigip_chassis_temp(info):
    for line in info:
        yield line[0], f5_bigip_chassis_temp_default_params


def check_f5_bigip_chassis_temp(item, params, info):
    for name, temp in info:
        if name == item:
            return check_temperature(int(temp), params, "f5_bigip_chassis_temp_%s" % item)
    return None


check_info["f5_bigip_chassis_temp"] = LegacyCheckDefinition(
    detect=DETECT,
    check_function=check_f5_bigip_chassis_temp,
    discovery_function=inventory_f5_bigip_chassis_temp,
    service_name="Temperature Chassis %s",
    check_ruleset_name="temperature",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3375.2.1.3.2.3.2.1",
        oids=["1", "2"],
    ),
)
