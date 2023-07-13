#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition, savefloat
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.dell import DETECT_CHASSIS


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

    infotext += "Power: %.1f W, PotentialPower: %.1f W, MaxPower: %.1f W, Current: %.1f A" % (
        savefloat(power),
        savefloat(PotentialPower),
        savefloat(MaxPowerSpec),
        savefloat(current),
    )

    perfdata = [("power", power + "Watt", 0, PotentialPower, "", MaxPowerSpec)]

    return state, infotext, perfdata


check_info["dell_chassis_power"] = LegacyCheckDefinition(
    detect=DETECT_CHASSIS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.674.10892.2",
        oids=["3.1.5.0", "4.1.1.2.1", "4.1.1.4.1", "4.1.1.13.1", "4.1.1.14.1"],
    ),
    service_name="Chassis Power",
    discovery_function=inventory_dell_chassis_power,
    check_function=check_dell_chassis_power,
)
