#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<netapp_api_vf_status:sep(9)>>>
# zcs1v    running
# zhs01    running
# zmppl01  running
# zmdp     running
# cdefs1v  running


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import StringTable


def inventory_netapp_api_vf_status(info):
    return [(x[0], None) for x in info]


def check_netapp_api_vf_status(item, _no_params, info):
    filer_states = dict(info)
    if item not in filer_states:
        return None

    state = 0 if filer_states[item] in ["running", "DR backup", "migrating"] else 2
    return state, "State is %s" % filer_states[item]


def parse_netapp_api_vf_status(string_table: StringTable) -> StringTable:
    return string_table


check_info["netapp_api_vf_status"] = LegacyCheckDefinition(
    parse_function=parse_netapp_api_vf_status,
    service_name="vFiler Status %s",
    discovery_function=inventory_netapp_api_vf_status,
    check_function=check_netapp_api_vf_status,
)
