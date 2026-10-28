#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.inventory_ui.v1 import Node, Table, TextField, Title, View

node_software_applications_aws = Node(
    name="software_applications_aws",
    path=["software", "applications", "aws"],
    title=Title("AWS"),
)

node_software_applications_aws_metadata = Node(
    name="software_applications_aws_metadata",
    path=["software", "applications", "aws", "metadata"],
    title=Title("Metadata"),
    attributes={
        "cloud_provider": TextField(Title("Cloud provider")),
        "entity": TextField(Title("Entity")),
        "name": TextField(Title("Name")),
        "service": TextField(Title("AWS service")),
        "resource_id": TextField(Title("Resource ID")),
        "account_id": TextField(Title("Account ID")),
        "account_name": TextField(Title("Account name")),
        "region": TextField(Title("Region")),
    },
)

node_software_applications_aws_tags = Node(
    name="software_applications_aws_tags",
    path=["software", "applications", "aws", "tags"],
    title=Title("Tags"),
    table=Table(
        view=View(name="invawstags", title=Title("AWS tags")),
        columns={
            "name": TextField(Title("Name")),
            "value": TextField(Title("Value")),
        },
    ),
)
