#!/usr/bin/python
# # -*- encoding: utf-8; py-indent-offset: 4 -*-

from collections.abc import Mapping
from typing import Any, Dict

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
)
from cmk.plugins.hyperv.lib import parse_hyperv

Section = Dict[str, Mapping[str, Any]]


def discovery_hyperv_cluster_nodes(section) -> DiscoveryResult:
    for node in section.keys():
        yield Service(item=node)


def check_hyperv_cluster_nodes(item: str, section: Section) -> CheckResult:

    node = section.get(item, "")

    if not node:
        yield Result(state=State(3), summary="Node not found in agent output")

    state = 0
    if node["cluster.node.state"] != "Up":
        state = 3
    message = f"is {node['cluster.node.state']}, has ID {node['cluster.node.id']} and weight {node['cluster.node.weight']}."
    yield Result(state=State(state), summary=message)


agent_section_hyperv_cluster_nodes = AgentSection(
    name="hyperv_cluster_nodes",
    parse_function=parse_hyperv,
)

check_plugin_hyperv_cluster_nodes = CheckPlugin(
    name="hyperv_cluster_nodes",
    service_name="HyperV Node %s",
    sections=["hyperv_cluster_nodes"],
    discovery_function=discovery_hyperv_cluster_nodes,
    check_function=check_hyperv_cluster_nodes,
)
