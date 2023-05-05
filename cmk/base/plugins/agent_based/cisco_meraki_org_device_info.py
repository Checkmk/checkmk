#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass

from .agent_based_api.v1 import Attributes, register
from .agent_based_api.v1.type_defs import InventoryResult, StringTable
from .utils.cisco_meraki import load_json, MerakiAPIData


@dataclass(frozen=True)
class DeviceInfo:
    product: str
    serial: str
    model: str
    description: str
    mac_address: str
    firmware: str
    organisation_id: str
    organisation_name: str
    network_id: str
    address: str

    @classmethod
    def parse(cls, row: MerakiAPIData) -> "DeviceInfo":
        return cls(
            # Some entries may missing in older API versions
            product=str(row.get("productType", "")),
            serial=str(row["serial"]),
            model=str(row["model"]),
            description=str(row["name"]),
            network_id=str(row["networkId"]),
            mac_address=str(row["mac"]),
            firmware=str(row["firmware"]),
            address=str(row["address"]),
            organisation_id=str(row["organisation_id"]),
            organisation_name=str(row["organisation_name"]),
        )


def parse_device_info(string_table: StringTable) -> DeviceInfo | None:
    return DeviceInfo.parse(loaded_json[0]) if (loaded_json := load_json(string_table)) else None


register.agent_section(
    name="cisco_meraki_org_device_info",
    parse_function=parse_device_info,
)


def inventory_device_info(section: DeviceInfo | None) -> InventoryResult:
    if section:
        yield Attributes(
            path=["hardware", "system"],
            inventory_attributes={
                "product": section.product,
                "serial": section.serial,
                "model": section.model,
                "description": section.description,
                "mac_address": section.mac_address,
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
                "address": section.address,
            },
        )


register.inventory_plugin(
    name="cisco_meraki_org_device_info",
    inventory_function=inventory_device_info,
)
