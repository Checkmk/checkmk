#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.bvip.lib import DETECT_BVIP


def parse_bvip_link(string_table: StringTable) -> StringTable:
    return string_table


def discover_bvip_link(section: StringTable) -> DiscoveryResult:
    if section:
        yield Service()


def check_bvip_link(params: Mapping[str, Sequence[int]], section: StringTable) -> CheckResult:
    states = {
        0: "No Link",
        1: "10 MBit - HalfDuplex",
        2: "10 MBit - FullDuplex",
        3: "100 Mbit - HalfDuplex",
        4: "100 Mbit - FullDuplex",
        5: "1 Gbit - FullDuplex",
        7: "Wifi",
    }
    for count, line in enumerate(section, start=1):
        link_status = int(line[0])
        if link_status in params["ok_states"]:
            state = State.OK
        elif link_status in params["crit_states"]:
            state = State.CRIT
        elif link_status in params["warn_states"]:
            state = State.WARN
        else:
            state = State.UNKNOWN
        yield Result(
            state=state,
            summary=f"{count}: State: {states.get(link_status, f'Not Implemented ({link_status})')}",
        )


snmp_section_bvip_link = SimpleSNMPSection(
    name="bvip_link",
    detect=DETECT_BVIP,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3967.1.5.1.8",
        oids=["1"],
    ),
    parse_function=parse_bvip_link,
)


check_plugin_bvip_link = CheckPlugin(
    name="bvip_link",
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
