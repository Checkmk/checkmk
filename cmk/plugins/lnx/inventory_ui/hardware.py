#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.inventory_ui.v1_unstable import (
    IECNotation,
    Node,
    NumberField,
    Table,
    TextField,
    Title,
    Unit,
)

UNIT_BYTES = Unit(IECNotation("B"))

node_hardware_storage = Node(
    name="hardware_storage",
    path=["hardware", "storage"],
    title=Title("Storage"),
)

node_hardware_storage_disks = Node(
    name="hardware_storage_disks",
    path=["hardware", "storage", "disks"],
    title=Title("Block devices"),
    attributes={
        "size": NumberField(Title("Size"), render=UNIT_BYTES),
    },
    table=Table(
        columns={
            "fsnode": TextField(Title("File system node")),
            "controller": TextField(Title("Controller")),
            "signature": TextField(Title("Disk ID")),
            "bus": TextField(Title("Bus")),
            "drive_index": TextField(Title("Drive")),
            "local": TextField(Title("Local")),
            "product": TextField(Title("Product")),
            "serial": TextField(Title("Serial number")),
            "size": NumberField(Title("Size"), render=UNIT_BYTES),
            "type": TextField(Title("Type")),
            "vendor": TextField(Title("Vendor")),
        },
    ),
)

node_hardware_video = Node(
    name="hardware_video",
    path=["hardware", "video"],
    title=Title("Graphic cards"),
    table=Table(
        columns={
            "slot": TextField(Title("Slot")),
            "name": TextField(Title("Graphic card name")),
            "subsystem": TextField(Title("Vendor and device ID")),
            "driver": TextField(Title("Driver")),
            "driver_version": TextField(Title("Driver version")),
            "driver_date": TextField(Title("Driver date")),
            "graphic_memory": NumberField(Title("Memory"), render=UNIT_BYTES),
        },
    ),
)
