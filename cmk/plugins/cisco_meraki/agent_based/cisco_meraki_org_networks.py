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

type Section = Sequence[Network]


class Network(BaseModel, frozen=True):
    id: str
    name: str
    organization_id: str = Field(alias="organizationId")
    organization_name: str = Field(alias="organizationName")
    product_types: list[str] = Field(alias="productTypes")
    time_zone: str = Field(alias="timeZone")
    tags: list[str]
    enrollment_string: str | None = Field(alias="enrollmentString")
    url: str
    notes: str
    is_bound_to_config_template: bool = Field(alias="isBoundToConfigTemplate")


def parse_meraki_networks(string_table: StringTable) -> Section:
    match string_table:
        case [[payload]] if payload:
            network_map = json.loads(payload)[0]
            return [Network.model_validate(data) for data in network_map.values()]
        case _:
            return []


agent_section_cisco_meraki_org_networks = AgentSection(
    name="cisco_meraki_org_networks",
    parse_function=parse_meraki_networks,
)


def inventory_meraki_networks(section: Section) -> InventoryResult:
    for network in section:
        inventory_columns = {
            "is_bound_to_template": "yes" if network.is_bound_to_config_template else "no",
            "network_name": network.name,
            "organization_id": network.organization_id,
            "organization_name": network.organization_name,
            "product_types": ", ".join(m.title() for m in network.product_types),
            "time_zone": network.time_zone,
            "url": network.url,
        }
        if network.notes:
            inventory_columns["notes"] = network.notes
        if network.enrollment_string:
            inventory_columns["enrollment_string"] = network.enrollment_string
        if network.tags:
            inventory_columns["tags"] = ", ".join(network.tags)

        yield TableRow(
            path=["software", "applications", "cisco_meraki", "networks"],
            key_columns={"network_id": network.id},
            inventory_columns=inventory_columns,
        )


inventory_plugin_cisco_meraki_org_networks = InventoryPlugin(
    name="cisco_meraki_org_networks",
    inventory_function=inventory_meraki_networks,
)
