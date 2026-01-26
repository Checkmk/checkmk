#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterator, Mapping, Sequence

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.bvip.lib import DETECT_BVIP

check_info = {}


def discover_bvip_link(info: StringTable) -> list[tuple[None, dict[str, object]]]:
    if info:
        return [(None, {})]
    return []


def check_bvip_link(
    _no_item: None, params: Mapping[str, Sequence[int]], info: StringTable
) -> Iterator[tuple[int, str]]:
    count = 0
    states = {
        0: "No Link",
        1: "10 MBit - HalfDuplex",
        2: "10 MBit - FullDuplex",
        3: "100 Mbit - HalfDuplex",
        4: "100 Mbit - FullDuplex",
        5: "1 Gbit - FullDuplex",
        7: "Wifi",
    }
    for line in info:
        count += 1
        link_status = int(line[0])
        if link_status in params["ok_states"]:
            state = 0
        elif link_status in params["crit_states"]:
            state = 2
        elif link_status in params["warn_states"]:
            state = 1
        else:
            state = 3
        yield (
            state,
            "{}: State: {}".format(
                count,
                states.get(link_status, "Not Implemented (%s)" % link_status),
            ),
        )


def parse_bvip_link(string_table: StringTable) -> StringTable:
    return string_table


check_info["bvip_link"] = LegacyCheckDefinition(
    name="bvip_link",
    parse_function=parse_bvip_link,
    detect=DETECT_BVIP,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3967.1.5.1.8",
        oids=["1"],
    ),
    service_name="Network Link",
    discovery_function=discover_bvip_link,
    check_function=check_bvip_link,
    check_ruleset_name="bvip_link",
    check_default_parameters={
        "ok_states": [0, 4, 5],
        "warn_states": [7],
        "crit_states": [1, 2, 3],
    },
)
