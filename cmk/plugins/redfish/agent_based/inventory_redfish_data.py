#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Redfish storage drives inventory plugin.

Extracts hardware component data from Redfish drive sections to build
a consolidated inventory view of physical drives.
"""

from cmk.agent_based.v2 import (
    InventoryPlugin,
    InventoryResult,
    TableRow,
)
from cmk.plugins.redfish.lib import RedfishAPIData


def _extract_component_name(entry: RedfishAPIData) -> str:
    """Build a component name from entry data."""
    entry_id = str(entry.get("Id", ""))
    name = str(entry.get("Name", ""))
    if entry_id and name and entry_id != name:
        return f"{entry_id}-{name}"
    return name or entry_id or "Unknown"


def inventorize_redfish_drives(section: RedfishAPIData) -> InventoryResult:
    """Create inventory entries from Redfish drive data."""
    for _key, entry in section.items():
        if not isinstance(entry, dict):
            continue
        component_name = _extract_component_name(entry)

        inventory_columns: dict[str, int | float | str | bool | None] = {}
        if manufacturer := entry.get("Manufacturer"):
            inventory_columns["manufacturer"] = manufacturer
        if model := entry.get("Model"):
            inventory_columns["model"] = model
        if serial := entry.get("SerialNumber"):
            inventory_columns["serial"] = serial
        if firmware := entry.get("FirmwareVersion"):
            inventory_columns["firmware_version"] = firmware
        if capacity := entry.get("CapacityBytes"):
            inventory_columns["capacity_bytes"] = capacity
        if media_type := entry.get("MediaType"):
            inventory_columns["media_type"] = media_type

        if not inventory_columns:
            continue

        yield TableRow(
            path=["hardware", "storage", "redfish_drives"],
            key_columns={"component": component_name},
            inventory_columns=inventory_columns,
        )


inventory_plugin_redfish_storage_inventory = InventoryPlugin(
    name="redfish_storage_inventory",
    sections=["redfish_drives"],
    inventory_function=inventorize_redfish_drives,
)
