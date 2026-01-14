#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.checkpoint.lib import DETECT

check_info = {}

tunnel_states = {
    "3": "Active",
    "4": "Destroy",
    "129": "Idle",
    "130": "Phase1",
    "131": "Down",
    "132": "Init",
}


def discover_checkpoint_tunnels(info):
    for peer, _ in info:
        yield peer, {}


def check_checkpoint_tunnels(item, params, info):
    for peer, status in info:
        if peer == item:
            state = params[tunnel_states[status]]
            return state, tunnel_states[status]
    return None


def parse_checkpoint_tunnels(string_table: StringTable) -> StringTable:
    return string_table


check_info["checkpoint_tunnels"] = LegacyCheckDefinition(
    name="checkpoint_tunnels",
    parse_function=parse_checkpoint_tunnels,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2620.500.9002.1",
        oids=["2", "3"],
    ),
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
