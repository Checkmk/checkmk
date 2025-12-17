#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

from pydantic import BaseModel, Field

from cmk.agent_based.v2 import (
    AgentSection,
    Attributes,
    HostLabel,
    HostLabelGenerator,
    InventoryPlugin,
    InventoryResult,
    StringTable,
)

type Section = DeviceInfo


class DeviceInfo(BaseModel, frozen=True):
    serial: str
    model: str
    firmware: str
    organisation_id: str
    organisation_name: str
    address: str
    description: str = Field(alias="name")
    mac_address: str = Field(alias="mac")
    network_id: str = Field(alias="networkId")
    network_name: str = Field(alias="networkName")
    product: str = Field(default="", alias="productType")


def host_label_meraki_device_info(section: Section) -> HostLabelGenerator:
    """Host label function

    Labels:
        cmk/meraki:
            This label is set to "yes" for all Meraki devices

        cmk/meraki/device_type:
            This label is set to the Meraki product type to which the device belongs, such as "switch" or "wireless".

        cmk/meraki/net_id:
            This label is set to the network id the Meraki device belongs to.

        cmk/meraki/net_name:
            This label is set to the network name the Meraki device belongs to.

        cmk/meraki/org_id:
            This label is set to the organisation id the Meraki device belongs to.

        cmk/meraki/org_name:
            This label is set to the organisation name the Meraki device belongs to.
    """
    yield HostLabel("cmk/meraki", "yes")
    yield HostLabel("cmk/meraki/device_type", section.product)
    yield HostLabel("cmk/meraki/net_id", section.network_id)
    yield HostLabel("cmk/meraki/net_name", section.network_name)
    yield HostLabel("cmk/meraki/org_id", section.organisation_id)
    yield HostLabel("cmk/meraki/org_name", section.organisation_name)


def parse_device_info(string_table: StringTable) -> Section | None:
    match string_table:
        case [[payload]] if payload:
            return DeviceInfo.model_validate(json.loads(payload)[0])
        case _:
            return None


agent_section_cisco_meraki_org_device_info = AgentSection(
    name="cisco_meraki_org_device_info",
    parse_function=parse_device_info,
    host_label_function=host_label_meraki_device_info,
)


def inventory_device_info(section: Section) -> InventoryResult:
    yield Attributes(
        path=["hardware", "system"],
        inventory_attributes={
            "product": section.product,
            "serial": section.serial,
            "model": section.model,
            "description": section.description,
            "mac_address": section.mac_address,
            "manufacturer": "Cisco Meraki",
        },
    )
    yield Attributes(
        path=["software", "firmware"],
        inventory_attributes={
            "version": section.firmware,
        },
    )
    yield Attributes(
        path=["software", "configuration", "organisation"],
        inventory_attributes={
            "organisation_id": section.organisation_id,
            "organisation_name": section.organisation_name,
            "network_id": section.network_id,
            "network_name": section.network_name,
            "address": section.address,
        },
    )


inventory_plugin_cisco_meraki_org_device_info = InventoryPlugin(
    name="cisco_meraki_org_device_info",
    inventory_function=inventory_device_info,
)
