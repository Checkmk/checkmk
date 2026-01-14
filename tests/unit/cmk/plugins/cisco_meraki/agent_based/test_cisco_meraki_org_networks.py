#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest
from polyfactory.factories import TypedDictFactory

from cmk.agent_based.v2 import StringTable, TableRow
from cmk.plugins.cisco_meraki.agent_based.cisco_meraki_org_networks import (
    inventory_meraki_networks,
    parse_meraki_networks,
)
from cmk.plugins.cisco_meraki.lib.schema import Network


class _NetworkFactory(TypedDictFactory[Network]):
    __check_model__ = False


def test_inventorize_device_info() -> None:
    device = _NetworkFactory.build(id="netid-123")
    string_table = [[f"[{json.dumps({device['id']: device})}]"]]
    section = parse_meraki_networks(string_table)

    row = next(row for row in inventory_meraki_networks(section) if isinstance(row, TableRow))

    assert not row.status_columns
    assert row.key_columns == {"network_id": "netid-123"}
    assert row.path == ["software", "applications", "cisco_meraki", "networks"]

    expected_inventory_columns = {
        "enrollment_string",
        "is_bound_to_template",
        "network_name",
        "notes",
        "organization_id",
        "organization_name",
        "product_types",
        "tags",
        "time_zone",
        "url",
    }

    assert set(row.inventory_columns.keys()) == expected_inventory_columns


@pytest.mark.parametrize("string_table ", [[], [[]], [[""]]])
def test_inventorize_device_info_no_payload(string_table: StringTable) -> None:
    section = parse_meraki_networks(string_table)
    assert not list(inventory_meraki_networks(section))
