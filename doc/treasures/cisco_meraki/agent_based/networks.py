#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# Original author: thl-cmk[at]outlook[dot]com

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

from cmk.agent_based.v2 import (
    AgentSection,
    InventoryPlugin,
    InventoryResult,
    StringTable,
    TableRow,
)
from cmk_addons.plugins.meraki.lib.utils import MerakiAPIData, MerakiNetwork, load_json


_API_NAME_ORGANISATION_NAME: Final = "name"


_is_bounf_to_template = {
    True: 'yes',
    False: 'no',
}


@dataclass(frozen=True)
class NetworkInfo(MerakiNetwork):
    enrollment_string: str | None
    id: str
    is_bound_to_config_template: bool
    name: str
    notes: str
    organisation_id: str
    organisation_name: str
    product_types: Sequence[str]
    tags: Sequence[str]
    time_zone: str
    url: str

    @classmethod
    def parse(cls, organisations: MerakiAPIData):
        networks = []
        for organisation in organisations:
            for network in organisation:
                networks += [network]
        return [cls(
            enrollment_string=network.get('enrollmentString', None),
            id=network['id'],
            is_bound_to_config_template=network['isBoundToConfigTemplate'],
            name=network['name'],
            notes=network['notes'],
            organisation_id=network['organizationId'],
            organisation_name=network['organizationName'],
            product_types=network['productTypes'],
            tags=network['tags'],
            time_zone=network['timeZone'],
            url=network['url'],
        ) for network in networks]


def parse_meraki_networks(string_table: StringTable) -> Sequence[NetworkInfo] | None:
    return NetworkInfo.parse(loaded_json) if (loaded_json := load_json(string_table)) else None


agent_section_cisco_meraki_org_networks = AgentSection(
    name="cisco_meraki_org_networks",
    parse_function=parse_meraki_networks,
)


def inventory_meraki_networks(section: Sequence[NetworkInfo] | None) -> InventoryResult:
    for network in section:
        inventory_columns = {
            'is_bound_to_template': _is_bounf_to_template[network.is_bound_to_config_template],
            'network_name': network.name,
            'organisation_id': network.organisation_id,
            'product_types': ', '.join(m.title() for m in network.product_types),
            'time_zone': network.time_zone,
            'url': network.url,
            'organisation_name': network.organisation_name
        }
        if network.notes:
            inventory_columns['notes'] = network.notes
        if network.enrollment_string:
            inventory_columns['enrollment_string'] = network.enrollment_string
        if network.tags:
            inventory_columns['tags'] = ', '.join(network.tags)

        yield TableRow(
            path=['software', 'applications', 'cisco_meraki', 'networks'],
            key_columns={'network_id': network.id},
            inventory_columns=inventory_columns,
        )


inventory_plugin_cisco_meraki_org_networks = InventoryPlugin(
    name="cisco_meraki_org_networks",
    inventory_function=inventory_meraki_networks,
)
