#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest
from polyfactory.factories import TypedDictFactory

from cmk.agent_based.v2 import StringTable, TableRow
from cmk.plugins.cisco_meraki.agent_based.cisco_meraki_org_device_uplinks_info import (
    inventory_device_uplinks,
    parse_device_uplinks,
)
from cmk.plugins.cisco_meraki.lib.schema import RawDeviceUplinksAddress


class _RawDeviceUplinksAddressFactory(TypedDictFactory[RawDeviceUplinksAddress]):
    __check_model__ = False


def test_inventory_device_uplinks_info() -> None:
    uplink_address = _RawDeviceUplinksAddressFactory.build()
    string_table = [[f"[{json.dumps(uplink_address)}]"]]
    section = parse_device_uplinks(string_table)

    row = next(row for row in inventory_device_uplinks(section) if isinstance(row, TableRow))

    assert not row.status_columns
    assert row.path == [
        "networking",
        "uplinks",
    ]
    assert set(row.key_columns) == {
        "interface",
        "protocol",
        "address",
    }
    assert set(row.inventory_columns) == {
        "assignment_mode",
        "gateway",
        "public_address",
    }


@pytest.mark.parametrize("string_table ", [[], [[]], [[""]]])
def test_inventory_device_uplinks_info_no_payload(string_table: StringTable) -> None:
    section = parse_device_uplinks(string_table)
    assert not list(inventory_device_uplinks(section))
