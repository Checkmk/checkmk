#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_legacy_includes.cisco_ucs import DETECT, map_operability
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree

# comNET GmbH, Fabian Binder - 2018-05-07

# .1.3.6.1.4.1.9.9.719.1.15.12.1.2  cucsEquipmentFanDn
# .1.3.6.1.4.1.9.9.719.1.15.12.1.10 cucsEquipmentFanOperability


def inventory_cisco_ucs_fan(info):
    for name, _status in info:
        name = " ".join(name.split("/")[2:])
        yield name, None


def check_cisco_ucs_fan(item, _no_params, info):
    for name, status in info:
        name = " ".join(name.split("/")[2:])
        if name == item:
            state, state_readable = map_operability.get(
                status, (3, "Unknown, status code %s" % status)
            )
            return state, "Status: %s" % (state_readable)
    return None


check_info["cisco_ucs_fan"] = {
    "detect": DETECT,
    "check_function": check_cisco_ucs_fan,
    "discovery_function": inventory_cisco_ucs_fan,
    "service_name": "Fan %s",
    "fetch": SNMPTree(
        base=".1.3.6.1.4.1.9.9.719.1.15.12.1",
        oids=["2", "10"],
    ),
}
