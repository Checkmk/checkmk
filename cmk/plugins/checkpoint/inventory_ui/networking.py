#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.inventory_ui.v1_unstable import Node, Table, TextField, Title, View

node_networking_tunnels = Node(
    name="networking_tunnels",
    path=["networking", "tunnels"],
    title=Title("Networking tunnels"),
    table=Table(
        view=View(name="invtunnels", title=Title("Networking tunnels")),
        columns={
            "peername": TextField(Title("Peer name")),
            "index": TextField(Title("Index")),
            "peerip": TextField(Title("Peer IP address")),
            "sourceip": TextField(Title("Source IP address")),
            "tunnelinterface": TextField(Title("Tunnel interface")),
            "linkpriority": TextField(Title("Link priority")),
        },
    ),
)
