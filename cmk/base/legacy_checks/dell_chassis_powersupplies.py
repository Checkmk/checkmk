#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import re

from cmk.base.check_api import LegacyCheckDefinition, savefloat
from cmk.base.config import check_info

from cmk.agent_based.v2 import OIDEnd, SNMPTree, StringTable
from cmk.plugins.lib.dell import DETECT_CHASSIS


def inventory_dell_chassis_powersupplies(info):
    inventory = []
    for line in info:
        item = re.sub(r"\.", "-", line[0])
        inventory.append((item, None))
    return inventory


def check_dell_chassis_powersupplies(item, _no_params, info):
    for oid_end, voltage, current, maxpower in info:
        if item == re.sub(r"\.", "-", oid_end):
            power = savefloat(voltage) * savefloat(current)
            state = 0
            infotext = ""
            infotext += "current/max Power: {:.2f} / {}, Current: {}, Voltage: {}".format(
                power,
                maxpower,
                current,
                voltage,
            )
            perfdata = [("power", str(power) + "Watt", 0, maxpower, "", maxpower)]

            if savefloat(current) == 0:
                infotext = infotext + " - device in standby"

            return state, infotext, perfdata

    return 3, "unknown power supply"


def parse_dell_chassis_powersupplies(string_table: StringTable) -> StringTable:
    return string_table


check_info["dell_chassis_powersupplies"] = LegacyCheckDefinition(
    parse_function=parse_dell_chassis_powersupplies,
    detect=DETECT_CHASSIS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.674.10892.2.4.2.1",
        oids=[OIDEnd(), "5", "6", "7"],
    ),
    service_name="Power Supply %s",
    discovery_function=inventory_dell_chassis_powersupplies,
    check_function=check_dell_chassis_powersupplies,
)
