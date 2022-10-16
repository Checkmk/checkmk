#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# (c) Andreas Doehler <andreas.doehler@bechtle.com/andreas.doehler@gmail.com>
# This is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
import ast
from typing import Any, Dict, Mapping

from .agent_based_api.v1 import register, render, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.prism import PRISM_POWER_STATES

Section = Dict[str, Mapping[str, Any]]


def parse_prism_vms(string_table: StringTable) -> Section:
    parsed: Section = {}
    data = ast.literal_eval(string_table[0][0])
    for element in data.get("entities"):
        parsed.setdefault(element.get("vmName", "unknown"), element)
    return parsed


register.agent_section(
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
        notice=f"Memory {memory}," f"\nDescription {vm_desc}," f"\nProtetion Domain {prot_domain}",
    )


register.check_plugin(
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
