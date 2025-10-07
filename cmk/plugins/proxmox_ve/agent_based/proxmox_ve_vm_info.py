#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    HostLabel,
    HostLabelGenerator,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib.uptime import check as check_uptime_seconds
from cmk.plugins.lib.uptime import Section as UptimeSection
from cmk.plugins.proxmox_ve.lib.vm_info import SectionVMInfo


def parse_proxmox_ve_vm_info(string_table: StringTable) -> SectionVMInfo:
    return SectionVMInfo.model_validate_json(string_table[0][0])


def host_label_function(section: SectionVMInfo) -> HostLabelGenerator:
    """
    Generate Proxmox VE VM host labels.
    Labels:
        cmk/pve/entity:<entity_type>:
            Shows that the object type is VM. It can be VM (qemu) or LXC (lxc).
        cmk/pve/node:<node_name>:
            The node of the Proxmox VE VM.
    """
    yield HostLabel("cmk/pve/entity", "vm" if section.type == "qemu" else "LXC")
    yield HostLabel("cmk/pve/node", section.node)


def discover_single(section: SectionVMInfo) -> DiscoveryResult:
    yield Service()


def check_proxmox_ve_vm_info(params: Mapping[str, Any], section: SectionVMInfo) -> CheckResult:
    yield Result(state=State.OK, summary=f"VM ID: {section.vmid}")

    vm_status = section.status.lower() if section.status else "n/a"
    req_vm_status = (params.get("required_vm_status") or "").lower()
    yield Result(
        state=State.OK if not req_vm_status or vm_status == req_vm_status else State.WARN,
        summary=f"Status: {vm_status}%s" % (req_vm_status and f" (required: {req_vm_status})"),
    )

    yield Result(state=State.OK, summary=f"Type: {section.type}, Host: {section.node}")

    yield from check_uptime_seconds(
        params={},
        section=UptimeSection(uptime_sec=section.uptime, message=None),
    )

    yield Result(
        state=State.OK if not section.lock else State.CRIT,
        notice=f"Config lock: {section.lock or 'none'}",
    )


agent_section_proxmox_ve_vm_info = AgentSection(
    name="proxmox_ve_vm_info",
    parse_function=parse_proxmox_ve_vm_info,
    host_label_function=host_label_function,
)

check_plugin_proxmox_ve_vm_info = CheckPlugin(
    name="proxmox_ve_vm_info",
    service_name="Proxmox VE VM Info",
    discovery_function=discover_single,
    check_function=check_proxmox_ve_vm_info,
    check_ruleset_name="proxmox_ve_vm_info",
    check_default_parameters={
        "required_vm_status": "",
    },
)
