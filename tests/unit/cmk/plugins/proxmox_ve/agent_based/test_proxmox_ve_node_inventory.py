#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Attributes
from cmk.plugins.proxmox_ve.agent_based.proxmox_ve_node_inventory import inventory_proxmox_ve_node
from cmk.plugins.proxmox_ve.lib.node_attributes import SectionNodeAttributes

SECTION_NODE_ATTRIBUTES = SectionNodeAttributes(
    cluster="pve-cluster",
    node_name="pve-dc4-001",
)


def test_inventory_proxmox_ve_node() -> None:
    assert list(inventory_proxmox_ve_node(section=SECTION_NODE_ATTRIBUTES)) == [
        Attributes(
            path=["software", "applications", "proxmox_ve", "metadata"],
            inventory_attributes={
                "object": "Node",
                "provider": "Proxmox VE",
                "name": "pve-dc4-001",
            },
            status_attributes={},
        ),
        Attributes(
            path=["software", "applications", "proxmox_ve", "cluster"],
            inventory_attributes={"cluster": "pve-cluster"},
            status_attributes={},
        ),
    ]
