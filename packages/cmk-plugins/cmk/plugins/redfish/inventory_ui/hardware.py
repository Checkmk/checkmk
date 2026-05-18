#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.inventory_ui.v1_unstable import (
    BoolField,
    Node,
    Table,
    TextField,
    Title,
    View,
)

node_hardware_firmware = Node(
    name="hardware_firmware",
    path=["hardware", "firmware"],
    title=Title("Firmware"),
)

node_hardware_firmware_redfish = Node(
    name="hardware_firmware_redfish",
    path=["hardware", "firmware", "redfish"],
    title=Title("Redfish"),
    table=Table(
        view=View(name="invfirmwareredfish", title=Title("Redfish")),
        columns={
            "component": TextField(Title("Component")),
            "version": TextField(Title("Version")),
            "location": TextField(Title("Location")),
            "description": TextField(Title("Description")),
            "updateable": BoolField(Title("Update possible")),
        },
    ),
)
