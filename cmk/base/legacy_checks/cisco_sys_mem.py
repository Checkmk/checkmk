#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# cseSysMemoryUtilization   .1.3.6.1.4.1.9.9.305.1.1.2.0
#


from cmk.base.check_api import check_levels, LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import render, SNMPTree, startswith

cisco_sys_mem_default_levels = (80.0, 90.0)


def inventory_cisco_sys_mem(info):
    if info:
        return [(None, cisco_sys_mem_default_levels)]
    return []


def check_cisco_sys_mem(_no_item, params, info):
    if info[0][0]:
        mem_used_percent = float(info[0][0])
        return check_levels(
            mem_used_percent,
            "mem_used_percent",
            params,
            human_readable_func=render.percent,
            infoname="Supervisor Memory used",
            boundaries=(0, 100),
        )
    return None


check_info["cisco_sys_mem"] = LegacyCheckDefinition(
    detect=startswith(".1.3.6.1.2.1.1.1.0", "Cisco NX-OS"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9.9.305.1.1.2",
        oids=["0"],
    ),
    service_name="Supervisor Mem Used",
    discovery_function=inventory_cisco_sys_mem,
    check_function=check_cisco_sys_mem,
    check_ruleset_name="cisco_supervisor_mem",  # seperate group since only percentage,
)
