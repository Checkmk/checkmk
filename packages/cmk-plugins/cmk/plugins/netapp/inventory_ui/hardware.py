#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.inventory_ui.v1_unstable import (
    DecimalNotation,
    Node,
    NumberField,
    StrictPrecision,
    Table,
    TextField,
    Title,
    Unit,
)

UNIT_COUNT = Unit(DecimalNotation(""), StrictPrecision(0))

node_hardware_cpu_nodes = Node(
    name="hardware_cpu_nodes",
    path=["hardware", "cpu", "nodes"],
    title=Title("Node processor"),
    table=Table(
        columns={
            "node_name": TextField(Title("Node name")),
            "cores": NumberField(Title("#Cores"), render=UNIT_COUNT),
            "model": TextField(Title("CPU model")),
        },
    ),
)

node_hardware_system_nodes = Node(
    name="hardware_system_nodes",
    path=["hardware", "system", "nodes"],
    title=Title("Node system"),
    table=Table(
        columns={
            "node_name": TextField(Title("Node name")),
            "id": TextField(Title("ID")),
            "model": TextField(Title("Model name")),
            "product": TextField(Title("Product")),
            "serial": TextField(Title("Serial number")),
        },
    ),
)
