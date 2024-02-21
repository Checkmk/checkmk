#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.avaya import DETECT_AVAYA

avaya_chassis_ps_status_codes = {
    1: (3, "unknown", "Status cannot be determined"),
    2: (1, "empty", "Power supply not installed"),
    3: (0, "up", "Present and supplying power"),
    4: (2, "down", "Failure indicated"),
}


def inventory_avaya_chassis_ps(info):
    for line in info:
        # Discover only installed power supplies
        if line[1] != "2":
            yield line[0], None


def check_avaya_chassis_ps(item, _no_params, info):
    for line in info:
        if line[0] == item:
            ps_status_code = int(line[1])

    status, status_name, description = avaya_chassis_ps_status_codes[ps_status_code]
    return status, f"{description} ({status_name})"


def parse_avaya_chassis_ps(string_table: StringTable) -> StringTable:
    return string_table


check_info["avaya_chassis_ps"] = LegacyCheckDefinition(
    parse_function=parse_avaya_chassis_ps,
    detect=DETECT_AVAYA,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2272.1.4.8.1.1",
        oids=["1", "2"],
    ),
    service_name="Power Supply %s",
    discovery_function=inventory_avaya_chassis_ps,
    check_function=check_avaya_chassis_ps,
)
