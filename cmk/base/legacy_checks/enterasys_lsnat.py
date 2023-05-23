#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition, saveint, state_markers
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import all_of, exists, SNMPTree, startswith


def inventory_enterasys_lsnat(info):
    return [(None, {})]


def check_enterasys_lsnat(_no_item, params, info):
    if not info:
        return 3, "LSNAT bindings info is missing"

    lsnat_bindings = saveint(info[0][0])
    warn, crit = params.get("current_bindings", (None, None))

    state = 0
    state_info = ""
    if warn:
        if lsnat_bindings > crit:
            state = 2
            state_info = state_markers[state]
        elif lsnat_bindings > warn:
            state = 1
            state_info = state_markers[state]

    perfdata = [("current_bindings", lsnat_bindings, warn, crit)]

    return state, "Current bindings %d%s" % (lsnat_bindings, state_info), perfdata


check_info["enterasys_lsnat"] = LegacyCheckDefinition(
    detect=all_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.5624.2.1"),
        exists(".1.3.6.1.4.1.5624.1.2.74.1.1.5.0"),
    ),
    check_function=check_enterasys_lsnat,
    discovery_function=inventory_enterasys_lsnat,
    service_name="LSNAT Bindings",
    check_ruleset_name="lsnat",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.5624.1.2.74.1.1.5",
        oids=["0"],
    ),
)
