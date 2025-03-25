#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import render, SNMPTree, StringTable
from cmk.plugins.lib.fireeye import DETECT

check_info = {}

# .1.3.6.1.4.1.25597.13.1.40.0 1


def discover_fireeye_quarantine(string_table):
    if string_table:
        yield None, {}


def check_fireeye_quarantine(_no_item, params, info):
    usage = int(info[0][0])
    return check_levels(
        usage,
        "quarantine",
        params["usage"],
        human_readable_func=render.percent,
        infoname="Usage",
    )


def parse_fireeye_quarantine(string_table: StringTable) -> StringTable:
    return string_table


check_info["fireeye_quarantine"] = LegacyCheckDefinition(
    name="fireeye_quarantine",
    parse_function=parse_fireeye_quarantine,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.25597.13.1.40",
        oids=["0"],
    ),
    service_name="Quarantine Usage",
    discovery_function=discover_fireeye_quarantine,
    check_function=check_fireeye_quarantine,
    check_ruleset_name="fireeye_quarantine",
    check_default_parameters={"usage": (70, 80)},
)
