#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.emc import DETECT_DATADOMAIN


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
            infotext = "Status %s Charge Level %s%%" % (dev_state_str, dev_charge)
            perfdata = [("charge", dev_charge + "%")]
            return dev_state_rc, infotext, perfdata
    return None


check_info["emc_datadomain_nvbat"] = LegacyCheckDefinition(
    detect=DETECT_DATADOMAIN,
    check_function=check_emc_datadomain_nvbat,
    discovery_function=inventory_emc_datadomain_nvbat,
    service_name="NVRAM Battery %s",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.19746.1.2.3.1.1",
        oids=["1", "2", "3", "4"],
    ),
)
