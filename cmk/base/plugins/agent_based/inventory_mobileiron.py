#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

from .agent_based_api.v1 import Attributes, register
from .agent_based_api.v1.type_defs import InventoryResult
from .utils.mobileiron import Section


def inventory_mobileiron(section: Section) -> InventoryResult:

    yield Attributes(
        path=["hardware", "system"],
        inventory_attributes={
            "Model Name": section.deviceModel,
            "Manufacturer": section.manufacturer,
            "Serial number": section.serialNumber,
        },
    )
    yield Attributes(
        path=["networking", "addresses"],
        inventory_attributes={
            "address": section.ipAddress,
        },
    )
    yield Attributes(
        path=["software", "os"],
        inventory_attributes={
            "Type": section.platformType,
        },
    )
    total_capacity = section.totalCapacity * 1024 * 1024 * 1024 if section.totalCapacity else None
    yield Attributes(
        path=["hardware", "storage", "disks"],
        inventory_attributes={"size": total_capacity},
    )
    yield Attributes(
        path=["software", "applications", "mobileiron"],
        inventory_attributes={
            "Registration state": section.registrationState,
            "Partition name": section.dmPartitionName,
        },
    )


register.inventory_plugin(
    name="mobileiron_inventory",
    sections=["mobileiron_section"],
    inventory_function=inventory_mobileiron,
)
