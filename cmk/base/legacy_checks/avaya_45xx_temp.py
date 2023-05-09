#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import contains
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.base.config import check_info, factory_settings
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree

factory_settings["avaya_45xx_temp_default_levels"] = {
    "levels": (55.0, 60.0),
}


def inventory_avaya_45xx_temp(info):
    for idx, _line in enumerate(info):
        yield str(idx), {}


def check_avaya_45xx_temp(item, params, info):
    for idx, temp in enumerate(info):
        if str(idx) == item:
            return check_temperature(float(temp[0]) / 2.0, params, "avaya_45xx_temp_%s" % item)
    return None


check_info["avaya_45xx_temp"] = {
    "detect": contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.45.3"),
    "check_function": check_avaya_45xx_temp,
    "discovery_function": inventory_avaya_45xx_temp,
    "service_name": "Temperature Chassis %s",
    "default_levels_variable": "avaya_45xx_temp_default_levels",
    "check_ruleset_name": "temperature",
    # S5-CHASSIS-MIB::s5ChasTmpSnrTmpValue
    # The current temperature value of the temperature
    # sensor. This is measured in units of a half degree
    # centigrade, e.g. a value of 121 indicates a temperature
    # of 60.5 degrees C.
    "fetch": SNMPTree(
        base=".1.3.6.1.4.1.45.1.6.3.7.1.1.5",
        oids=["5"],
    ),
}
