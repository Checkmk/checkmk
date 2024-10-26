#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.emc import DETECT_DATADOMAIN

check_info = {}


def inventory_emc_datadomain_fans(info):
    inventory = []
    for line in info:
        item = line[0] + "-" + line[1]
        inventory.append((item, None))
    return inventory


def check_emc_datadomain_fans(item, _no_params, info):
    state_table = {
        "0": ("notfound", 1),
        "1": ("OK", 0),
        "2": ("Fail", 2),
    }
    fan_level = {"0": "Unknown", "1": "Low", "2": "Medium", "3": "High"}
    for line in info:
        if item == f"{line[0]}-{line[1]}":
            dev_descr = line[2]
            dev_level = line[3]
            dev_state = line[4]
            dev_state_str = state_table.get(dev_state, ("Unknown", 3))[0]
            dev_state_rc = state_table.get(dev_state, ("Unknown", 3))[1]
            dev_level_str = fan_level.get(dev_level, "Unknown")
            infotext = f"{dev_descr} {dev_state_str} RPM {dev_level_str}"
            return dev_state_rc, infotext
    return None


def parse_emc_datadomain_fans(string_table: StringTable) -> StringTable:
    return string_table


check_info["emc_datadomain_fans"] = LegacyCheckDefinition(
    name="emc_datadomain_fans",
    parse_function=parse_emc_datadomain_fans,
    detect=DETECT_DATADOMAIN,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.19746.1.1.3.1.1.1",
        oids=["1", "2", "4", "5", "6"],
    ),
    service_name="FAN %s",
    discovery_function=inventory_emc_datadomain_fans,
    check_function=check_emc_datadomain_fans,
)
