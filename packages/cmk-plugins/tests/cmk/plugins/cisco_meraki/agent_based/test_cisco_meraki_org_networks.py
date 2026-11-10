#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest
from polyfactory.factories import TypedDictFactory

from cmk.agent_based.v2 import StringTable, TableRow
from cmk.plugins.cisco_meraki.agent_based.cisco_meraki_org_networks import (
    inventorize_meraki_networks,
    parse_meraki_networks,
)
from cmk.plugins.cisco_meraki.lib.schema import Network


class _NetworkFactory(TypedDictFactory[Network]):
    __check_model__ = False


def test_parsed_networks_count_with_multiple_orgs_and_single_network() -> None:
    networks = [
        {"netid-123": _NetworkFactory.build(id="netid-123", organizationId="123")},
        {"netid-456": _NetworkFactory.build(id="netid-456", organizationId="456")},
    ]
    string_table = [[json.dumps(networks)]]

    value = len(parse_meraki_networks(string_table))
    expected = 2

    assert value == expected


def test_parsed_networks_count_with_orgs_with_multiple_networks() -> None:
    networks = [
        {
            "netid-123-a": _NetworkFactory.build(id="netid-123-a", organizationId="123"),
            "netid-123-b": _NetworkFactory.build(id="netid-123-b", organizationId="123"),
        },
        {
            "netid-456-a": _NetworkFactory.build(id="netid-456-a", organizationId="456"),
            "netid-456-b": _NetworkFactory.build(id="netid-456-b", organizationId="456"),
        },
    ]
    string_table = [[json.dumps(networks)]]

    value = len(parse_meraki_networks(string_table))
    expected = 4

    assert value == expected


def test_parsing_validation_works_with_known_optional_fields() -> None:
    networks = [{"id": _NetworkFactory.build(id="id", notes=None, enrollmentString=None)}]
    string_table = [[json.dumps(networks)]]
    assert parse_meraki_networks(string_table)


def test_inventorize_meraki_networks() -> None:
    device = _NetworkFactory.build(id="netid-123")
    string_table = [[f"[{json.dumps({device['id']: device})}]"]]
    section = parse_meraki_networks(string_table)

    row = next(row for row in inventorize_meraki_networks(section) if isinstance(row, TableRow))

    assert not row.status_columns
    assert row.key_columns == {"network_id": "netid-123"}
    assert row.path == ["software", "applications", "cisco_meraki", "networks"]

    expected_inventory_columns = {
        "enrollment_string",
        "is_bound_to_template",
        "network_name",
        "notes",
        "org_id",
        "org_name",
        "product_types",
        "tags",
        "time_zone",
        "url",
    }

    assert set(row.inventory_columns.keys()) == expected_inventory_columns


@pytest.mark.parametrize("string_table ", [[], [[]], [[""]]])
def test_inventorize_meraki_networks_no_payload(string_table: StringTable) -> None:
    section = parse_meraki_networks(string_table)
    assert not list(inventorize_meraki_networks(section))
