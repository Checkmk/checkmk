#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="var-annotated"

from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
)


def parse_aix_hacmp_nodes(string_table):
    parsed = {}
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
                (line[3].replace(",", ""), line[5].replace(",", ""), line[8].replace(",", ""))
            )

    return parsed


def inventory_aix_hacmp_nodes(section: Any) -> DiscoveryResult:
    yield from [Service(item=key) for key in section]


def check_aix_hacmp_nodes(item: str, section: Any) -> CheckResult:
    if (data := section.get(item)) is None:
        return

    for network_name in data:
        infotext = "Network: %s" % network_name

        for if_name, attribute, ip_adr in data[network_name]:
            infotext += f", interface: {if_name}, attribute: {attribute}, IP: {ip_adr}"

        yield Result(state=State.OK, summary=infotext)


agent_section_aix_hacmp_nodes = AgentSection(
    name="aix_hacmp_nodes", parse_function=parse_aix_hacmp_nodes
)
check_plugin_aix_hacmp_nodes = CheckPlugin(
    name="aix_hacmp_nodes",
    service_name="HACMP Node %s",
    discovery_function=inventory_aix_hacmp_nodes,
    check_function=check_aix_hacmp_nodes,
)
