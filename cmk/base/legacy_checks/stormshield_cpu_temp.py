#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_legacy_includes.temperature import check_temperature

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.stormshield import DETECT_STORMSHIELD

check_info = {}


def inventory_stormshield_cpu_temp(info):
    for index, _temp in info:
        yield index, {}


def check_stormshield_cpu_temp(item, params, info):
    for index, temp in info:
        if item == index:
            return check_temperature(int(temp), params, "stormshield_cpu_temp_%s" % index)
    return None


def parse_stormshield_cpu_temp(string_table: StringTable) -> StringTable:
    return string_table


check_info["stormshield_cpu_temp"] = LegacyCheckDefinition(
    name="stormshield_cpu_temp",
    parse_function=parse_stormshield_cpu_temp,
    detect=DETECT_STORMSHIELD,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11256.1.10.7.1",
        oids=["1", "2"],
    ),
    service_name="CPU Temp %s",
    discovery_function=inventory_stormshield_cpu_temp,
    check_function=check_stormshield_cpu_temp,
)
