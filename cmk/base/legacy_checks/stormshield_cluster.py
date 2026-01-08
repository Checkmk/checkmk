#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Older versions replay an empty string if the state is Unknown / Error state


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import (
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.stormshield import DETECT_STORMSHIELD_CLUSTER

sync_name_mapping = {
    "1": "Synced",
    "0": "Not Synced",
    "-1": "Unknown / Error",
    "": "Unknown / Error",
}

sync_status_mapping = {
    "1": 0,
    "0": 2,
    "-1": 3,
    "": 3,
}


def inventory_stormshield_cluster(info):
    yield None, None


def check_stormshield_cluster(item, params, info):
    for number, not_replying, active, eth_links, faulty_links, sync in info:
        _not_replying = int(not_replying)
        _faulty_links = int(faulty_links)

        yield sync_status_mapping[sync], "Sync Status: %s" % sync_name_mapping[sync]
        yield 0, f"Member: {number}, Active: {active}, Links used: {eth_links}"

        if _not_replying > 0:
            status = 2
        else:
            status = 0
        yield status, "Not replying: %s" % _not_replying

        if _faulty_links > 0:
            status = 2
        else:
            status = 0
        yield status, "Faulty: %s" % _faulty_links


def parse_stormshield_cluster(string_table: StringTable) -> StringTable | None:
    return string_table or None


check_info["stormshield_cluster"] = LegacyCheckDefinition(
    parse_function=parse_stormshield_cluster,
    detect=DETECT_STORMSHIELD_CLUSTER,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11256.1.11",
        oids=["1", "2", "3", "5", "6", "8"],
    ),
    service_name="HA Status",
    discovery_function=inventory_stormshield_cluster,
    check_function=check_stormshield_cluster,
)
