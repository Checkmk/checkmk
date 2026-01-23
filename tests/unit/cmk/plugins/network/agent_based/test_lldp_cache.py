#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import (
    Attributes,
    HostLabel,
    InventoryResult,
    StringByteTable,
    TableRow,
)
from cmk.plugins.network.agent_based.lldp_cache import (
    host_label_lldp_cache,
    inventory_lldp_cache,
    Lldp,
    LldpGlobal,
    LldpNeighbor,
    parse_lldp_cache,
)

STRING_TABLE_1_NEIGHBOR = [
    [
        [
            "1",
            "4",  # lldpRemChassisIdSubtype   4 - mac-adrress, 5-network adress, rest
            [99, 160, 210, 120, 34, 200],  # lldpRemChassisId
            "3",  # lldpRemPortIdSubtype      4 - mac-adrress, 5/7-network adress, rest
            [55, 56, 49, 56, 46, 101, 99, 50, 101, 46, 98, 97, 56, 97],  # lldpRemPortId
            "port desc",  # lldpRemPortDesc
            "sys name",  # lldpRemSysName
            "sys desc",  # lldpRemSysDesc
            "01 00",  # lldpRemSysCapSupported
            "01 00",  # lldpRemSysCapEnabled
        ]
    ],  # lldp_rem_entry
    [
        [
            "1",  # interface index
            "3",  # lldpLocPortIdSubtype
            [55, 56, 49, 56, 46, 101, 99, 50, 101, 46, 98, 97, 56, 97],  # lldpLocPortId
        ]
    ],  # lldp_local_port_entry
    [
        [
            "4",  # lldpLocChassisIdSubtype
            [0, 4, 96, 155, 189, 79],  # lldpLocChassisId
            "Local Sys Name",  # lldpLocSysName
            "Local Sys Desc",  # lldpLocSysDesc
            "28 00 ",  # lldpLocSysCapSupported
            "28 00 ",  # lldpLocSysCapEnabled
        ]
    ],  # lldp_local_info
    [
        [
            "1",  # index
            "3",  # lldpRemManAddrIfSubtype
        ]
    ],  # lldp_rem_man_addr_entry
]


STRING_TABLE_2_NEIGHBORS = [
    [
        [
            "1",
            "4",  # lldpRemChassisIdSubtype   4 - mac-adrress, 5-network adress, rest
            [99, 160, 210, 120, 34, 200],  # lldpRemChassisId
            "3",  # lldpRemPortIdSubtype      4 - mac-adrress, 5/7-network adress, rest
            [55, 56, 49, 56, 46, 101, 99, 50, 101, 46, 98, 97, 56, 97],  # lldpRemPortId
            "port desc",  # lldpRemPortDesc
            "sys name",  # lldpRemSysName
            "sys desc",  # lldpRemSysDesc
            "01 00",  # lldpRemSysCapSupported
            "01 00",  # lldpRemSysCapEnabled
        ],
        [
            "1",
            "4",  # lldpRemChassisIdSubtype   4 - mac-adrress, 5-network adress, rest
            [99, 160, 210, 120, 34, 200],  # lldpRemChassisId
            "3",  # lldpRemPortIdSubtype      4 - mac-adrress, 5/7-network adress, rest
            [55, 56, 49, 56, 46, 101, 99, 50, 101, 46, 98, 97, 56, 97],  # lldpRemPortId
            "port desc 2",  # lldpRemPortDesc
            "sys name 2",  # lldpRemSysName
            "sys desc 2",  # lldpRemSysDesc
            "01 00",  # lldpRemSysCapSupported
            "01 00",  # lldpRemSysCapEnabled
        ],
    ],  # lldp_rem_entry
    [
        [
            "1",  # interface index
            "3",  # lldpLocPortIdSubtype
            [55, 56, 49, 56, 46, 101, 99, 50, 101, 46, 98, 97, 56, 97],  # lldpLocPortId
        ]
    ],  # lldp_local_port_entry
    [
        [
            "4",  # lldpLocChassisIdSubtype
            [0, 4, 96, 155, 189, 79],  # lldpLocChassisId
            "Local Sys Name",  # lldpLocSysName
            "Local Sys Desc",  # lldpLocSysDesc
            "28 00 ",  # lldpLocSysCapSupported
            "28 00 ",  # lldpLocSysCapEnabled
        ]
    ],  # lldp_local_info
    [
        [
            "1",  # index
            "3",  # lldpRemManAddrIfSubtype
        ],
        [
            "1",  # index
            "3",  # lldpRemManAddrIfSubtype
        ],
    ],  # lldp_rem_man_addr_entry
]


LLDP_GLOBAL = LldpGlobal(
    id="00:04:60:9B:BD:4F",
    name="Local Sys Name",
    description="Local Sys Desc",
    cap_supported="Phone, Repeater, Router",
    cap_enabled="Phone, Repeater, Router",
)

LLDP_NEIGHBOURS = [
    LldpNeighbor(
        capabilities="Phone, Router",
        capabilities_map_supported="Phone, Router",
        local_port="78:18:EC:2E:BA:8A",
        local_port_index="1",
        neighbor_address="",
        neighbor_id="63:A0:D2:78:22:C8",
        neighbor_name="sys name",
        neighbor_port="78:18:EC:2E:BA:8A",
        port_description="port desc",
        system_description="sys desc",
    ),
]

LLDP = Lldp(
    lldp_global=LLDP_GLOBAL,
    lldp_neighbors=LLDP_NEIGHBOURS,
)


@pytest.mark.parametrize(
    "data, expected",
    [
        ([], None),
        (STRING_TABLE_1_NEIGHBOR, LLDP),
        (
            STRING_TABLE_2_NEIGHBORS,
            Lldp(
                lldp_global=LLDP_GLOBAL,
                lldp_neighbors=LLDP_NEIGHBOURS
                + [
                    LldpNeighbor(
                        capabilities="Phone, Router",
                        capabilities_map_supported="Phone, Router",
                        local_port="78:18:EC:2E:BA:8A",
                        local_port_index="1",
                        neighbor_address="",
                        neighbor_id="63:A0:D2:78:22:C8",
                        neighbor_name="sys name 2",
                        neighbor_port="78:18:EC:2E:BA:8A",
                        port_description="port desc 2",
                        system_description="sys desc 2",
                    )
                ],
            ),
        ),
    ],
    ids=["no data", "lldp available", "lldp with 2 neighbors"],
)
def test_parse_lldp_cache(data: Sequence[StringByteTable], expected: Lldp | None) -> None:
    parsed = parse_lldp_cache(string_table=data)
    assert parsed == expected


@pytest.mark.parametrize(
    "section, expected",
    [
        (
            Lldp(
                lldp_global=LLDP_GLOBAL,
                lldp_neighbors=[],
            ),
            [],
        ),
        (
            LLDP,
            [
                HostLabel("cmk/has_lldp_neighbors", "yes"),
            ],
        ),
        (
            Lldp(
                lldp_global=LLDP_GLOBAL,
                lldp_neighbors=LLDP_NEIGHBOURS
                + [
                    LldpNeighbor(
                        capabilities="Phone, Router",
                        capabilities_map_supported="Phone, Router",
                        local_port="78:18:EC:2E:BA:8A",
                        local_port_index="2",
                        neighbor_address="",
                        neighbor_id="63:A0:D2:78:22:C8",
                        neighbor_name="sys name 2",
                        neighbor_port="78:18:EC:2E:BA:8A",
                        port_description="port desc 2",
                        system_description="sys desc 2",
                    ),
                ],
            ),
            [
                HostLabel("cmk/has_lldp_neighbors", "yes"),
            ],
        ),
    ],
    ids=["no neighbors", "with 1 neighbor", "with 2 neighbors"],
)
def test_host_label_lldp_cache(section: Lldp, expected: list[HostLabel]) -> None:
    labels = list(host_label_lldp_cache(section=section))
    assert labels == expected


LLDP_GLOBAL_ATTRIBUTE = Attributes(
    path=["networking", "lldp_cache"],
    inventory_attributes={
        "local_id": "00:04:60:9B:BD:4F",
        "local_name": "Local Sys Name",
        "local_description": "Local Sys Desc",
        "local_cap_supported": "Phone, Repeater, Router",
        "local_cap_enabled": "Phone, Repeater, Router",
    },
    status_attributes={},
)


LLDP_NEIGHBOUR_ATTRIBUTE = TableRow(
    path=["networking", "lldp_cache", "neighbors"],
    key_columns={
        "local_port": "78:18:EC:2E:BA:8A",
        "neighbor_name": "sys name",
        "neighbor_port": "78:18:EC:2E:BA:8A",
    },
    inventory_columns={
        "capabilities": "Phone, Router",
        "capabilities_map_supported": "Phone, Router",
        "neighbor_id": "63:A0:D2:78:22:C8",
        "port_description": "port desc",
        "system_description": "sys desc",
    },
    status_columns={},
)


@pytest.mark.parametrize(
    "section, params, expected",
    [
        (
            Lldp(lldp_global=LLDP_GLOBAL, lldp_neighbors=[]),
            {},
            [LLDP_GLOBAL_ATTRIBUTE],
        ),
        (
            LLDP,
            {},
            [LLDP_GLOBAL_ATTRIBUTE, LLDP_NEIGHBOUR_ATTRIBUTE],
        ),
    ],
    ids=["no neighbors", "with neighbors"],
)
def test_inventory_lldp_cache(section: Lldp, params: Any, expected: InventoryResult) -> None:  # type: ignore[misc]
    parsed = list(inventory_lldp_cache(params=params, section=section))
    assert parsed == expected
