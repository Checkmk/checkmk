#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import equals, SNMPTree, StringTable
from cmk.base.check_legacy_includes.temperature import check_temperature

check_info = {}

# this is currently here only to prevent error messages when upgrading


def inventory_adva_fsp_temp(info):
    for line in info:
        # Ignore unconnected sensors
        if len(line) == 5 and line[0] != "" and line[4] != "" and int(line[0]) >= -2730:
            yield line[4], {}


def check_adva_fsp_temp(item, params, info):
    for line in info:
        if len(line) == 5 and line[4] == item:
            temp, high, low, _descr = line[0:4]
            temp = float(temp) / 10
            high = float(high) / 10
            low = float(low) / 10

            if temp <= -2730:
                return 3, "Invalid sensor data"

            if low > -273:
                return check_temperature(
                    temp,
                    params,
                    "adva_fsp_temp_%s" % item,
                    dev_levels=(high, high),
                    dev_levels_lower=(low, low),
                )

            return check_temperature(
                temp, params, "adva_fsp_temp_%s" % item, dev_levels=(high, high)
            )
    return None


def parse_adva_fsp_temp(string_table: StringTable) -> StringTable:
    return string_table


check_info["adva_fsp_temp"] = LegacyCheckDefinition(
    name="adva_fsp_temp",
    parse_function=parse_adva_fsp_temp,
    detect=equals(".1.3.6.1.2.1.1.1.0", "Fiber Service Platform F7"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2544",
        oids=[
            "1.11.2.4.2.1.1.1",
            "1.11.2.4.2.1.1.2",
            "1.11.2.4.2.1.1.3",
            "2.5.5.1.1.1",
            "2.5.5.2.1.5",
        ],
    ),
    service_name="Temperature %s",
    discovery_function=inventory_adva_fsp_temp,
    check_function=check_adva_fsp_temp,
    check_ruleset_name="temperature",
    check_default_parameters={},
)
