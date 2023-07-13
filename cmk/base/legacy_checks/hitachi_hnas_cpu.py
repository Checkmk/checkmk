#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.hitachi_hnas import DETECT

hitachi_hnas_cpu_default_levels = {"levels": (80.0, 90.0)}


def inventory_hitachi_hnas_cpu(info):
    inventory = []
    for id_, _util in info:
        inventory.append((id_, hitachi_hnas_cpu_default_levels))
    return inventory


def check_hitachi_hnas_cpu(item, params, info):
    warn, crit = params["levels"]
    rc = 0

    for id_, util in info:
        if id_ == item:
            util = float(util)
            if util > warn:
                rc = 1
            if util > crit:
                rc = 2
            perfdata = [("cpu_util", str(util) + "%", warn, crit, 0, 100)]
            return rc, "CPU utilization is %s%%" % util, perfdata

    return 3, "No CPU utilization found"


check_info["hitachi_hnas_cpu"] = LegacyCheckDefinition(
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11096.6.1.1.6.1.2.1",
        oids=["1", "3"],
    ),
    service_name="CPU utilization PNode %s",
    discovery_function=inventory_hitachi_hnas_cpu,
    check_function=check_hitachi_hnas_cpu,
    check_ruleset_name="cpu_utilization_multiitem",
)
