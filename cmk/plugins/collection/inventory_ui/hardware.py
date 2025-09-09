#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.inventory_ui.v1_alpha import IECNotation, Node, NumberField, Title, Unit

UNIT_BYTES = Unit(IECNotation("B"))

node_hardware = Node(
    name="hardware",
    path=["hardware"],
    title=Title("Hardware"),
)

node_hardware_memory = Node(
    name="hardware_memory",
    path=["hardware", "memory"],
    title=Title("Memory (RAM)"),
    attributes={
        "total_ram_usable": NumberField(Title("Total usable RAM"), render=UNIT_BYTES),
        "total_swap": NumberField(Title("Total swap space"), render=UNIT_BYTES),
        "total_vmalloc": NumberField(Title("Virtual addresses for mapping"), render=UNIT_BYTES),
    },
)
