#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.inventory_ui.v1_unstable import (
    Node,
    TextField,
    Title,
)

node_software_applications_azure_metadata = Node(
    name="software_applications_azure_metadata",
    path=["software", "applications", "azure", "metadata"],
    title=Title("Metadata"),
    attributes={
        "object": TextField(Title("Object")),
        "name": TextField(Title("Name")),
        "entity": TextField(Title("Entity")),
        "resource_group": TextField(Title("Resource group")),
        "subscription_id": TextField(Title("Subscription ID")),
        "subscription_name": TextField(Title("Subscription name")),
        "region": TextField(Title("Region")),
        "tenant_id": TextField(Title("Tenant ID")),
        "tenant_name": TextField(Title("Tenant Name")),
    },
)
