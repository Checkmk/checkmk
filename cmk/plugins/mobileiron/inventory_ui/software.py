#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.inventory_ui.v1_unstable import Node, TextField, Title

node_software_applications_mobileiron = Node(
    name="software_applications_mobileiron",
    path=["software", "applications", "mobileiron"],
    title=Title("Mobileiron"),
    attributes={
        "partition_name": TextField(Title("Partition name")),
        "registration_state": TextField(Title("Registration state")),
    },
)
