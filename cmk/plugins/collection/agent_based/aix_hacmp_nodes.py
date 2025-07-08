#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

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


@dataclass(frozen=True, kw_only=True)
class NetworkInterface:
    name: str
    attribute: str
    ip_address: str


type Section = Mapping[str, Mapping[str, Sequence[NetworkInterface]]]


def parse_aix_hacmp_nodes(
    string_table: StringTable,
) -> Section:
    parsed: dict[str, dict[str, list[NetworkInterface]]] = {}
    for line in string_table:
        if len(line) == 1:
            parsed[line[0]] = {}

        elif "node" in line[0].lower():
            if line[1].replace(":", "") in parsed:
                node_name = line[1].replace(":", "")
                get_details = True
            else:
                get_details = False

        elif "Interfaces" in line[0] and get_details:
            network_name = line[3].replace(",", "")
            parsed[node_name][network_name] = []

        elif "Communication" in line[0] and get_details:
            parsed[node_name][network_name].append(
                NetworkInterface(
                    name=line[3].replace(",", ""),
                    attribute=line[5].replace(",", ""),
                    ip_address=line[8].replace(",", ""),
                )
            )

    return parsed


def discover_aix_hacmp_nodes(section: Section) -> DiscoveryResult:
    yield from [Service(item=key) for key in section]


def check_aix_hacmp_nodes(item: str, section: Section) -> CheckResult:
    if (data := section.get(item)) is None:
        return

    for network_name in data:
        infotext = "Network: %s" % network_name

        for interface in data[network_name]:
            infotext += f", interface: {interface.name}, attribute: {interface.attribute}, IP: {interface.ip_address}"

        yield Result(state=State.OK, summary=infotext)


agent_section_aix_hacmp_nodes = AgentSection(
    name="aix_hacmp_nodes", parse_function=parse_aix_hacmp_nodes
)
check_plugin_aix_hacmp_nodes = CheckPlugin(
    name="aix_hacmp_nodes",
    service_name="HACMP Node %s",
    discovery_function=discover_aix_hacmp_nodes,
    check_function=check_aix_hacmp_nodes,
)
