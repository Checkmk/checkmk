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

node_software_applications_checkmk_agent = Node(
    name="software_applications_checkmk_agent",
    path=["software", "applications", "checkmk-agent"],
    title=Title("Checkmk agent"),
    attributes={
        "version": TextField(Title("Version")),
        "agentdirectory": TextField(Title("Agent directory")),
        "datadirectory": TextField(Title("Data directory")),
        "spooldirectory": TextField(Title("Spool directory")),
        "pluginsdirectory": TextField(Title("Plug-ins directory")),
        "localdirectory": TextField(Title("Local directory")),
        "agentcontroller": TextField(Title("Agent Controller")),
    },
)

node_software_applications_checkmk_agent_plugins = Node(
    name="software_applications_checkmk_agent_plugins",
    path=["software", "applications", "checkmk-agent", "plugins"],
    title=Title("Agent plug-ins"),
    table=Table(
        columns={
            "name": TextField(Title("Name")),
            "version": TextField(Title("Version")),
            "cache_interval": TextField(Title("Cache interval")),
        },
    ),
)


node_software_applications_checkmk_agent_local_checks = Node(
    name="software_applications_checkmk_agent_local_checks",
    path=["software", "applications", "checkmk-agent", "local_checks"],
    title=Title("Local checks"),
    table=Table(
        columns={
            "name": TextField(Title("Name")),
            "version": TextField(Title("Version")),
            "cache_interval": TextField(Title("Cache interval")),
        },
    ),
)
