#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.inventory_ui.v1_unstable import (
    Node,
    Table,
    TextField,
    Title,
    View,
)

node_hardware_components = Node(
    name="hardware_components",
    path=["hardware", "components"],
    title=Title("Physical components"),
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

node_hardware_components_psus = Node(
    name="hardware_components_psus",
    path=["hardware", "components", "psus"],
    title=Title("Power supplies"),
    table=Table(
        view=View(name="invpsu", title=Title("Power supplies")),
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
