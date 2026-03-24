#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
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
    View,
)

_UNIT_BYTES = Unit(IECNotation("B"))

node_hardware_storage_redfish_drives = Node(
    name="hardware_storage_redfish_drives",
    path=["hardware", "storage", "redfish_drives"],
    title=Title("Redfish drives"),
    table=Table(
        view=View(name="invstorageredfishdrives", title=Title("Redfish drives")),
        columns={
            "component": TextField(Title("Component")),
            "manufacturer": TextField(Title("Manufacturer")),
            "model": TextField(Title("Model")),
            "serial": TextField(Title("Serial number")),
            "firmware_version": TextField(Title("Firmware version")),
            "capacity_bytes": NumberField(Title("Capacity"), render=_UNIT_BYTES),
            "media_type": TextField(Title("Media type")),
        },
    ),
)
