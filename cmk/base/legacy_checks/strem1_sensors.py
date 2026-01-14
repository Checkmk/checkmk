#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"

# Author: Lars Michelsen <lm@mathias-kettner.de>, 2011-03-21


from collections.abc import Sequence

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import contains, SNMPTree, StringTable

check_info = {}


def strem1_sensors_parse_info(info):
    # Change format of output: 1 tuple for each group
    parsed = []
    for group in zip(*info):
        grp = group[0]

        items = group[1:]
        for i in range(0, len(items), 3):
            parsed.append([grp + " " + items[i]] + list(items[i : i + 3]))
    return parsed


def discover_strem1_sensors(info):
    return [
        (index, {})
        for index, _typ, val, _intval in strem1_sensors_parse_info(info[1])
        if val != "-999.9"
    ]


def check_strem1_sensors(item, _no_params, info):
    for index, typ, val, _intval in strem1_sensors_parse_info(info[1]):
        if index == item:
            uom = info[0][0][0] if typ == "Temperature" else "%"
            val = float(val)
            (warn, crit) = (None, None) if typ in {"Humidity", "Wetness"} else (28, 32)

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


def parse_strem1_sensors(string_table: Sequence[StringTable]) -> Sequence[StringTable]:
    return string_table


check_info["strem1_sensors"] = LegacyCheckDefinition(
    name="strem1_sensors",
    parse_function=parse_strem1_sensors,
    detect=contains(".1.3.6.1.2.1.1.1.0", "Sensatronics EM1"),
    fetch=[
        # 1,  # SENSATRONICS-EM1::group1Name
        # 2,  # SENSATRONICS-EM1::group1TempName
        # 3,  # SENSATRONICS-EM1::group1TempDataStr
        # 4,  # SENSATRONICS-EM1::group1TempDataInt
        # 5,  # SENSATRONICS-EM1::group1HumidName
        # 6,  # group1HumidDataStr
        # 7,  # group1HumidDataInt
        # 8,  # group1WetName
        # 9,  # group1WetDataStr
        # 10, # group1WetDataInt,
        SNMPTree(
            base=".1.3.6.1.4.1.16174.1.1.3.2.3",
            oids=["1"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.16174.1.1.3.3",
            oids=["1", "2", "3", "4"],
        ),
    ],
    service_name="Sensor - %s",
    discovery_function=discover_strem1_sensors,
    check_function=check_strem1_sensors,
)
