#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.inventory_ui.v1_unstable import Node, Table, TextField, Title

node_networking_sip_interfaces = Node(
    name="networking_sip_interfaces",
    path=["networking", "sip_interfaces"],
    title=Title("SIP interfaces"),
    table=Table(
        columns={
            "index": TextField(Title("Index")),
            "name": TextField(Title("Name")),
            "application_type": TextField(Title("Application type")),
            "sys_interface": TextField(Title("System interface")),
            "device": TextField(Title("Device")),
            "tcp_port": TextField(Title("TCP Port")),
            "gateway": TextField(Title("Gateway")),
        },
    ),
)
