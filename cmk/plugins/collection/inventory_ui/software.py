#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.inventory_ui.v1_alpha import Node, Title

node_software = Node(
    name="software",
    path=["software"],
    title=Title("Software"),
)

node_software_applications = Node(
    name="software_applications",
    path=["software", "applications"],
    title=Title("Applications"),
)

node_software_applications_azure = Node(
    name="software_applications_azure",
    path=["software", "applications", "azure"],
    title=Title("Azure"),
)

node_software_applications_azure_application_gateways = Node(
    name="software_applications_azure_application_gateways",
    path=["software", "applications", "azure", "application_gateways"],
    title=Title("Application gateways"),
)

node_software_applications_azure_application_gateways_rules = Node(
    name="software_applications_azure_application_gateways_rules",
    path=["software", "applications", "azure", "application_gateways", "rules"],
    title=Title("Rules"),
)
