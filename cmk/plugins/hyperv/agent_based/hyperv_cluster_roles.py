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


hyperv_cluster_roles_default_levels = {
    "states": {
        "active": 0,
        "inactive": 1,
        "Online": 0,
        "Offline": 1,
    }
}


def discovery_hyperv_cluster_roles(section) -> DiscoveryResult:
    for vm in section.keys():
        yield Service(item=vm)


def check_hyperv_cluster_roles(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    vm = section.get(item, "")

    translate_state = {
        "active": "Online",
        "inactive": "Offline",
    }

    if not vm:
        yield Result(state=State(0), summary="VM not found in agent output")
        return

    state = 0
    wanted_result = None
    wanted_states = params.get("match_services")

    if wanted_states:
        for element in wanted_states:
            if element.get("service_name") == item:
                wanted_state = element.get("state")
                wanted_result = translate_state.get(wanted_state)
                break

    vm_state = vm.get("cluster.vm.state")
    if wanted_result:
        if wanted_result == vm_state:
            message = "power state: %s" % vm.get("cluster.vm.state")
            yield Result(state=State(state), summary=message)
        else:
            state = 1
            message = "power state: %s - wanted state: %s" % (
                vm.get("cluster.vm.state"),
                wanted_state,
            )
            yield Result(state=State(state), summary=message)
    else:
        if params.get("states") == "ignore":
            state = 0
        else:
            state = hyperv_cluster_roles_default_levels.get("states", {}).get(
                vm.get("cluster.vm.state"), 3
            )
        message = "power state: %s" % vm.get("cluster.vm.state")
        yield Result(state=State(state), summary=message)

    if vm.get("cluster.vm.owner"):
        if vm.get("cluster.vm.state") == "Online":
            message = "running on %s" % vm.get("cluster.vm.owner")
            yield Result(state=State(0), summary=message)
        else:
            message = "defined on %s" % vm.get("cluster.vm.owner")
            yield Result(state=State(0), summary=message)


agent_section_hyperv_cluster_roles = AgentSection(
    name="hyperv_cluster_roles",
    parse_function=parse_hyperv,
)

check_plugin_hyperv_cluster_roles = CheckPlugin(
    name="hyperv_cluster_roles",
    service_name="HyperV VM %s",
    sections=["hyperv_cluster_roles"],
    discovery_function=discovery_hyperv_cluster_roles,
    check_function=check_hyperv_cluster_roles,
    check_default_parameters=hyperv_cluster_roles_default_levels,
    check_ruleset_name="hyperv_cluster_roles",
)
