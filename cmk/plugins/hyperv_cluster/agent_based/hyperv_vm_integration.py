#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Thanks to Andreas Döhler for the contribution.

# # -*- encoding: utf-8; py-indent-offset: 4 -*-

from typing import Final, Literal, TypedDict

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
)
from cmk.plugins.hyperv_cluster.lib import hyperv_vm_convert

ActivityStatus = Literal["active", "inactive"]


class ServiceSettings(TypedDict):
    default_status: str
    state_if_not_default: int


class ServiceConfig(TypedDict):
    service_name: str
    default_status: ActivityStatus
    state_if_not_default: int


class IntegrationServicesParams(TypedDict):
    default_status: ActivityStatus
    state_if_not_default: int
    match_services: list[ServiceConfig]


Section = dict[str, str | int]

hyperv_vm_integration_default_levels: Final[IntegrationServicesParams] = {
    "default_status": "active",
    "state_if_not_default": State.WARN.value,
    "match_services": [
        {
            "service_name": "Guest Service Interface",
            "default_status": "inactive",
            "state_if_not_default": State.OK.value,
        }
    ],
}


def discovery_hyperv_vm_integration(section: Section) -> DiscoveryResult:
    if "guest.tools.number" in section:
        yield Service()


def process_service_status(
    section: Section,
    match_services: dict[str, ServiceSettings],
    global_default_status: str,
    global_state_if_not_default: int,
) -> CheckResult:
    for key in section:
        if key.startswith("guest.tools.service"):
            service = key.replace("guest.tools.service.", "").replace("_", " ")
            if "VSS" in service:
                service = "VSS (Volume Shadow Copy Service)"
            service_status = section[key]

            if service in match_services:
                # Use service-specific configuration
                service_settings = match_services[service]
                default_status = service_settings["default_status"]
                state_if_not_default = service_settings["state_if_not_default"]
            else:
                # Use global configuration for unmatched services
                default_status = global_default_status
                state_if_not_default = global_state_if_not_default

            if service_status == default_status:
                state = State.OK
            elif service_status in ["active", "inactive"]:
                # Valid state but not expected - use state_if_not_default
                state = State(state_if_not_default)
            else:
                # Invalid/unknown state - always return UNKNOWN
                state = State.UNKNOWN

            yield Result(state=state, summary=f"{service}: {service_status}")


def check_hyperv_vm_integration(params: IntegrationServicesParams, section: Section) -> CheckResult:
    global_default_status = str(params["default_status"])
    global_state_if_not_default = int(params["state_if_not_default"])

    match_services: dict[str, ServiceSettings] = {}

    for item in hyperv_vm_integration_default_levels.get("match_services", []):
        service_name = item["service_name"]
        default_status = item["default_status"]
        state_if_not_default = item["state_if_not_default"]

        match_services[service_name] = ServiceSettings(
            default_status=default_status, state_if_not_default=state_if_not_default
        )

    match_services_param = params.get("match_services", [])
    if isinstance(match_services_param, list):
        for item in match_services_param:
            if isinstance(item, dict):
                service_name = item["service_name"]
                default_status = item["default_status"]
                state_if_not_default = item["state_if_not_default"]

                match_services[service_name] = ServiceSettings(
                    default_status=default_status, state_if_not_default=state_if_not_default
                )

    yield from process_service_status(
        section, match_services, global_default_status, global_state_if_not_default
    )


agent_section_hyperv_vm_integration: AgentSection = AgentSection(
    name="hyperv_vm_integration",
    parse_function=hyperv_vm_convert,
)

check_plugin_hyperv_vm_integration = CheckPlugin(
    name="hyperv_vm_integration",
    service_name="Hyper-V VM integration services",
    sections=["hyperv_vm_integration"],
    discovery_function=discovery_hyperv_vm_integration,
    check_function=check_hyperv_vm_integration,
    check_default_parameters=hyperv_vm_integration_default_levels,
    check_ruleset_name="hyperv_vm_integration",
)
