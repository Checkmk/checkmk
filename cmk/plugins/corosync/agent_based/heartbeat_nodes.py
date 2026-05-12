#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example outputs from agent:
#
# <<<heartbeat_nodes>>>
# smwp active lanb up lanb up lana up lana up
# swi04 ping swi04 up
# swi03 ping swi03 up


from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)


def parse_heartbeat_nodes(string_table: StringTable) -> StringTable:
    return string_table


def discover_heartbeat_nodes(section: StringTable) -> DiscoveryResult:
    for line in section:
        if line[0] != "":
            yield Service(item=line[0])


def check_heartbeat_nodes(item: str, section: StringTable) -> CheckResult:
    for line in section:
        if line[0] == item:
            status = State.OK
            node_status = line[1]

            link_output = ""
            for link, state in zip(line[2::2], line[3::2]):
                state_txt = ""
                if state != "up":
                    status = State.CRIT
                    state_txt = " (!!)"
                link_output += f"{link}: {state}{state_txt}, "
            link_output = link_output.rstrip(", ")

            if node_status in ["active", "up", "ping"] and status == State.OK:
                status = State.OK
            elif node_status == "dead":
                status = State.CRIT

            if node_status not in ["active", "up", "ping", "dead"]:
                yield Result(
                    state=State.UNKNOWN,
                    summary=f"Node {line[0]} has an unhandled state: {node_status}",
                )
                return

            yield Result(
                state=status,
                summary=f'Node {line[0]} is in state "{node_status}". Links: {link_output}',
            )
            return

    yield Result(state=State.UNKNOWN, summary="Node is not present anymore")


agent_section_heartbeat_nodes = AgentSection(
    name="heartbeat_nodes",
    parse_function=parse_heartbeat_nodes,
)

check_plugin_heartbeat_nodes = CheckPlugin(
    name="heartbeat_nodes",
    service_name="Heartbeat Node %s",
    discovery_function=discover_heartbeat_nodes,
    check_function=check_heartbeat_nodes,
)
