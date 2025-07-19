#!/usr/bin/python
# # -*- encoding: utf-8; py-indent-offset: 4 -*-

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


def discovery_hyperv_cluster_disks(section) -> DiscoveryResult:
    for disk in section.keys():
        yield Service(item=disk)


def check_hyperv_cluster_disks(item: str, section) -> CheckResult:

    disk = section.get(item, "")

    if not disk:
        yield Result(state=State(3), summary="Disk not found in agent output")
        return

    state = 0
    if disk["cluster.disk.state"] != "Online":
        state = 3
    message = "is %s, with owner %s and group %s." % (
        disk["cluster.disk.state"],
        disk["cluster.disk.owner_node"],
        disk["cluster.disk.owner_group"],
    )
    yield Result(state=State(state), summary=message)


agent_section_hyperv_cluster_disks = AgentSection(
    name="hyperv_cluster_disks",
    parse_function=parse_hyperv,
)

check_plugin_hyperv_cluster_disks = CheckPlugin(
    name="hyperv_cluster_disks",
    service_name="HyperV Disk %s",
    sections=["hyperv_cluster_disks"],
    discovery_function=discovery_hyperv_cluster_disks,
    check_function=check_hyperv_cluster_disks,
)
