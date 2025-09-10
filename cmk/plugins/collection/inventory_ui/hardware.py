#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.inventory_ui.v1_alpha import (
    IECNotation,
    Node,
    NumberField,
    Table,
    TextField,
    Title,
    Unit,
    View,
)

UNIT_BYTES = Unit(IECNotation("B"))

node_hardware = Node(
    name="hardware",
    path=["hardware"],
    title=Title("Hardware"),
)

node_hardware_chassis = Node(
    name="hardware_chassis",
    path=["hardware", "chassis"],
    title=Title("Chassis"),
)

node_hardware_components = Node(
    name="hardware_components",
    path=["hardware", "components"],
    title=Title("Physical components"),
)

node_hardware_components_backplanes = Node(
    name="hardware_components_backplanes",
    path=["hardware", "components", "backplanes"],
    title=Title("Backplanes"),
    table=Table(
        view=View(name="invbackplane", title=Title("Backplanes")),
        columns={
            "index": TextField(Title("Index")),
            "name": TextField(Title("Name")),
            "description": TextField(Title("Description")),
            "software": TextField(Title("Software")),
            "serial": TextField(Title("Serial number")),
            "manufacturer": TextField(Title("Manufacturer")),
            "model": TextField(Title("Model name")),
            "location": TextField(Title("Location")),
        },
    ),
)

node_hardware_components_chassis = Node(
    name="hardware_components_chassis",
    path=["hardware", "components", "chassis"],
    title=Title("Chassis"),
    table=Table(
        view=View(name="invchassis", title=Title("Chassis")),
        columns={
            "index": TextField(Title("Index")),
            "name": TextField(Title("Name")),
            "description": TextField(Title("Description")),
            "software": TextField(Title("Software")),
            "serial": TextField(Title("Serial number")),
            "manufacturer": TextField(Title("Manufacturer")),
            "model": TextField(Title("Model name")),
            "location": TextField(Title("Location")),
        },
    ),
)

node_hardware_components_containers = Node(
    name="hardware_components_containers",
    path=["hardware", "components", "containers"],
    title=Title("HW containers"),
    table=Table(
        view=View(name="invcontainer", title=Title("HW containers")),
        columns={
            "index": TextField(Title("Index")),
            "name": TextField(Title("Name")),
            "description": TextField(Title("Description")),
            "software": TextField(Title("Software")),
            "serial": TextField(Title("Serial number")),
            "manufacturer": TextField(Title("Manufacturer")),
            "model": TextField(Title("Model name")),
            "location": TextField(Title("Location")),
        },
    ),
)

node_hardware_components_fans = Node(
    name="hardware_components_fans",
    path=["hardware", "components", "fans"],
    title=Title("Fans"),
    table=Table(
        view=View(name="invfan", title=Title("Fans")),
        columns={
            "index": TextField(Title("Index")),
            "name": TextField(Title("Name")),
            "description": TextField(Title("Description")),
            "software": TextField(Title("Software")),
            "serial": TextField(Title("Serial number")),
            "manufacturer": TextField(Title("Manufacturer")),
            "model": TextField(Title("Model name")),
            "location": TextField(Title("Location")),
        },
    ),
)

node_hardware_components_modules = Node(
    name="hardware_components_modules",
    path=["hardware", "components", "modules"],
    title=Title("Modules"),
    table=Table(
        view=View(name="invmodule", title=Title("Modules")),
        columns={
            "index": TextField(Title("Index")),
            "name": TextField(Title("Name")),
            "description": TextField(Title("Description")),
            "software": TextField(Title("Software")),
            "serial": TextField(Title("Serial number")),
            "model": TextField(Title("Model name")),
            "manufacturer": TextField(Title("Manufacturer")),
            "bootloader": TextField(Title("Bootloader")),
            "firmware": TextField(Title("Firmware")),
            "type": TextField(Title("Type")),
            "location": TextField(Title("Location")),
            "ha_status": TextField(Title("HA status")),
            "software_version": TextField(Title("Software version")),
            "license_key_list": TextField(Title("License key list")),
        },
    ),
)

node_hardware_components_others = Node(
    name="hardware_components_others",
    path=["hardware", "components", "others"],
    title=Title("Other entities"),
    table=Table(
        view=View(name="invother", title=Title("Other entities")),
        columns={
            "index": TextField(Title("Index")),
            "name": TextField(Title("Name")),
            "description": TextField(Title("Description")),
            "software": TextField(Title("Software")),
            "serial": TextField(Title("Serial number")),
            "manufacturer": TextField(Title("Manufacturer")),
            "model": TextField(Title("Model name")),
            "location": TextField(Title("Location")),
        },
    ),
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
