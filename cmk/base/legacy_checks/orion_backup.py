#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree, startswith


def inventory_orion_backup(info):
    return [(None, {})]


def check_orion_backup(item, params, info):
    map_states = {
        "1": (1, "inactive"),
        "2": (0, "OK"),
        "3": (1, "occured"),
        "4": (2, "fail"),
    }

    backup_time_status, backup_time = info[0]
    state, state_readable = map_states[backup_time_status]
    return state, "Status: %s, Expected time: %s minutes" % (state_readable, backup_time)


check_info["orion_backup"] = LegacyCheckDefinition(
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.20246"),
    discovery_function=inventory_orion_backup,
    check_function=check_orion_backup,
    service_name="Backup",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.20246.2.3.1.1.1.2.5.3.3",
        oids=["2", "3"],
    ),
)
