#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_legacy_includes.temperature import check_temperature

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.datapower import DETECT

check_info = {}


def inventory_datapower_temp(info):
    for name, _temp, _upper_warn, _status, _upper_crit in info:
        yield name.strip("Temperature "), {}


def _create_dev_levels(warn: str, crit: str) -> tuple[float, float] | None:
    try:
        return (float(warn), float(crit))
    except ValueError:
        return None


def check_datapower_temp(item, params, info):
    datapower_temp_status = {
        "8": (2, "failure"),
        "9": (3, "noReading"),
        "10": (2, "invalid"),
    }
    for name, temp, upper_warn, status, upper_crit in info:
        if item == name.strip("Temperature "):
            if int(status) >= 8:
                dev_state, dev_state_txt = datapower_temp_status[status]
                return dev_state, "device status: %s" % dev_state_txt

            state, infotext, perfdata = check_temperature(
                float(temp),
                params,
                "datapower_temp_%s" % item,
                dev_levels=_create_dev_levels(upper_warn, upper_crit),
            )

            return state, infotext, perfdata
    return None


def parse_datapower_temp(string_table: StringTable) -> StringTable:
    return string_table


check_info["datapower_temp"] = LegacyCheckDefinition(
    name="datapower_temp",
    parse_function=parse_datapower_temp,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.14685.3.1.141.1",
        oids=["1", "2", "3", "5", "6"],
    ),
    service_name="Temperature %s",
    discovery_function=inventory_datapower_temp,
    check_function=check_datapower_temp,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (65.0, 70.0),  # 70C recommended alarm level by IBM
    },
)
