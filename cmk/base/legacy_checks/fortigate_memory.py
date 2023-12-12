#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import check_levels, LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    all_of,
    contains,
    exists,
    render,
    SNMPTree,
)


def parse_fortigate_memory(string_table):
    try:
        return int(string_table[0][0])
    except ValueError:
        return None


def inventory_fortigate_memory(parsed):
    if parsed is not None:
        return [(None, {})]
    return []


def check_fortigate_memory(item, params, current_reading):
    if current_reading is None:
        return

    warn, crit = params["levels"]
    if isinstance(warn, int):
        yield 3, "Absolute levels are not supported"
        warn, crit = None, None

    # The checkgroup "memory" might set negative values which act as levels for free space
    # These levels are converted to used space, too..
    if warn is not None and warn < 0:
        warn = 100 + warn
        crit = 100 + crit

    yield check_levels(
        current_reading,
        "mem_usage",
        (warn, crit),
        infoname="Usage",
        human_readable_func=render.percent,
    )


check_info["fortigate_memory"] = LegacyCheckDefinition(
    detect=all_of(contains(".1.3.6.1.2.1.1.1.0", "fortigate"), exists(".1.3.6.1.4.1.12356.1.9.0")),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12356.1",
        oids=["9"],
    ),
    parse_function=parse_fortigate_memory,
    service_name="Memory",
    discovery_function=inventory_fortigate_memory,
    check_function=check_fortigate_memory,
    check_ruleset_name="memory",
    check_default_parameters={"levels": (70.0, 80.0)},
)
