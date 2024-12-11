#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Redfish firmware inventory for HPE devices"""

from cmk.agent_based.v2 import (
    AgentSection,
    InventoryPlugin,
    InventoryResult,
    TableRow,
)
from cmk.plugins.redfish.lib import (
    parse_redfish,
    RedfishAPIData,
)

agent_section_redfish_firmware_hpe_ilo4 = AgentSection(
    name="redfish_firmware_hpe_ilo4",
    parse_function=parse_redfish,
    parsed_section_name="redfish_firmware_hpe_ilo4",
)


def inventory_redfish_firmware_hpe_ilo4(section: RedfishAPIData) -> InventoryResult:
    """create inventory table for firmware"""
    path = ["hardware", "firmware", "redfish"]
    padding = len(str(len(section)))
    for index, entry_id in enumerate(section):
        entry = section[entry_id]
        component_name = f"{str(index).zfill(padding)}-{entry[0].get('Name')}"
        yield TableRow(
            path=path,
            key_columns={
                "component": component_name,
            },
            inventory_columns={
                "version": entry[0].get("VersionString"),
                "location": entry[0].get("Location"),
            },
        )


inventory_plugin_redfish_firmware_hpe_ilo4 = InventoryPlugin(
    name="redfish_firmware_hpe_ilo4",
    inventory_function=inventory_redfish_firmware_hpe_ilo4,
)
