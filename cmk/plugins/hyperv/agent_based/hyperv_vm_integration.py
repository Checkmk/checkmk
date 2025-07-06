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

hyperv_vm_integration_default_levels = {
    "default_status": "active",
    "match_services": [("Guest Service Interface", "inactive")],
}


def discovery_hyperv_vm_integration(section) -> DiscoveryResult:
    if "guest.tools.number" in section:
        yield Service()


def check_hyperv_vm_integration(
    params: Mapping[str, Any], section: Section
) -> CheckResult:
    is_state = {
        "active": 0,
        "inactive": 1,
    }
    for key in section:
        if key.startswith("guest.tools.service"):
            service = key.replace("guest.tools.service.", "").replace("_", " ")
            if service in (item.get("service_name") for item in params["match_services"]):
                serv_params = ""
                for element in params["match_services"]:
                    if element.get("service_name") == service:
                        serv_params = element.get("state")
                        break
                if section[key] == serv_params:
                    yield Result(state=State(0), summary=f"{service} - {section[key]}")

                else:
                    yield Result(state=State(1), summary=f"{service} - {section[key]}")
            else:
                state = is_state.get(section[key], 3)
                yield Result(state=State(state), summary=f"{service} - {section[key]}")


agent_section_hyperv_vm_integration = AgentSection(
    name="hyperv_vm_integration",
    parse_function=hyperv_vm_convert,
)

check_plugin_hyperv_vm_integration = CheckPlugin(
    name="hyperv_vm_integration",
    service_name="HyperV Integration Services",
    sections=["hyperv_vm_integration"],
    discovery_function=discovery_hyperv_vm_integration,
    check_function=check_hyperv_vm_integration,
    check_default_parameters=hyperv_vm_integration_default_levels,
    check_ruleset_name="hyperv_vm_integration",
)
