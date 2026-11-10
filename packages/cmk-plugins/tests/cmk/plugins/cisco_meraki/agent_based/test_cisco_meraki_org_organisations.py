#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest
from polyfactory.factories import TypedDictFactory

from cmk.agent_based.v2 import StringTable, TableRow
from cmk.plugins.cisco_meraki.agent_based.cisco_meraki_org_organisations import (
    inventorize_meraki_organizations,
    parse_meraki_organizations,
)
from cmk.plugins.cisco_meraki.lib.schema import RawOrganisation


class _RawOrganisationFactory(TypedDictFactory[RawOrganisation]):
    __check_model__ = False


def test_inventory_organisations() -> None:
    org = _RawOrganisationFactory.build(
        id="123",
        name="Name1",
        url="http://example.com",
        api={"enabled": True},
        licensing={"model": "co-term"},
        cloud={"region": {"name": "North America"}},
    )
    string_table = [[f"[{json.dumps(org)}]"]]
    section = parse_meraki_organizations(string_table)

    row = next(
        row for row in inventorize_meraki_organizations(section) if isinstance(row, TableRow)
    )

    assert row.key_columns == {"org_id": "123"}
    assert row.path == ["software", "applications", "cisco_meraki", "organisations"]
    assert row.inventory_columns == {
        "org_name": "Name1",
        "url": "http://example.com",
        "api_status": "enabled",
        "licensing_model": "co-term",
        "cloud_region": "North America",
    }


def test_inventory_organisations_disabled_api() -> None:
    org = _RawOrganisationFactory.build(api={"enabled": False})
    string_table = [[f"[{json.dumps(org)}]"]]
    section = parse_meraki_organizations(string_table)

    row = next(
        row for row in inventorize_meraki_organizations(section) if isinstance(row, TableRow)
    )

    assert row.inventory_columns["api_status"] == "disabled"


@pytest.mark.parametrize("string_table ", [[], [[]], [[""]]])
def test_inventorize_device_info_no_payload(string_table: StringTable) -> None:
    section = parse_meraki_organizations(string_table)
    assert not list(inventorize_meraki_organizations(section))
