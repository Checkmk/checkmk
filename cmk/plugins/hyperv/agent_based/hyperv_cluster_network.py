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


def discovery_hyperv_cluster_network(section) -> DiscoveryResult:
    for network in section.keys():
        yield Service(item=network)


def check_hyperv_cluster_network(item: str, section: Section) -> CheckResult:

    network = section.get(item, "")

    if not network:
        yield Result(state=State(3), summary="Network not found in agent output")

    state = 0
    if network["cluster.network.state"] != "Up":
        state = 3
    message = f"is {network['cluster.network.state']}, has address {network['cluster.network.ip']} and role {network['cluster.network.role']}."
    yield Result(state=State(state), summary=message)


agent_section_hyperv_cluster_network = AgentSection(
    name="hyperv_cluster_network",
    parse_function=parse_hyperv,
)

check_plugin_hyperv_cluster_network = CheckPlugin(
    name="hyperv_cluster_network",
    service_name="HyperV Network %s",
    sections=["hyperv_cluster_network"],
    discovery_function=discovery_hyperv_cluster_network,
    check_function=check_hyperv_cluster_network,
)
