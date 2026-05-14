#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.inventory_ui.v1_unstable import Node, Table, TextField, Title

node_software_applications_fortinet = Node(
    name="software_applications_fortinet",
    path=["software", "applications", "fortinet"],
    title=Title("Fortinet"),
)

node_software_applications_fortinet_fortigate_high_availability = Node(
    name="software_applications_fortinet_fortigate_high_availability",
    path=["software", "applications", "fortinet", "fortigate_high_availability"],
    title=Title("FortiGate HighAvailability"),
)

node_software_applications_fortinet_fortisandbox = Node(
    name="software_applications_fortinet_fortisandbox",
    path=["software", "applications", "fortinet", "fortisandbox"],
    title=Title("FortiSandbox software"),
    table=Table(
        columns={
            "name": TextField(Title("Name")),
            "version": TextField(Title("Version")),
        },
    ),
)
