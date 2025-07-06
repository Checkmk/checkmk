#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-

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


def discovery_hyperv_vm_nic(section) -> DiscoveryResult:
    for key, values in section.items():
        if "nic.connectionstate" in values:
            yield Service(item=key)


def check_hyperv_vm_nic(item: str, section: Section) -> CheckResult:
    data = section.get(item)

    if not data:
        yield Result(state=State(0), summary="NIC information is missing")
        return

    connection_state = data.get("nic.connectionstate", False)
    vswitch = data.get("nic.vswitch", "no vSwitch")
    vlan_id = data.get("nic.VLAN.id", 0)
    # vlan_mode = data.get("nic.VLAN.mode", "Access")

    if connection_state == "True":
        message = f"{item} connected to {vswitch} with VLAN ID {vlan_id}"
        yield Result(state=State(0), summary=message)
    else:
        message = f"{item} disconnected"
        yield Result(state=State(1), summary=message)


agent_section_hyperv_vm_nic = AgentSection(
    name="hyperv_vm_nic",
    parse_function=parse_hyperv,
)

check_plugin_hyperv_vm_nic = CheckPlugin(
    name="hyperv_vm_nic",
    service_name="HyperV NIC %s",
    sections=["hyperv_vm_nic"],
    discovery_function=discovery_hyperv_vm_nic,
    check_function=check_hyperv_vm_nic,
)
