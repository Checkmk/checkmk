#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.inventory_ui.v1_unstable import Node, TextField, Title

node_software_applications_citrix = Node(
    name="software_applications_citrix",
    path=["software", "applications", "citrix"],
    title=Title("Citrix"),
)

node_software_applications_citrix_controller = Node(
    name="software_applications_citrix_controller",
    path=["software", "applications", "citrix", "controller"],
    title=Title("Controller"),
    attributes={
        "controller_version": TextField(Title("Controller version")),
    },
)

node_software_applications_citrix_vm = Node(
    name="software_applications_citrix_vm",
    path=["software", "applications", "citrix", "vm"],
    title=Title("Virtual machine"),
    attributes={
        "desktop_group_name": TextField(Title("Desktop group name")),
        "catalog": TextField(Title("Catalog")),
        "agent_version": TextField(Title("Agent version")),
    },
)
