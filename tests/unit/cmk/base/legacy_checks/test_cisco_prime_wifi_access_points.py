#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.legacy_checks.cisco_prime_wifi_access_points import (
    check_cisco_prime_wifi_access_points,
    discover_cisco_prime_wifi_access_points,
    parse_cisco_prime_wifi_access_points,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                [
                    '{ "queryResponse": {  "entity": [   {    "@dtoType": "accessPointsDTO",    "@type": "AccessPoints",    "@url": "https://hello.world.de/webacs/api/v1/data/AccessPoints/2101795",    "accessPointsDTO": {     "@displayName": "2101795",     "@id": "2101795",     "adminStatus": "ENABLE",     "clientCount": 0,     "clientCount_2_4GHz": 0,     "clientCount_5GHz": 0,     "controllerName": "wism22",     "countryCode": "DE",     "hreapEnabled": false,     "location": "default location",     "lwappUpTime": 70343302,     "model": "AIR-LAP1131AG-E-K9",     "softwareVersion": "8.0.152.12",     "status": "CLEARED",     "type": "AP1130",     "upTime": 125852602    }   },   {    "@dtoType": "accessPointsDTO",    "@type": "AccessPoints",    "@url": "https://hello.world.de/webacs/api/v1/data/AccessPoints/40164274",    "accessPointsDTO": {     "@displayName": "40164274",     "@id": "40164274",     "adminStatus": "ENABLE",     "clientCount": 0,     "clientCount_2_4GHz": 0,     "clientCount_5GHz": 0,     "controllerName": "wism21",     "countryCode": "DE",     "hreapEnabled": false,     "lwappUpTime": 126151608,     "model": "AIR-LAP1131AG-E-K9",     "serialNumber": "FCZ1046Q143",     "softwareVersion": "8.0.152.12",     "status": "CLEARED",     "type": "AP1130",     "upTime": 126158708    }   },   {    "@dtoType": "accessPointsDTO",    "@type": "AccessPoints",    "@url": "https://hello.world.de/webacs/api/v1/data/AccessPoints/40164277",    "accessPointsDTO": {     "@displayName": "40164277",     "@id": "40164277",     "adminStatus": "ENABLE",     "bootVersion": "12.3.2.4",     "clientCount": 0,     "clientCount_2_4GHz": 0,     "clientCount_5GHz": 0,     "countryCode": "DE",     "hreapEnabled": false,     "lwappUpTime": 3638416300,     "model": "AIR-LAP1231G-E-K9    ",     "softwareVersion": "7.0.252.0",     "status": "CRITICAL",     "type": "AP1200",     "upTime": 941477604    }   },   {    "@dtoType": "accessPointsDTO",    "@type": "AccessPoints",    "@url": "https://hello.world.de/webacs/api/v1/data/AccessPoints/59467791",    "accessPointsDTO": {     "@displayName": "59467791",     "@id": "59467791",     "adminStatus": "ENABLE",     "bootVersion": "1.2.3.4",     "clientCount": 4,     "clientCount_2_4GHz": 3,     "clientCount_5GHz": 1,     "controllerName": "wism22",     "countryCode": "DE",     "hreapEnabled": false,     "location": "Daheim",     "lwappUpTime": 70336104,     "model": "AIR-LAP1242AG-E-K9",     "softwareVersion": "8.0.152.12",     "status": "CLEARED",     "type": "AP1240",     "upTime": 125766504    }   }  ] }}'
                ]
            ],
            [(None, {})],
        ),
    ],
)
def test_discover_cisco_prime_wifi_access_points(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str | None, Mapping[str, Any]]]
) -> None:
    """Test discovery function for cisco_prime_wifi_access_points check."""
    parsed = parse_cisco_prime_wifi_access_points(string_table)
    result = list(discover_cisco_prime_wifi_access_points(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            None,
            {},
            [
                [
                    '{ "queryResponse": {  "entity": [   {    "@dtoType": "accessPointsDTO",    "@type": "AccessPoints",    "@url": "https://hello.world.de/webacs/api/v1/data/AccessPoints/2101795",    "accessPointsDTO": {     "@displayName": "2101795",     "@id": "2101795",     "adminStatus": "ENABLE",     "clientCount": 0,     "clientCount_2_4GHz": 0,     "clientCount_5GHz": 0,     "controllerName": "wism22",     "countryCode": "DE",     "hreapEnabled": false,     "location": "default location",     "lwappUpTime": 70343302,     "model": "AIR-LAP1131AG-E-K9",     "softwareVersion": "8.0.152.12",     "status": "CLEARED",     "type": "AP1130",     "upTime": 125852602    }   },   {    "@dtoType": "accessPointsDTO",    "@type": "AccessPoints",    "@url": "https://hello.world.de/webacs/api/v1/data/AccessPoints/40164274",    "accessPointsDTO": {     "@displayName": "40164274",     "@id": "40164274",     "adminStatus": "ENABLE",     "clientCount": 0,     "clientCount_2_4GHz": 0,     "clientCount_5GHz": 0,     "controllerName": "wism21",     "countryCode": "DE",     "hreapEnabled": false,     "lwappUpTime": 126151608,     "model": "AIR-LAP1131AG-E-K9",     "serialNumber": "FCZ1046Q143",     "softwareVersion": "8.0.152.12",     "status": "CLEARED",     "type": "AP1130",     "upTime": 126158708    }   },   {    "@dtoType": "accessPointsDTO",    "@type": "AccessPoints",    "@url": "https://hello.world.de/webacs/api/v1/data/AccessPoints/40164277",    "accessPointsDTO": {     "@displayName": "40164277",     "@id": "40164277",     "adminStatus": "ENABLE",     "bootVersion": "12.3.2.4",     "clientCount": 0,     "clientCount_2_4GHz": 0,     "clientCount_5GHz": 0,     "countryCode": "DE",     "hreapEnabled": false,     "lwappUpTime": 3638416300,     "model": "AIR-LAP1231G-E-K9    ",     "softwareVersion": "7.0.252.0",     "status": "CRITICAL",     "type": "AP1200",     "upTime": 941477604    }   },   {    "@dtoType": "accessPointsDTO",    "@type": "AccessPoints",    "@url": "https://hello.world.de/webacs/api/v1/data/AccessPoints/59467791",    "accessPointsDTO": {     "@displayName": "59467791",     "@id": "59467791",     "adminStatus": "ENABLE",     "bootVersion": "1.2.3.4",     "clientCount": 4,     "clientCount_2_4GHz": 3,     "clientCount_5GHz": 1,     "controllerName": "wism22",     "countryCode": "DE",     "hreapEnabled": false,     "location": "Daheim",     "lwappUpTime": 70336104,     "model": "AIR-LAP1242AG-E-K9",     "softwareVersion": "8.0.152.12",     "status": "CLEARED",     "type": "AP1240",     "upTime": 125766504    }   }  ] }}'
                ]
            ],
            [
                (
                    0,
                    "Percent Critical: 25.00%",
                    [("ap_devices_percent_unhealthy", 25.0, None, None)],
                ),
                (0, "Cleared: 3", [("ap_devices_cleared", 3)]),
                (0, "Critical: 1", [("ap_devices_critical", 1)]),
            ],
        ),
        (
            None,
            {"levels": (20, 40)},
            [
                [
                    '{ "queryResponse": {  "entity": [   {    "@dtoType": "accessPointsDTO",    "@type": "AccessPoints",    "@url": "https://hello.world.de/webacs/api/v1/data/AccessPoints/2101795",    "accessPointsDTO": {     "@displayName": "2101795",     "@id": "2101795",     "adminStatus": "ENABLE",     "clientCount": 0,     "clientCount_2_4GHz": 0,     "clientCount_5GHz": 0,     "controllerName": "wism22",     "countryCode": "DE",     "hreapEnabled": false,     "location": "default location",     "lwappUpTime": 70343302,     "model": "AIR-LAP1131AG-E-K9",     "softwareVersion": "8.0.152.12",     "status": "CLEARED",     "type": "AP1130",     "upTime": 125852602    }   },   {    "@dtoType": "accessPointsDTO",    "@type": "AccessPoints",    "@url": "https://hello.world.de/webacs/api/v1/data/AccessPoints/40164274",    "accessPointsDTO": {     "@displayName": "40164274",     "@id": "40164274",     "adminStatus": "ENABLE",     "clientCount": 0,     "clientCount_2_4GHz": 0,     "clientCount_5GHz": 0,     "controllerName": "wism21",     "countryCode": "DE",     "hreapEnabled": false,     "lwappUpTime": 126151608,     "model": "AIR-LAP1131AG-E-K9",     "serialNumber": "FCZ1046Q143",     "softwareVersion": "8.0.152.12",     "status": "CLEARED",     "type": "AP1130",     "upTime": 126158708    }   },   {    "@dtoType": "accessPointsDTO",    "@type": "AccessPoints",    "@url": "https://hello.world.de/webacs/api/v1/data/AccessPoints/40164277",    "accessPointsDTO": {     "@displayName": "40164277",     "@id": "40164277",     "adminStatus": "ENABLE",     "bootVersion": "12.3.2.4",     "clientCount": 0,     "clientCount_2_4GHz": 0,     "clientCount_5GHz": 0,     "countryCode": "DE",     "hreapEnabled": false,     "lwappUpTime": 3638416300,     "model": "AIR-LAP1231G-E-K9    ",     "softwareVersion": "7.0.252.0",     "status": "CRITICAL",     "type": "AP1200",     "upTime": 941477604    }   },   {    "@dtoType": "accessPointsDTO",    "@type": "AccessPoints",    "@url": "https://hello.world.de/webacs/api/v1/data/AccessPoints/59467791",    "accessPointsDTO": {     "@displayName": "59467791",     "@id": "59467791",     "adminStatus": "ENABLE",     "bootVersion": "1.2.3.4",     "clientCount": 4,     "clientCount_2_4GHz": 3,     "clientCount_5GHz": 1,     "controllerName": "wism22",     "countryCode": "DE",     "hreapEnabled": false,     "location": "Daheim",     "lwappUpTime": 70336104,     "model": "AIR-LAP1242AG-E-K9",     "softwareVersion": "8.0.152.12",     "status": "CLEARED",     "type": "AP1240",     "upTime": 125766504    }   }  ] }}'
                ]
            ],
            [
                (
                    1,
                    "Percent Critical: 25.00% (warn/crit at 20.00%/40.00%)",
                    [("ap_devices_percent_unhealthy", 25.0, 20, 40)],
                ),
                (0, "Cleared: 3", [("ap_devices_cleared", 3)]),
                (0, "Critical: 1", [("ap_devices_critical", 1)]),
            ],
        ),
    ],
)
def test_check_cisco_prime_wifi_access_points(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for cisco_prime_wifi_access_points check."""
    parsed = parse_cisco_prime_wifi_access_points(string_table)
    result = list(check_cisco_prime_wifi_access_points(item, params, parsed))
    assert result == expected_results
