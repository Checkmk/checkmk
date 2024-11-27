#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.emc import DETECT_DATADOMAIN

check_info = {}


def inventory_emc_datadomain_nvbat(info):
    inventory = []
    for line in info:
        item = line[0] + "-" + line[1]
        inventory.append((item, None))
    return inventory


def check_emc_datadomain_nvbat(item, _no_params, info):
    state_table = {
        "0": ("OK", 0),
        "1": ("Disabled", 1),
        "2": ("Discharged", 2),
        "3": ("Softdisabled", 1),
    }
    for line in info:
        if item == line[0] + "-" + line[1]:
            dev_charge = line[3]
            dev_state = line[2]
            dev_state_str = state_table.get(dev_state, ("Unknown", 3))[0]
            dev_state_rc = state_table.get(dev_state, ("Unknown", 3))[1]
            infotext = f"Status {dev_state_str} Charge Level {dev_charge}%"
            perfdata = [("battery_capacity", dev_charge + "%")]
            return dev_state_rc, infotext, perfdata
    return None


def parse_emc_datadomain_nvbat(string_table: StringTable) -> StringTable:
    return string_table


check_info["emc_datadomain_nvbat"] = LegacyCheckDefinition(
    name="emc_datadomain_nvbat",
    parse_function=parse_emc_datadomain_nvbat,
    detect=DETECT_DATADOMAIN,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.19746.1.2.3.1.1",
        oids=["1", "2", "3", "4"],
    ),
    service_name="NVRAM Battery %s",
    discovery_function=inventory_emc_datadomain_nvbat,
    check_function=check_emc_datadomain_nvbat,
)
