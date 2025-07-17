#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Thanks to Andreas Döhler for the contribution.

# # -*- encoding: utf-8; py-indent-offset: 4 -*-

from collections.abc import Mapping
from typing import Final

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

Section = dict[str, str]
Params = Mapping[str, list[Section] | str]

hyperv_vm_integration_default_levels: Final[Params] = {
    "default_status": "active",
    "match_services": [{"service_name": "Guest Service Interface", "expected_state": "inactive"}],
}


def discovery_hyperv_vm_integration(section: Section) -> DiscoveryResult:
    if "guest.tools.number" in section:
        yield Service()


def process_service_state(
    section: Section, match_services: dict[str, str], is_state: dict[str, int]
) -> CheckResult:
    for key in section:
        if key.startswith("guest.tools.service"):
            service = key.replace("guest.tools.service.", "").replace("_", " ")
            service_state = section[key]
            if service in match_services:
                expected_state = match_services[service]
                state = State.OK if service_state == expected_state else State.WARN
                yield Result(state=state, summary=f"{service} - {service_state}")
            else:
                state = State(is_state.get(str(service_state), State.UNKNOWN))
                yield Result(state=state, summary=f"{service} - {service_state}")


def check_hyperv_vm_integration(params: Params, section: Section) -> CheckResult:
    is_state = {
        "active": 0,
        "inactive": 1,
    }
    # Build a lookup dict from the list of dicts
    match_services = {
        item["service_name"]: item["expected_state"]
        for item in params.get("match_services", [])
        if isinstance(item, dict)
    }

    yield from process_service_state(section, match_services, is_state)


agent_section_hyperv_vm_integration: AgentSection = AgentSection(
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
