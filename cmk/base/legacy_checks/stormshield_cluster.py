#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Older versions replay an empty string if the state is Unknown / Error state


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    all_of,
    any_of,
    equals,
    exists,
    SNMPTree,
    startswith,
)

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
        not_replying = int(not_replying)
        faulty_links = int(faulty_links)

        yield sync_status_mapping[sync], "Sync Status: %s" % sync_name_mapping[sync]
        yield 0, "Member: %s, Active: %s, Links used: %s" % (number, active, eth_links)

        if not_replying > 0:
            status = 2
        else:
            status = 0
        yield status, "Not replying: %s" % not_replying

        if faulty_links > 0:
            status = 2
        else:
            status = 0
        yield status, "Faulty: %s" % faulty_links


check_info["stormshield_cluster"] = LegacyCheckDefinition(
    detect=all_of(
        any_of(
            startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.8072.3.2.8"),
            equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.11256.2.0"),
        ),
        exists(".1.3.6.1.4.1.11256.1.11.*"),
    ),
    discovery_function=inventory_stormshield_cluster,
    check_function=check_stormshield_cluster,
    service_name="HA Status",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11256.1.11",
        oids=["1", "2", "3", "5", "6", "8"],
    ),
)
