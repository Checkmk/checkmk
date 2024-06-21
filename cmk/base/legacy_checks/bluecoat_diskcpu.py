#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import contains, SNMPTree, StringTable


def inventory_bluecoat_diskcpu(info):
    return [(line[0], None) for line in info]


def check_bluecoat_diskcpu(item, _no_params, info):
    for line in info:
        if line[0] == item:
            perfdata = [("value", line[1])]
            if line[2] == "1":
                return (0, f"{line[1]}", perfdata)
            return (2, f"{line[1]}", perfdata)
    return (3, "item not found in SNMP data")


def parse_bluecoat_diskcpu(string_table: StringTable) -> StringTable:
    return string_table


check_info["bluecoat_diskcpu"] = LegacyCheckDefinition(
    parse_function=parse_bluecoat_diskcpu,
    detect=contains(".1.3.6.1.2.1.1.2.0", "1.3.6.1.4.1.3417.1.1"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3417.2.4.1.1.1",
        oids=["3", "4", "6"],
    ),
    service_name="%s",
    discovery_function=inventory_bluecoat_diskcpu,
    check_function=check_bluecoat_diskcpu,
)
