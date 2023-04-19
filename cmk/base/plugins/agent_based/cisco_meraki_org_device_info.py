#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import asdict, dataclass

from .agent_based_api.v1 import Attributes, register
from .agent_based_api.v1.type_defs import InventoryResult, StringTable
from .utils.cisco_meraki import load_json, MerakiAPIData


@dataclass(frozen=True)
class DeviceInfo:
    name: str
    network_id: str
    serial: str
    model: str
    mac: str
    firmware: str

    @classmethod
    def parse(cls, row: MerakiAPIData) -> "DeviceInfo":
        return cls(
            name=str(row["name"]),
            network_id=str(row["networkId"]),
            serial=str(row["serial"]),
            model=str(row["model"]),
            mac=str(row["mac"]),
            firmware=str(row["firmware"]),
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
            path=["software", "applications", "cisco_meraki"],
            inventory_attributes=asdict(section),
        )


register.inventory_plugin(
    name="cisco_meraki_org_device_info",
    inventory_function=inventory_device_info,
)
