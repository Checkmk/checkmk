#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree, startswith


def inventory_aruba_clients(info):
    if info:
        return [(None, {})]
    return []


def check_aruba_clients(_no_item, _params, info):
    try:
        connected_clients = info[0][0]
    except IndexError:
        return None
    return 0, "Connected: %s" % connected_clients, [("connections", connected_clients)]


check_info["aruba_clients"] = LegacyCheckDefinition(
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.14823"),
    discovery_function=inventory_aruba_clients,
    check_function=check_aruba_clients,
    service_name="WLAN Clients",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.14823.2.2.1.1.3",
        oids=["2"],
    ),
)
