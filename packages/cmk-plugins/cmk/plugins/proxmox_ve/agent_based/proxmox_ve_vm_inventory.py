#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import Attributes, InventoryPlugin, InventoryResult
from cmk.plugins.proxmox_ve.lib.vm_info import SectionVMInfo


def inventory_proxmox_ve_vm(
    section: SectionVMInfo,
) -> InventoryResult:
    yield Attributes(
        path=["software", "applications", "proxmox_ve", "metadata"],
        inventory_attributes={
            "object": "VM" if section.type == "qemu" else "LXC",
            "provider": "Proxmox VE",
            "name": section.name,
            "node": section.node,
        },
    )


inventory_plugin_proxmox_ve_vm = InventoryPlugin(
    name="inventory_proxmox_ve_vm",
    sections=["proxmox_ve_vm_info"],
    inventory_function=inventory_proxmox_ve_vm,
)
