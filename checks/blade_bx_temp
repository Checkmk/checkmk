#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import saveint
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.blade import DETECT_BLADE_BX


def check_blade_bx_temp(item, params, info):
    blade_bx_status = {
        1: "unknown",
        2: "sensor-disabled",
        3: "ok",
        4: "sensor-faild",
        5: "warning-temp",
        6: "critical-temp",
        7: "not-available",
    }
    for _index, status, descr, level_warn, level_crit, temp, crit_react in info:
        status = saveint(status)
        level_crit = saveint(level_crit)
        level_warn = saveint(level_warn)
        temp = saveint(temp)
        if descr != item:
            # wrong item
            continue

        statuscode, message, perfdata = check_temperature(
            temp, params, "blade_bx_temp_%s" % item, dev_levels=(level_warn, level_crit)
        )

        if crit_react != "2":
            return (2, "Temperature not present or poweroff", perfdata)
        if status != 3:
            return (2, "Status is %s" % blade_bx_status.get(status, 1), perfdata)
        return statuscode, message, perfdata

    return (3, "Device %s not found in SNMP data" % item, [])


def inventory_blade_bx_temp(info):
    for line in info:
        if int(line[1]) != 7:
            yield line[2], None


check_info["blade_bx_temp"] = {
    "detect": DETECT_BLADE_BX,
    "check_function": check_blade_bx_temp,
    "discovery_function": inventory_blade_bx_temp,
    "service_name": "Temperature Blade %s",
    "fetch": SNMPTree(
        base=".1.3.6.1.4.1.7244.1.1.1.3.4.1.1",
        oids=["1", "2", "3", "4", "5", "6", "7"],
    ),
    "check_ruleset_name": "temperature",
}
