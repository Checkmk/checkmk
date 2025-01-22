#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Redfish firmware inventory for HPE devices"""

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    InventoryPlugin,
    InventoryResult,
    Result,
    Service,
    State,
    TableRow,
)
from cmk.plugins.redfish.lib import (
    parse_redfish_multiple,
    redfish_health_state,
    RedfishAPIData,
)

agent_section_redfish_firmware = AgentSection(
    name="redfish_firmwareinventory",
    parse_function=parse_redfish_multiple,
    parsed_section_name="redfish_firmware",
)


def _item_name(item_data, padding):
    """build item name for inventory entry"""
    if not item_data.get("Id"):
        if item_data.get("Name"):
            item_name = item_data.get("Name")
        else:
            return None
    elif item_data.get("Id").isdigit():
        item_name = f"{item_data.get('Id').zfill(padding)}-{item_data.get('Name')}"
    elif item_data.get("Id") == item_data.get("Name"):
        item_name = item_data.get("Name")
    elif item_data.get("Description") == "Represents Firmware Inventory":
        prefix = item_data.get("Id").split("-")[0]
        item_name = f"{prefix}-{item_data.get('Name')}"
    else:
        item_name = f"{item_data.get('Id')}-{item_data.get('Name')}"
    return item_name


def inventory_redfish_firmware(section: RedfishAPIData) -> InventoryResult:
    """create inventory table for firmware"""
    path = ["hardware", "firmware", "redfish"]
    if section.get("FirmwareInventory", {}).get("Current"):
        data = section.get("FirmwareInventory", {}).get("Current")
        padding = len(str(len(data)))
        for index, entry_id in enumerate(data):
            entry = data.get(entry_id)
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
    else:
        padding = len(str(len(section)))
        for _key, entry in section.items():
            item_name = _item_name(entry, padding)
            if not item_name:
                continue
            if entry.get("Description") == "Represents Firmware Inventory":
                description = entry.get("Id")
            else:
                description = entry.get("Description")
            yield TableRow(
                path=path,
                key_columns={
                    "component": item_name,
                },
                inventory_columns={
                    "version": entry.get("Version"),
                    "description": description,
                    "updateable": entry.get("Updateable"),
                },
            )


inventory_plugin_redfish_firmware = InventoryPlugin(
    name="redfish_firmware",
    inventory_function=inventory_redfish_firmware,
)


def discovery_redfish_firmware(section: RedfishAPIData) -> DiscoveryResult:
    """discover service if data exists"""
    if section:
        yield Service()


# TODO: this outputs html
# TODO: for manpage: which agents generate this?
def check_redfish_firmware(section: RedfishAPIData) -> CheckResult:
    """check the health state of the firmware"""

    padding = len(str(len(section)))
    overall_state = 0
    msg_text = ""
    info_text = ""
    info_list = []
    for _key, entry in section.items():
        if not entry.get("Status"):
            continue
        component_name = _item_name(entry, padding)
        comp_state, comp_msg = redfish_health_state(entry.get("Status", {}))
        if entry.get("Status", {}).get("State", "UNKNOWN") == "StandbyOffline":
            comp_state = 0
        overall_state = max(overall_state, comp_state)
        if comp_state != 0:
            msg_text += f"{component_name} - {comp_msg} - "
        info_list.append([component_name, comp_msg, entry.get("Version"), entry.get("Updateable")])

    if not msg_text:
        msg_text = "All firmware in optimal state"

    line_bracket = "<tr>%s</tr>"
    cell_bracket = "<td>%s</td>"
    cell_seperator = ""
    headers = ("Component", "Status", "Version", "Updateable")
    info_text = f'<table style="border-collapse: separate; border-spacing: 10px 0;">{(
        "<tr><th>"
        + "</th><th>".join(headers)
        + "</th></tr>"
        + "".join(
            [
                line_bracket
                % cell_seperator.join([cell_bracket % value for value in info_entry])
                for info_entry in info_list
            ]
        )
    )}</table>'

    yield Result(state=State(overall_state), summary=msg_text, details=info_text)


check_plugin_redfish_firmware = CheckPlugin(
    name="redfish_firmware",
    service_name="Firmware health",
    sections=["redfish_firmware"],
    discovery_function=discovery_redfish_firmware,
    check_function=check_redfish_firmware,
)
