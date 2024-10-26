#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import render, SNMPTree
from cmk.plugins.lib.sophos import DETECT_SOPHOS

check_info = {}


def parse_sophos_memory(string_table):
    try:
        return int(string_table[0][0])
    except (ValueError, IndexError):
        return None


def check_sophos_memory(_item, params, parsed):
    return check_levels(
        parsed,
        "memory_util",
        params.get("memory_levels", (None, None)),
        infoname="Usage",
        human_readable_func=render.percent,
    )


def discover_sophos_memory(parsed):
    yield None, {}


check_info["sophos_memory"] = LegacyCheckDefinition(
    name="sophos_memory",
    detect=DETECT_SOPHOS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.21067.2.1.2.4",
        oids=["2"],
    ),
    parse_function=parse_sophos_memory,
    service_name="Memory",
    discovery_function=discover_sophos_memory,
    check_function=check_sophos_memory,
    check_ruleset_name="sophos_memory",
)
