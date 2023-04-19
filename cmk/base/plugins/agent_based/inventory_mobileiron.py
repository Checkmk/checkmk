#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Optional

from .agent_based_api.v1 import Attributes, register, TableRow
from .agent_based_api.v1.type_defs import InventoryResult
from .utils.mobileiron import Section


def inventory_mobileiron(section: Optional[Section]) -> InventoryResult:

    if section is None:
        return

    yield Attributes(
        path=["hardware", "system"],
        inventory_attributes={
            "model": section.device_model,
            "manufacturer": section.manufacturer,
            "serial": section.serial_number,
        },
    )
    yield TableRow(
        path=["networking", "addresses"],
        key_columns={
            "address": section.ip_address,
            "device": "generic",
        },
        inventory_columns={
            "type": "ipv4",
        },
    )
    yield Attributes(
        path=["software", "os"],
        inventory_attributes={
            "type": section.platform_type,
        },
    )

    yield Attributes(
        path=["software", "applications", "mobileiron"],
        inventory_attributes={
            "registration_state": section.registration_state,
            "partition_name": section.dm_partition_name,
        },
    )


register.inventory_plugin(
    name="mobileiron_inventory",
    sections=["mobileiron_section"],
    inventory_function=inventory_mobileiron,
)
