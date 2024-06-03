#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
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
from cmk.plugins.lib.threepar import parse_3par


@dataclass
class ThreeParSystem:
    name: str | None
    serial_number: str
    model: str
    system_version: str
    cluster_nodes: Sequence[int]
    online_nodes: Sequence[int]


def parse_threepar_system(string_table: StringTable) -> ThreeParSystem:
    pre_parsed = parse_3par(string_table)

    return ThreeParSystem(
        name=pre_parsed.get("name"),
        serial_number=pre_parsed.get("serialNumber", "N/A"),
        model=pre_parsed.get("model", "N/A"),
        system_version=pre_parsed.get("systemVersion", "N/A"),
        cluster_nodes=pre_parsed.get("clusterNodes", []),
        online_nodes=pre_parsed.get("onlineNodes", []),
    )


agent_section_3par_system = AgentSection(
    name="3par_system",
    parse_function=parse_threepar_system,
)


def discover_threepar_system(section: ThreeParSystem) -> DiscoveryResult:
    if section.name:
        yield Service(item=section.name)


def check_threepar_system(item: str, section: ThreeParSystem) -> CheckResult:
    yield Result(
        state=State.OK,
        summary=f"Model: {section.model}, Version: {section.system_version}, Serial number: {section.serial_number}, Online nodes: {len(section.online_nodes)}/{len(section.cluster_nodes)}",
    )

    if len(section.online_nodes) < len(section.cluster_nodes):
        for node in set(section.cluster_nodes) ^ set(section.online_nodes):
            yield Result(state=State.CRIT, summary=f"(Node {node} not available)")


check_plugin_3par_system = CheckPlugin(
    name="3par_system",
    check_function=check_threepar_system,
    discovery_function=discover_threepar_system,
    service_name="3PAR %s",
)
