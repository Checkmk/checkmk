#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.base.plugins.agent_based import cisco_meraki_org_device_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable

from .utils_inventory import sort_inventory_result

_STRING_TABLE = [
    [
        (
            '[{"name": "My AP", "lat": 37.4180951010362, "lng": -122.098531723022,'
            '"address": "1600 Pennsylvania Ave", "notes": "My AP\'s note",'
            '"tags": " recently-added ", "networkId": "N_24329156", "serial": "Q234-ABCD-5678",'
            '"model": "MR34", "mac": "00:11:22:33:44:55", "lanIp": "1.2.3.4",'
            '"firmware": "wireless-25-14", "organisation_id": "123", "organisation_name": "org-name"}]'
        ),
    ]
]


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        ([], []),
        ([[]], []),
        ([[""]], []),
        (
            _STRING_TABLE,
            [
                Attributes(
                    path=["software", "applications", "cisco_meraki"],
                    inventory_attributes={
                        "name": "My AP",
                        "network_id": "N_24329156",
                        "serial": "Q234-ABCD-5678",
                        "model": "MR34",
                        "mac": "00:11:22:33:44:55",
                        "firmware": "wireless-25-14",
                        "address": "1600 Pennsylvania Ave",
                        "product_type": "",
                        "organisation_id": "123",
                        "organisation_name": "org-name",
                    },
                )
            ],
        ),
    ],
)
def test_inventory_device_info(
    string_table: StringTable, expected_result: Sequence[Attributes]
) -> None:
    section = cisco_meraki_org_device_info.parse_device_info(string_table)
    assert sort_inventory_result(
        cisco_meraki_org_device_info.inventory_device_info(section)
    ) == sort_inventory_result(expected_result)
