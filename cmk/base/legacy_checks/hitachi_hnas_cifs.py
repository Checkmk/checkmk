#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.hitachi_hnas.lib import DETECT

check_info = {}


def discover_hitachi_hnas_cifs(info):
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


def parse_hitachi_hnas_cifs(string_table: StringTable) -> StringTable:
    return string_table


check_info["hitachi_hnas_cifs"] = LegacyCheckDefinition(
    name="hitachi_hnas_cifs",
    parse_function=parse_hitachi_hnas_cifs,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11096.6.1.1.3.2.1.3.1",
        oids=["1", "2", "5"],
    ),
    service_name="CIFS Share EVS %s",
    discovery_function=discover_hitachi_hnas_cifs,
    check_function=check_hitachi_hnas_cifs,
)
