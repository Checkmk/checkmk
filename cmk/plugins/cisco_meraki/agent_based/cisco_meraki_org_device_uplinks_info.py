#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# Original author: thl-cmk[at]outlook[dot]com

import json
from collections.abc import Sequence

from pydantic import BaseModel, Field

from cmk.agent_based.v2 import (
    AgentSection,
    InventoryPlugin,
    InventoryResult,
    StringTable,
    TableRow,
)

type Section = Sequence[Uplink]


class Public(BaseModel, frozen=True):
    address: str | None


class Address(BaseModel, frozen=True):
    address: str
    assignment_mode: str = Field(alias="assignmentMode")
    gateway: str
    protocol: str
    public: Public


class Uplink(BaseModel, frozen=True):
    interface: str
    addresses: list[Address]


class UplinkAddress(BaseModel, frozen=True):
    uplinks: list[Uplink]


def parse_device_uplinks(string_table: StringTable) -> Section:
    match string_table:
        case [[payload]] if payload:
            uplink_address = UplinkAddress.model_validate(json.loads(payload)[0])
            return uplink_address.uplinks
        case _:
            return []


agent_section_cisco_meraki_org_device_uplinks_info = AgentSection(
    name="cisco_meraki_org_device_uplinks_info",
    parse_function=parse_device_uplinks,
)


def inventory_device_uplinks(section: Section) -> InventoryResult:
    for uplink in section:
        if not uplink.interface:
            continue

        for address in uplink.addresses:
            yield TableRow(
                path=["networking", "uplinks"],
                key_columns={
                    "interface": uplink.interface,
                    "protocol": address.protocol,
                    "address": address.address,
                },
                inventory_columns={
                    "assignment_mode": address.assignment_mode,
                    "gateway": address.gateway,
                    "public_address": address.public.address,
                },
            )


inventory_plugin_cisco_meraki_org_device_uplinks_info = InventoryPlugin(
    name="cisco_meraki_org_device_uplinks_info",
    inventory_function=inventory_device_uplinks,
)
