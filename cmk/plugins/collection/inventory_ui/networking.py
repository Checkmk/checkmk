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

node_networking_kube = Node(
    name="networking_kube",
    path=["networking", "kube"],
    title=Title("Kubernetes"),
    table=Table(
        columns={
            "ip": TextField(Title("IP address")),
            "address_type": TextField(Title("Type")),
        },
    ),
)
