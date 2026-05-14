#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.inventory_ui.v1_unstable import (
    Node,
    NumberField,
    SINotation,
    Table,
    TextField,
    Title,
    Unit,
)

UNIT_BITS_PER_SECOND = Unit(SINotation("bits/s"))

node_hardware_nwadapter = Node(
    name="hardware_nwadapter",
    path=["hardware", "nwadapter"],
    title=Title("Network adapters"),
    table=Table(
        columns={
            "name": TextField(Title("Name")),
            "type": TextField(Title("Type")),
            "macaddress": TextField(Title("Physical address (MAC)")),
            "speed": NumberField(Title("Speed"), render=UNIT_BITS_PER_SECOND),
            "gateway": TextField(Title("Gateway")),
            "ipv4_address": TextField(Title("IPv4 address")),
            "ipv6_address": TextField(Title("IPv6 address")),
            "ipv4_subnet": TextField(Title("IPv4 subnet")),
            "ipv6_subnet": TextField(Title("IPv6 subnet")),
        },
    ),
)
