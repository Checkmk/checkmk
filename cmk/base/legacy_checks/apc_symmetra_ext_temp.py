#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.apc import DETECT


def inventory_apc_symmetra_ext_temp(info):
    for index, status, _temp, _temp_unit in info:
        if status == "2":
            yield index, {}


def check_apc_symmetra_ext_temp(item, params, info):
    for index, _status, temp, temp_unit in info:
        if item == index:
            unit = "f" if temp_unit == "2" else "c"
            return check_temperature(
                int(temp), params, "apc_symmetra_ext_temp_%s" % item, dev_unit=unit
            )

    return 3, "Sensor not found in SNMP data"


check_info["apc_symmetra_ext_temp"] = LegacyCheckDefinition(
    detect=DETECT,
    check_function=check_apc_symmetra_ext_temp,
    discovery_function=inventory_apc_symmetra_ext_temp,
    service_name="Temperature External %s",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.318.1.1.10.2.3.2.1",
        oids=["1", "3", "4", "5"],
    ),
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (30.0, 35.0)},
)
