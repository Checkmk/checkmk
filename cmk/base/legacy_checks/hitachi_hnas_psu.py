#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.hitachi_hnas.lib import DETECT

check_info = {}


def discover_hitachi_hnas_psu(info):
    inventory = []
    for clusternode, id_, _status in info:
        inventory.append((clusternode + "." + id_, None))
    return inventory


def check_hitachi_hnas_psu(item, _no_params, info):
    statusmap = (
        ("", 3),  # 0
        ("ok", 0),  # 1
        ("failed", 2),  # 2
        ("notFitted", 1),  # 3
        ("unknown", 3),  # 4
    )

    for clusternode, id_, status in info:
        if clusternode + "." + id_ == item:
            status = int(status)
            if status == 0 or status >= len(statusmap):
                return 3, f"PNode {clusternode} PSU {id_} reports unidentified status {status}"
            return statusmap[status][
                1
            ], f"PNode {clusternode} PSU {id_} reports status {statusmap[status][0]}"

    return 3, "SNMP did not report a status of this PSU"


def parse_hitachi_hnas_psu(string_table: StringTable) -> StringTable:
    return string_table


check_info["hitachi_hnas_psu"] = LegacyCheckDefinition(
    name="hitachi_hnas_psu",
    parse_function=parse_hitachi_hnas_psu,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11096.6.1.1.1.2.1.13.1",
        oids=["1", "2", "3"],
    ),
    service_name="PSU %s",
    discovery_function=discover_hitachi_hnas_psu,
    check_function=check_hitachi_hnas_psu,
)
