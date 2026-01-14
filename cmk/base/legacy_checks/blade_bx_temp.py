#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.plugins.blade.agent_based.detection import DETECT_BLADE_BX

check_info = {}


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


def discover_blade_bx_temp(info):
    for line in info:
        if int(line[1]) != 7:
            yield line[2], None


def parse_blade_bx_temp(string_table: StringTable) -> StringTable:
    return string_table


check_info["blade_bx_temp"] = LegacyCheckDefinition(
    name="blade_bx_temp",
    parse_function=parse_blade_bx_temp,
    detect=DETECT_BLADE_BX,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.7244.1.1.1.3.4.1.1",
        oids=["1", "2", "3", "4", "5", "6", "7"],
    ),
    service_name="Temperature Blade %s",
    discovery_function=discover_blade_bx_temp,
    check_function=check_blade_bx_temp,
    check_ruleset_name="temperature",
)
