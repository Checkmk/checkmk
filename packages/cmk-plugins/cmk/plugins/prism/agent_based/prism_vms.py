#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

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
from cmk.plugins.prism.lib import load_json, PRISM_POWER_STATES, v4_power_state
from cmk.plugins.prism.v4_models import VmsWithHostNames

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


def parse_prism_vms_v2(string_table: StringTable) -> Section:
    if not string_table:
        return {}
    # Prism doesn't keep VM names unique, the start of the extId tells VMs apart
    return {
        f"{vm.name} ({vm.ext_id[:8]})": {
            "vmName": vm.name,
            "powerState": v4_power_state(vm.power_state),
            "description": vm.description,
            "hostName": vm.host_name,
            "memoryCapacityInBytes": vm.memory_size_bytes,
            "protectionDomainName": None,
        }
        for vm in VmsWithHostNames.model_validate_json(string_table[0][0]).root
    }


agent_section_prism_vms_v2 = AgentSection(
    name="prism_vms_v2",
    parsed_section_name="prism_vms",
    parse_function=parse_prism_vms_v2,
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
    state = 0 if wanted_state == state_text.lower() else state_value

    message = f"with status {state_text} - on Host {host_name}"
    yield Result(state=State(state), summary=message)

    yield Result(state=State.OK, notice=f"Memory {memory}")
    yield Result(state=State.OK, notice=f"Description {vm_desc}")
    if prot_domain is not None:
        yield Result(state=State.OK, notice=f"Protection Domain {prot_domain}")


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
