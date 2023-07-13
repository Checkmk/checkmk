#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.stormshield import DETECT_STORMSHIELD

route_type_mapping = {
    "DefaultRoute": "default route",
    "PBR": "policy based routing",
    "": "not defined",
}

route_state_mapping = {
    "UP": (0, "Route is up"),
    "DOWN": (2, "Route is down"),
    "UNDEF": (3, "Route is undefined"),
}


def inventory_stormshield_route(info):
    for line in info:
        if line[5] == "UP":
            yield (line[0], None)


def check_stormshield_route(item, params, info):
    for line in info:
        if line[0] == item:
            _index, typ, name, gateway_name, gateway_type, state = line
            yield route_state_mapping[state]
            infotext = "Type: %s, Router name: %s, Gateway name: %s, Gateway type: %s" % (
                route_type_mapping[typ],
                name,
                gateway_name,
                gateway_type,
            )
            yield 0, infotext


check_info["stormshield_route"] = LegacyCheckDefinition(
    detect=DETECT_STORMSHIELD,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11256.1.14.1.1",
        oids=["1", "2", "4", "5", "7", "9"],
    ),
    service_name="Gateway %s",
    discovery_function=inventory_stormshield_route,
    check_function=check_stormshield_route,
)
