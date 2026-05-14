#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.inventory_ui.v1_unstable import Node, Table, TextField, Title

node_software_os_service_packs = Node(
    name="software_os_service_packs",
    path=["software", "os", "service_packs"],
    title=Title("Service packs"),
    table=Table(
        columns={
            "name": TextField(Title("Name")),
        },
    ),
)
