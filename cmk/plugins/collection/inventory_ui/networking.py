#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.inventory_ui.v1_unstable import (
    Node,
    Table,
    TextField,
    Title,
    View,
)

node_networking_kube = Node(
    name="networking_kube",
    path=["networking", "kube"],
    title=Title("Kubernetes"),
    table=Table(
        columns={
            "ip": TextField(Title("IP address")),
            "address_type": TextField(Title("Type")),
        },
    ),
)


node_networking_device_uplinks = Node(
    name="networking_device_uplinks",
    path=["networking", "uplinks"],
    title=Title("Device uplinks"),
    table=Table(
        view=View(name="invdeviceuplinks", title=Title("Device uplinks")),
        columns={
            "interface": TextField(Title("Interface")),
            "protocol": TextField(Title("Protocol")),
            "address": TextField(Title("Address")),
            "gateway": TextField(Title("Gateway")),
            "public_address": TextField(Title("Public address")),
            "assignment_mode": TextField(Title("Assignment mode")),
        },
    ),
)
