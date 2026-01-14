#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, startswith, StringTable

check_info = {}


def discover_packeteer_ps_status(info):
    if info:
        return [(None, None)]
    return []


def check_packeteer_ps_status(_no_item, _no_params, info):
    for nr, ps_status in enumerate(info[0]):
        if ps_status == "1":
            yield 0, "Power Supply %d okay" % nr
        else:
            yield 2, "Power Supply %d not okay" % nr


def parse_packeteer_ps_status(string_table: StringTable) -> StringTable:
    return string_table


check_info["packeteer_ps_status"] = LegacyCheckDefinition(
    name="packeteer_ps_status",
    parse_function=parse_packeteer_ps_status,
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.2334"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2334.2.1.5",
        oids=["8", "10"],
    ),
    service_name="Power Supply Status",
    discovery_function=discover_packeteer_ps_status,
    check_function=check_packeteer_ps_status,
)
