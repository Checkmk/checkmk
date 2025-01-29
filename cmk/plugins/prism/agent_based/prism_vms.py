#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib.prism import load_json, PRISM_POWER_STATES

Section = Mapping[str, Mapping[str, Any]]


def parse_prism_vms(string_table: StringTable) -> Section:
    parsed: dict[str, dict[str, Any]] = {}
    data = load_json(string_table)
    for element in data.get("entities", {}):
        parsed.setdefault(element.get("vmName", "unknown"), element)
    return parsed


agent_section_prism_vms = AgentSection(
    name="prism_vms",
    parse_function=parse_prism_vms,
)


def discovery_prism_vms(section: Section) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def check_prism_vms(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    wanted_state = params.get("system_state", "on")
    data = section.get(item)
    if not data:
        return

    state_text = data["powerState"]
    state_value = PRISM_POWER_STATES.get(state_text.lower(), 3)
    vm_desc = data["description"]
    if vm_desc:
        vm_desc = vm_desc.replace("\n", r"\n")

    if "template" in str(vm_desc):
        vm_desc = "Template"
        state = 0
    prot_domain = data["protectionDomainName"]
    host_name = data["hostName"]
    memory = render.bytes(data["memoryCapacityInBytes"])
    if wanted_state == state_text.lower():
        state = 0
    else:
        state = state_value

    message = f"with status {state_text} - on Host {host_name}"
    yield Result(state=State(state), summary=message)

    yield Result(
        state=State(0),
        notice=f"Memory {memory},\nDescription {vm_desc},\nProtetion Domain {prot_domain}",
    )


check_plugin_prism_vms = CheckPlugin(
    name="prism_vms",
    service_name="NTNX VM %s",
    sections=["prism_vms"],
    check_default_parameters={
        "system_state": "on",
    },
    discovery_function=discovery_prism_vms,
    check_function=check_prism_vms,
    check_ruleset_name="prism_vms",
)
