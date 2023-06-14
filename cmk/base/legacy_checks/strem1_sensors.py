#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Author: Lars Michelsen <lm@mathias-kettner.de>, 2011-03-21


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import contains, SNMPTree

strem1_temp_defaultlevels = (28, 32)


def strem1_sensors_parse_info(info):
    # Change format of output: 1 tuple for each group
    parsed = []
    for group in zip(*info):
        grp = group[0]

        items = group[1:]
        for i in range(0, len(items), 3):
            parsed.append([grp + " " + items[i]] + list(items[i : i + 3]))
    return parsed


def inventory_strem1_sensors(info):
    inventory = []
    for index, typ, val, _intval in strem1_sensors_parse_info(info[1]):
        lvls: tuple[int, int] | tuple[None, None] = strem1_temp_defaultlevels
        if typ in {"Humidity", "Wetness"}:
            lvls = (None, None)
        if val != "-999.9":
            inventory.append((index, lvls))
    return inventory


def check_strem1_sensors(item, params, info):
    for index, typ, val, _intval in strem1_sensors_parse_info(info[1]):
        if index == item:
            uom = info[0][0][0] if typ == "Temperature" else "%"
            val = float(val)
            warn, crit = params

            infotext = "%.1f" % val + uom
            perfdata = [(typ.lower(), infotext, warn, crit)]
            thrtext = []
            if warn:
                thrtext += ["warn at %.1f" % warn + uom]
            if crit:
                thrtext += ["crit at %.1f" % crit + uom]
            if thrtext:
                infotext += " (%s)" % ", ".join(thrtext)

            if crit and val >= crit:
                return (2, "%s is: " % typ + infotext, perfdata)
            if warn and val >= warn:
                return (1, "%s is: " % typ + infotext, perfdata)
            return (0, "%s is: " % typ + infotext, perfdata)
    return (3, "Sensor not found")


check_info["strem1_sensors"] = LegacyCheckDefinition(
    detect=contains(".1.3.6.1.2.1.1.1.0", "Sensatronics EM1"),
    check_function=check_strem1_sensors,
    discovery_function=inventory_strem1_sensors,
    service_name="Sensor - %s",
    # 1,  # SENSATRONICS-EM1::group1Name
    # 2,  # SENSATRONICS-EM1::group1TempName
    # 3,  # SENSATRONICS-EM1::group1TempDataStr
    # 4,  # SENSATRONICS-EM1::group1TempDataInt
    # 5,  # SENSATRONICS-EM1::group1HumidName
    # 6,  # group1HumidDataStr
    # 7,  # group1HumidDataInt
    # 8,  # group1WetName
    # 9,  # group1WetDataStr
    # 10, # group1WetDataInt
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.16174.1.1.3.2.3",
            oids=["1"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.16174.1.1.3.3",
            oids=["1", "2", "3", "4"],
        ),
    ],
)
