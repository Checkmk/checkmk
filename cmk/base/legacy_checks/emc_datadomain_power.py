#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.emc import DETECT_DATADOMAIN

check_info = {}


def inventory_emc_datadomain_power(info):
    inventory = []
    for line in info:
        item = line[0] + "-" + line[1]
        inventory.append((item, None))
    return inventory


def check_emc_datadomain_power(item, _no_params, info):
    state_table = {
        "0": ("Absent", 0),
        "1": ("OK", 0),
        "2": ("Failed", 2),
        "3": ("Faulty", 2),
        "4": ("Acnone", 1),
        "99": ("Unknown", 3),
    }
    for line in info:
        if item == line[0] + "-" + line[1]:
            dev_descr = line[2]
            dev_state = line[3]
            dev_state_str = state_table.get(dev_state, ("Unknown", 3))[0]
            dev_state_rc = state_table.get(dev_state, ("Unknown", 3))[1]
            infotext = f"{dev_descr} Status {dev_state_str}"
            return dev_state_rc, infotext
    return None


def parse_emc_datadomain_power(string_table: StringTable) -> StringTable:
    return string_table


check_info["emc_datadomain_power"] = LegacyCheckDefinition(
    name="emc_datadomain_power",
    parse_function=parse_emc_datadomain_power,
    detect=DETECT_DATADOMAIN,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.19746.1.1.1.1.1.1",
        oids=["1", "2", "3", "4"],
    ),
    service_name="Power Module %s",
    discovery_function=inventory_emc_datadomain_power,
    check_function=check_emc_datadomain_power,
)
