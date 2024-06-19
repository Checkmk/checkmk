#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.dell import DETECT_CHASSIS


def savefloat(f: str) -> float:
    """Tries to cast a string to an float and return it. In case this fails,
    it returns 0.0.

    Advice: Please don't use this function in new code. It is understood as
    bad style these days, because in case you get 0.0 back from this function,
    you can not know whether it is really 0.0 or something went wrong."""
    try:
        return float(f)
    except (TypeError, ValueError):
        return 0.0


def inventory_dell_chassis_power(info):
    if info:
        return [(None, None)]
    return []


def check_dell_chassis_power(item, _no_params, info):
    status, PotentialPower, MaxPowerSpec, power, current = info[0]
    state_table = {
        "1": ("other, ", 1),
        "2": ("unknown, ", 1),
        "3": ("", 0),
        "4": ("nonCritical, ", 1),
        "5": ("Critical, ", 2),
        "6": ("NonRecoverable, ", 2),
    }
    infotext, state = state_table.get(status, ("unknown state, ", 3))

    infotext += (
        "Power: {:.1f} W, PotentialPower: {:.1f} W, MaxPower: {:.1f} W, Current: {:.1f} A".format(
            savefloat(power),
            savefloat(PotentialPower),
            savefloat(MaxPowerSpec),
            savefloat(current),
        )
    )

    perfdata = [("power", power + "Watt", 0, PotentialPower, "", MaxPowerSpec)]

    return state, infotext, perfdata


def parse_dell_chassis_power(string_table: StringTable) -> StringTable:
    return string_table


check_info["dell_chassis_power"] = LegacyCheckDefinition(
    parse_function=parse_dell_chassis_power,
    detect=DETECT_CHASSIS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.674.10892.2",
        oids=["3.1.5.0", "4.1.1.2.1", "4.1.1.4.1", "4.1.1.13.1", "4.1.1.14.1"],
    ),
    service_name="Chassis Power",
    discovery_function=inventory_dell_chassis_power,
    check_function=check_dell_chassis_power,
)
