#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.hitachi_hnas import DETECT

check_info = {}


def hitachi_hnas_pnode_combine_item(id_, name):
    combined = str(id_)
    if name != "":
        combined += " " + name
    return combined


def inventory_hitachi_hnas_pnode(info):
    inventory = []
    for id_, name, _status in info:
        inventory.append((hitachi_hnas_pnode_combine_item(id_, name), None))
    return inventory


def check_hitachi_hnas_pnode(item, _no_params, info):
    statusmap = (
        ("", 3),
        ("unknown", 3),
        ("up", 0),
        ("notUp", 1),
        ("onLine", 0),
        ("dead", 2),
        ("dormant", 2),
    )

    for id_, name, status in info:
        if hitachi_hnas_pnode_combine_item(id_, name) == item:
            status = int(status)
            if status == 0 or status >= len(statusmap):
                return 3, "PNode reports unidentified status %s" % status
            return statusmap[status][1], "PNode reports status %s" % statusmap[status][0]

    return 3, "SNMP did not report a status of this PNode"


def parse_hitachi_hnas_pnode(string_table: StringTable) -> StringTable:
    return string_table


check_info["hitachi_hnas_pnode"] = LegacyCheckDefinition(
    name="hitachi_hnas_pnode",
    parse_function=parse_hitachi_hnas_pnode,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11096.6.1.1.1.2.5.9.1",
        oids=["1", "2", "4"],
    ),
    service_name="PNode %s",
    discovery_function=inventory_hitachi_hnas_pnode,
    check_function=check_hitachi_hnas_pnode,
)
