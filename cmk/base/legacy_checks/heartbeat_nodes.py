#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

# Author: Lars Michelsen <lm@mathias-kettner.de>

# Example outputs from agent:
#
# <<<heartbeat_nodes>>>
# smwp active lanb up lanb up lana up lana up
# swi04 ping swi04 up
# swi03 ping swi03 up


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import StringTable

check_info = {}


def discover_heartbeat_nodes(info):
    return [(line[0], None) for line in info if line[0] != ""]


def check_heartbeat_nodes(item, params, info):
    for line in info:
        if line[0] == item:
            status = 0
            nodeStatus = line[1]

            linkOutput = ""
            for link, state in zip(line[2::2], line[3::2]):
                state_txt = ""
                if state != "up":
                    status = 2
                    state_txt = " (!!)"
                linkOutput += f"{link}: {state}{state_txt}, "
            linkOutput = linkOutput.rstrip(", ")

            if nodeStatus in ["active", "up", "ping"] and status <= 0:
                status = 0
            elif nodeStatus == "dead" and status <= 2:
                status = 2

            if nodeStatus not in ["active", "up", "ping", "dead"]:
                return (3, f"Node {line[0]} has an unhandled state: {nodeStatus}")

            return (
                status,
                f'Node {line[0]} is in state "{nodeStatus}". Links: {linkOutput}',
            )

    return (3, "Node is not present anymore")


def parse_heartbeat_nodes(string_table: StringTable) -> StringTable:
    return string_table


check_info["heartbeat_nodes"] = LegacyCheckDefinition(
    name="heartbeat_nodes",
    parse_function=parse_heartbeat_nodes,
    service_name="Heartbeat Node %s",
    discovery_function=discover_heartbeat_nodes,
    check_function=check_heartbeat_nodes,
)
