#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

# cseSysMemoryUtilization   .1.3.6.1.4.1.9.9.305.1.1.2.0
#


from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import render, SNMPTree, startswith, StringTable

check_info = {}


def discover_cisco_sys_mem(info):
    if info:
        yield None, {}


def check_cisco_sys_mem(_no_item, params, info):
    if info[0][0]:
        mem_used_percent = float(info[0][0])
        return check_levels(
            mem_used_percent,
            "mem_used_percent",
            params["levels"],
            human_readable_func=render.percent,
            infoname="Supervisor Memory used",
            boundaries=(0, 100),
        )
    return None


def parse_cisco_sys_mem(string_table: StringTable) -> StringTable:
    return string_table


check_info["cisco_sys_mem"] = LegacyCheckDefinition(
    name="cisco_sys_mem",
    parse_function=parse_cisco_sys_mem,
    detect=startswith(".1.3.6.1.2.1.1.1.0", "Cisco NX-OS"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9.9.305.1.1.2",
        oids=["0"],
    ),
    service_name="Supervisor Mem Used",
    discovery_function=discover_cisco_sys_mem,
    check_function=check_cisco_sys_mem,
    check_ruleset_name="cisco_supervisor_mem",  # separate group since only percentage,
    check_default_parameters={"levels": (80.0, 90.0)},
)
