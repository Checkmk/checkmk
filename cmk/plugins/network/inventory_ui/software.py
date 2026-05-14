#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.inventory_ui.v1_unstable import Node, TextField, Title

node_software_configuration = Node(
    name="software_configuration",
    path=["software", "configuration"],
    title=Title("Configuration"),
)

node_software_configuration_snmp_info = Node(
    name="software_configuration_snmp_info",
    path=["software", "configuration", "snmp_info"],
    title=Title("SNMP information"),
    attributes={
        "contact": TextField(Title("Contact")),
        "location": TextField(Title("Location")),
        "name": TextField(Title("System name")),
    },
)

node_software_firmware = Node(
    name="software_firmware",
    path=["software", "firmware"],
    title=Title("Firmware"),
    attributes={
        "vendor": TextField(Title("Vendor")),
        "version": TextField(Title("Version")),
        "platform_level": TextField(Title("Platform firmware level")),
    },
)
