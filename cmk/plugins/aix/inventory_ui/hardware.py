#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.inventory_ui.v1_unstable import (
    Node,
    Table,
    TextField,
    Title,
)

node_hardware_volumes = Node(
    name="hardware_volumes",
    path=["hardware", "volumes"],
    title=Title("Volumes"),
)

node_hardware_volumes_physical_volumes = Node(
    name="hardware_volumes_physical_volumes",
    path=["hardware", "volumes", "physical_volumes"],
    title=Title("Physical volumes"),
    table=Table(
        columns={
            "volume_group_name": TextField(Title("Volume group name")),
            "physical_volume_name": TextField(Title("Physical volume name")),
            "physical_volume_status": TextField(Title("Physical volume status")),
            "physical_volume_total_partitions": TextField(
                Title("Physical volume total partitions")
            ),
            "physical_volume_free_partitions": TextField(Title("Physical volume free partitions")),
        },
    ),
)
