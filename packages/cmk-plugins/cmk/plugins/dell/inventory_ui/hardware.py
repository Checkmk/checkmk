#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.inventory_ui.v1_unstable import Node, TextField, Title

node_hardware_storage_controller = Node(
    name="hardware_storage_controller",
    path=["hardware", "storage", "controller"],
    title=Title("Controller"),
    attributes={
        "version": TextField(Title("Version")),
    },
)
