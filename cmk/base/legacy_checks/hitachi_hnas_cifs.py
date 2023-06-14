#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.hitachi_hnas import DETECT


def inventory_hitachi_hnas_cifs(info):
    inventory = []
    for evs_id, share_name, _users in info:
        inventory.append((evs_id + " " + share_name, None))
    return inventory


def check_hitachi_hnas_cifs(item, _no_params, info):
    for evs_id, share_name, users in info:
        if evs_id + " " + share_name == item:
            perfdata = [("users", users, "", "", 0)]
            return 0, "%s users" % users, perfdata
    return 3, "Share not found"


check_info["hitachi_hnas_cifs"] = LegacyCheckDefinition(
    detect=DETECT,
    check_function=check_hitachi_hnas_cifs,
    discovery_function=inventory_hitachi_hnas_cifs,
    service_name="CIFS Share EVS %s",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11096.6.1.1.3.2.1.3.1",
        oids=["1", "2", "5"],
    ),
)
