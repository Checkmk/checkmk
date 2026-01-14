#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.hitachi_hnas.lib import DETECT

check_info = {}


def hitachi_hnas_vnode_combine_item(id_, name):
    combined = str(id_)
    if name != "":
        combined += " " + name
    return combined


def discover_hitachi_hnas_vnode(info):
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
                f"EVS is hosted by PNode {hosted_by} and reports status {statusmap[status][0]}. {nodetype}",
            )

    return 3, "SNMP did not report a status of this EVS"


def parse_hitachi_hnas_vnode(string_table: StringTable) -> StringTable:
    return string_table


check_info["hitachi_hnas_vnode"] = LegacyCheckDefinition(
    name="hitachi_hnas_vnode",
    parse_function=parse_hitachi_hnas_vnode,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11096.6.1.1.1.2.5.11.1",
        oids=["1", "2", "4", "5", "6"],
    ),
    service_name="EVS %s",
    discovery_function=discover_hitachi_hnas_vnode,
    check_function=check_hitachi_hnas_vnode,
)
