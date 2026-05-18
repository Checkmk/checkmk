#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.inventory_ui.v1_unstable import (
    DecimalNotation,
    IECNotation,
    Node,
    NumberField,
    SINotation,
    StrictPrecision,
    Table,
    TextField,
    Title,
    Unit,
    View,
)

UNIT_BITS_PER_SECOND = Unit(SINotation("bits/s"))
UNIT_BYTES = Unit(IECNotation("B"))
UNIT_COUNT = Unit(DecimalNotation(""), StrictPrecision(0))
UNIT_HZ = Unit(SINotation("Hz"))
UNIT_VOLTAGE = Unit(DecimalNotation("V"))

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

node_hardware_components_sensors = Node(
    name="hardware_components_sensors",
    path=["hardware", "components", "sensors"],
    title=Title("Sensors"),
    table=Table(
        view=View(name="invsensor", title=Title("Sensors")),
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

node_hardware_components_stacks = Node(
    name="hardware_components_stacks",
    path=["hardware", "components", "stacks"],
    title=Title("Stacks"),
    table=Table(
        view=View(name="invstack", title=Title("Stacks")),
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

node_hardware_components_unknowns = Node(
    name="hardware_components_unknowns",
    path=["hardware", "components", "unknowns"],
    title=Title("Unknown entities"),
    table=Table(
        view=View(name="invunknown", title=Title("Unknown entities")),
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

node_hardware_storage_controller = Node(
    name="hardware_storage_controller",
    path=["hardware", "storage", "controller"],
    title=Title("Controller"),
    attributes={
        "version": TextField(Title("Version")),
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
