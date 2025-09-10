#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.inventory_ui.v1_alpha import (
    DecimalNotation,
    Node,
    NumberField,
    StrictPrecision,
    TextField,
    Title,
    Unit,
)

UNIT_COUNT = Unit(DecimalNotation(""), StrictPrecision(0))

node_networking = Node(
    name="networking",
    path=["networking"],
    title=Title("Networking"),
    attributes={
        "hostname": TextField(Title("Host name")),
        "total_interfaces": NumberField(Title("Total interfaces"), render=UNIT_COUNT),
        "total_ethernet_ports": NumberField(Title("Ports"), render=UNIT_COUNT),
        "available_ethernet_ports": NumberField(Title("Ports available"), render=UNIT_COUNT),
    },
)
