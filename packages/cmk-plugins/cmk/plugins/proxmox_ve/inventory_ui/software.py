#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.inventory_ui.v1_unstable import Node, TextField, Title

node_software_applications_proxmox_ve = Node(
    name="software_applications_proxmox_ve",
    path=["software", "applications", "proxmox_ve"],
    title=Title("Proxmox"),
)

node_software_applications_proxmox_ve_metadata = Node(
    name="software_applications_proxmox_ve_metadata",
    path=["software", "applications", "proxmox_ve", "metadata"],
    title=Title("Metadata"),
    attributes={
        "object": TextField(Title("Object")),
        "provider": TextField(Title("Provider")),
        "name": TextField(Title("Name")),
        "node": TextField(Title("Node")),
    },
)

node_software_applications_proxmox_ve_cluster = Node(
    name="software_applications_proxmox_ve_cluster",
    path=["software", "applications", "proxmox_ve", "cluster"],
    title=Title("Cluster"),
    attributes={
        "cluster": TextField(Title("Cluster name")),
    },
)
