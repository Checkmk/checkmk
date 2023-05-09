#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.hitachi_hnas import DETECT


def hitachi_hnas_vnode_combine_item(id_, name):
    combined = str(id_)
    if name != "":
        combined += " " + name
    return combined


def inventory_hitachi_hnas_vnode(info):
    inventory = []
    for id_, name, _status, _is_admin, _hosted_by in info:
        inventory.append((hitachi_hnas_vnode_combine_item(id_, name), None))
    return inventory


def check_hitachi_hnas_vnode(item, _no_params, info):
    statusmap = (
        ("", 3),
        ("unknown", 3),
        ("onLine", 0),
        ("offLine", 2),
    )

    for id_, name, status, is_admin, hosted_by in info:
        if hitachi_hnas_vnode_combine_item(id_, name) == item:
            status = int(status)
            nodetype = ""
            if status == 0 or status >= len(statusmap):
                return 3, "EVS reports unidentified status %s" % status

            if is_admin == "0":
                nodetype = "This is a service node."
            if is_admin == "1":
                nodetype = "This is a administrative node."
            return (
                statusmap[status][1],
                "EVS is hosted by PNode %s and reports status %s. %s"
                % (hosted_by, statusmap[status][0], nodetype),
            )

    return 3, "SNMP did not report a status of this EVS"


check_info["hitachi_hnas_vnode"] = {
    "detect": DETECT,
    "check_function": check_hitachi_hnas_vnode,
    "discovery_function": inventory_hitachi_hnas_vnode,
    "service_name": "EVS %s",
    "fetch": SNMPTree(
        base=".1.3.6.1.4.1.11096.6.1.1.1.2.5.11.1",
        oids=["1", "2", "4", "5", "6"],
    ),
}
