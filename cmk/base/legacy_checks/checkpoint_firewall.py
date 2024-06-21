#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.checkpoint import DETECT


def inventory_checkpoint_firewall(info):
    if info:
        return [(None, None)]
    return []


def check_checkpoint_firewall(item, params, info):
    if info:
        state, filter_name, filter_date, major, minor = info[0]
        if state.lower() == "installed":
            return 0, "{} (v{}.{}), filter: {} (since {})".format(
                state,
                major,
                minor,
                filter_name,
                filter_date,
            )
        return 2, "not installed, state: %s" % state
    return None


def parse_checkpoint_firewall(string_table: StringTable) -> StringTable:
    return string_table


check_info["checkpoint_firewall"] = LegacyCheckDefinition(
    parse_function=parse_checkpoint_firewall,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2620.1.1",
        oids=["1", "2", "3", "8", "9"],
    ),
    service_name="Firewall Module",
    discovery_function=inventory_checkpoint_firewall,
    check_function=check_checkpoint_firewall,
)
