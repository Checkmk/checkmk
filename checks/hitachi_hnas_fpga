#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.hitachi_hnas import DETECT

hitachi_hnas_fpga_default_levels = {"levels": (80.0, 90.0)}


def inventory_hitachi_hnas_fpga(info):
    inventory = []
    for clusternode, id_, name, _util in info:
        inventory.append((clusternode + "." + id_ + " " + name, hitachi_hnas_fpga_default_levels))
    return inventory


def check_hitachi_hnas_fpga(item, params, info):
    warn, crit = params["levels"]
    rc = 0

    for clusternode, id_, name, util in info:
        if clusternode + "." + id_ + " " + name == item:
            util = float(util)
            if util > warn:
                rc = 1
            if util > crit:
                rc = 2
            perfdata = [("fpga_util", str(util) + "%", warn, crit, 0, 100)]
            return (
                rc,
                "PNode %s FPGA %s %s utilization is %s%%" % (clusternode, id_, name, util),
                perfdata,
            )

    return 3, "No utilization found for FPGA %s" % item


check_info["hitachi_hnas_fpga"] = {
    "detect": DETECT,
    "check_function": check_hitachi_hnas_fpga,
    "discovery_function": inventory_hitachi_hnas_fpga,
    "service_name": "FPGA %s",
    "fetch": SNMPTree(
        base=".1.3.6.1.4.1.11096.6.1.1.6.1.4.1",
        oids=["1", "2", "3", "4"],
    ),
    "check_ruleset_name": "fpga_utilization",
}
