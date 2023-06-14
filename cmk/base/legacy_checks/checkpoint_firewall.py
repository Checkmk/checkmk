#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.checkpoint import DETECT


def inventory_checkpoint_firewall(info):
    if info:
        return [(None, None)]
    return []


def check_checkpoint_firewall(item, params, info):
    if info:
        state, filter_name, filter_date, major, minor = info[0]
        if state.lower() == "installed":
            return 0, "%s (v%s.%s), filter: %s (since %s)" % (
                state,
                major,
                minor,
                filter_name,
                filter_date,
            )
        return 2, "not installed, state: %s" % state
    return None


check_info["checkpoint_firewall"] = LegacyCheckDefinition(
    detect=DETECT,
    check_function=check_checkpoint_firewall,
    discovery_function=inventory_checkpoint_firewall,
    service_name="Firewall Module",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2620.1.1",
        oids=["1", "2", "3", "8", "9"],
    ),
)
