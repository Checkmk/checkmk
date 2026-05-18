#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.inventory_ui.v1_unstable import Node, Table, TextField, Title

node_software_applications_vmwareesx = Node(
    name="software_applications_vmwareesx",
    path=["software", "applications", "vmwareesx"],
    title=Title("VMware ESX"),
    table=Table(
        columns={
            "clusters": TextField(Title("Clusters")),
        },
    ),
)
