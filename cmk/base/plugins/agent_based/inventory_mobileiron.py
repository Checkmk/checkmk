#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Optional

from cmk.base.plugins.agent_based.utils.df import BlocksSubsection, InodesSubsection

from .agent_based_api.v1 import Attributes, register
from .agent_based_api.v1.type_defs import InventoryResult
from .utils.mobileiron import Section


def inventory_mobileiron(
    section_mobileiron_section: Optional[Section],
    section_df: Optional[tuple[BlocksSubsection, InodesSubsection]],
) -> InventoryResult:

    if section_mobileiron_section is None:
        return

    yield Attributes(
        path=["hardware", "system"],
        inventory_attributes={
            "model": section_mobileiron_section.device_model,
            "manufacturer": section_mobileiron_section.manufacturer,
            "serial": section_mobileiron_section.serial_number,
        },
    )
    yield Attributes(
        path=["networking", "addresses"],
        inventory_attributes={
            "address": section_mobileiron_section.ip_address,
        },
    )
    yield Attributes(
        path=["software", "os"],
        inventory_attributes={
            "type": section_mobileiron_section.platform_type,
        },
    )

    yield Attributes(
        path=["software", "applications", "mobileiron"],
        inventory_attributes={
            "registration_state": section_mobileiron_section.registration_state,
            "partition_name": section_mobileiron_section.dm_partition_name,
        },
    )

    if section_df is not None:
        total_capacity = (
            total_capacity * 1024 * 1024 if (total_capacity := section_df[0][0].size_mb) else None
        )
        yield Attributes(
            path=["hardware", "storage", "disks"],
            inventory_attributes={"size": total_capacity},
        )


register.inventory_plugin(
    name="mobileiron_inventory",
    sections=["mobileiron_section", "df"],
    inventory_function=inventory_mobileiron,
)
