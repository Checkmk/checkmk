#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.inventory_ui.v1_unstable import Node, Table, TextField, Title

node_networking_wlan = Node(
    name="networking_wlan",
    path=["networking", "wlan"],
    title=Title("WLAN"),
)

node_networking_wlan_controller = Node(
    name="networking_wlan_controller",
    path=["networking", "wlan", "controller"],
    title=Title("Controller"),
)

node_networking_wlan_controller_accesspoints = Node(
    name="networking_wlan_controller_accesspoints",
    path=["networking", "wlan", "controller", "accesspoints"],
    title=Title("Access points"),
    table=Table(
        columns={
            "name": TextField(Title("Name")),
            "group": TextField(Title("Group")),
            "ip_addr": TextField(Title("IP address")),
            "model": TextField(Title("Model")),
            "serial": TextField(Title("Serial number")),
            "sys_location": TextField(Title("System location")),
        },
    ),
)
