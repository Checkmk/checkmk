#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping

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
from cmk.plugins.checkpoint.lib import DETECT

tunnel_states = {
    "3": "Active",
    "4": "Destroy",
    "129": "Idle",
    "130": "Phase1",
    "131": "Down",
    "132": "Init",
}


def parse_checkpoint_tunnels(string_table: StringTable) -> StringTable:
    return string_table


def discover_checkpoint_tunnels(section: StringTable) -> DiscoveryResult:
    for peer, _status in section:
        yield Service(item=peer)


def check_checkpoint_tunnels(
    item: str, params: Mapping[str, int], section: StringTable
) -> CheckResult:
    for peer, status in section:
        if peer == item:
            state_name = tunnel_states.get(status)
            if state_name is None:
                yield Result(state=State.UNKNOWN, summary=f"Unknown tunnel status: {status}")
                return
            yield Result(state=State(params[state_name]), summary=state_name)
            return


snmp_section_checkpoint_tunnels = SimpleSNMPSection(
    name="checkpoint_tunnels",
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2620.500.9002.1",
        oids=["2", "3"],
    ),
    parse_function=parse_checkpoint_tunnels,
)


check_plugin_checkpoint_tunnels = CheckPlugin(
    name="checkpoint_tunnels",
    service_name="Tunnel %s",
    discovery_function=discover_checkpoint_tunnels,
    check_function=check_checkpoint_tunnels,
    check_ruleset_name="checkpoint_tunnels",
    check_default_parameters={
        "Active": 0,
        "Destroy": 1,
        "Idle": 0,
        "Phase1": 2,
        "Down": 2,
        "Init": 1,
    },
)
