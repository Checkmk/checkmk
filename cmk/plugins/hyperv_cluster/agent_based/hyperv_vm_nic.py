#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Thanks to Andreas Döhler for the contribution.

from collections.abc import Mapping

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
)
from cmk.plugins.hyperv_cluster.lib import parse_hyperv

Section = Mapping[str, Mapping[str, str]]


def discovery_hyperv_vm_nic(section: Section) -> DiscoveryResult:
    for key, values in section.items():
        if "nic.connectionstate" in values:
            yield Service(item=key)


def check_hyperv_vm_nic(item: str, section: Section) -> CheckResult:
    data = section.get(item)

    if not data:
        yield Result(state=State.OK, summary="NIC information is missing")
        return

    connection_state = data.get("nic.connectionstate", "False")
    vswitch = data.get("nic.vswitch", "no vSwitch")
    vlan_id = data.get("nic.VLAN.id", "no VLAN ID")

    if connection_state == "True":
        yield Result(
            state=State.OK,
            summary=f"{item} connected to {vswitch} with VLAN ID {vlan_id}",
        )
    else:
        yield Result(
            state=State.WARN,
            summary=f"{item} disconnected",
        )


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
