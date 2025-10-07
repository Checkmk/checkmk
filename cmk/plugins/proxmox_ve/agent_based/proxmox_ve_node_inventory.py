#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import Attributes, InventoryPlugin, InventoryResult
from cmk.plugins.proxmox_ve.lib.node_attributes import SectionNodeAttributes


def inventory_proxmox_ve_node(
    section: SectionNodeAttributes,
) -> InventoryResult:
    yield Attributes(
        path=["software", "applications", "proxmox_ve", "metadata"],
        inventory_attributes={
            "object": "Node",
            "provider": "Proxmox VE",
            "name": section.node_name,
        },
    )

    if section.cluster:
        yield Attributes(
            path=["software", "applications", "proxmox_ve", "cluster"],
            inventory_attributes={
                "cluster": section.cluster,
            },
        )


inventory_plugin_proxmox_ve_node = InventoryPlugin(
    name="inventory_proxmox_ve_node",
    sections=["proxmox_ve_node_attributes"],
    inventory_function=inventory_proxmox_ve_node,
)
