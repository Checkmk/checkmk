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
from cmk.plugins.hyperv.lib import hyperv_vm_convert

Section = Dict[str, Mapping[str, Any]]


def discovery_hyperv_cluster_general(section) -> DiscoveryResult:
    if section:
        yield Service()


def check_hyperv_cluster_general(section: Section) -> CheckResult:
    if section:
        name = section.get("cluster.name", "")
        quorum = section.get("quorum.resourcename", "")
        ip = section.get("cluster.ip", "")
        quorum_typ = section.get("quorum.type", "")

        message = f"Hyper-V Cluster {name} with IP {ip} and quorum {quorum} as {quorum_typ} quorum."

        yield Result(state=State(0), summary=message)


agent_section_hyperv_cluster_general = AgentSection(
    name="hyperv_cluster_general",
    parse_function=hyperv_vm_convert,
)

check_plugin_hyperv_cluster_general = CheckPlugin(
    name="hyperv_cluster_general",
    service_name="HyperV Cluster Status",
    sections=["hyperv_cluster_general"],
    discovery_function=discovery_hyperv_cluster_general,
    check_function=check_hyperv_cluster_general,
)
