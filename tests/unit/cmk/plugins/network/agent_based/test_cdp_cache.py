#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import (
    Attributes,
    HostLabel,
    InventoryResult,
    StringByteTable,
    TableRow,
)
from cmk.plugins.network.agent_based.cdp_cache import (
    Cdp,
    CdpGlobal,
    CdpNeighbor,
    host_label_cdp_cache,
    inventorize_cdp_cache,
    InventoryParams,
    parse_cdp_cache,
)

STRING_TABLE_1_NEIGHBOR = [
    [
        [
            "1",
            "1",
            "0A CD 0B 9A ",
            "Cisco IOS Software, C3560 Software (C3560-IPBASE-M), Version 12.2(25)SEB4, RELEASE SOFTWARE (fc1)Copyright (c) 1986-2005 by Cisco Systems, Inc.Compiled Tue 30-Aug-05 14:19 by yenanh",
            "SCHE-CH-BASEL-SW-1",
            "FastEthernet0/1",
            "cisco WS-C3560-24PS",
            [0, 0, 0, 29],
            "sche-ch-basel",
            "2",
            "3",
            None,
        ]
    ],  # cdp_info
    [
        [
            "1",
            "60",
            "180",
            "ip-enke-ch-bsk-r-005",
        ]
    ],  # cdp_global
    [
        [
            "1",
            "Gi0/0",
        ]
    ],  # if_info
]

STRING_TABLE_2_NEIGHBORS = [
    [
        [
            "1",
            "1",
            "0A CD 0B 9A ",
            "Cisco IOS Software, C3560 Software (C3560-IPBASE-M), Version 12.2(25)SEB4, RELEASE SOFTWARE (fc1)Copyright (c) 1986-2005 by Cisco Systems, Inc.Compiled Tue 30-Aug-05 14:19 by yenanh",
            "SCHE-CH-BASEL-SW-1",
            "FastEthernet0/1",
            "cisco WS-C3560-24PS",
            [0, 0, 0, 29],
            "sche-ch-basel",
            "2",
            "3",
            None,
        ],
        [
            "1",
            "1",
            "0A CD 0B 9A ",
            "Cisco IOS Software, C3560 Software (C3560-IPBASE-M), Version 12.2(25)SEB4, RELEASE SOFTWARE (fc1)Copyright (c) 1986-2005 by Cisco Systems, Inc.Compiled Tue 30-Aug-05 14:19 by yenanh",
            "SCHE-CH-BASEL-SW-2",
            "FastEthernet0/1",
            "cisco WS-C3560-24PS",
            [0, 0, 0, 29],
            "sche-ch-basel",
            "2",
            "3",
            None,
        ],
    ],  # cdp_info
    [
        [
            "1",
            "60",
            "180",
            "ip-enke-ch-bsk-r-005",
        ]
    ],  # cdp_global
    [
        [
            "1",
            "Gi0/0",
        ]
    ],  # if_info
]

CDP_GLOBAL = CdpGlobal(
    enabled="yes",
    hold_time=180,
    local_id="ip-enke-ch-bsk-r-005",
    message_interval=60,
)

CDP_NEIGHBORS = [
    CdpNeighbor(
        neighbor_id="SCHE-CH-BASEL-SW-1",
        neighbor_port="FastEthernet0/1",
        local_port="Gi0/0",
        address=None,
        capabilities="Host, L2, L3, SB",
        duplex="full duplex",
        native_vlan="2",
        platform="cisco WS-C3560-24PS",
        platform_details="Cisco IOS Software, C3560 Software (C3560-IPBASE-M), Version 12.2(25)SEB4, RELEASE SOFTWARE (fc1)Copyright (c) 1986-2005 by Cisco Systems, Inc.Compiled Tue 30-Aug-05 14:19 by yenanh",
        power_consumption="None",
        vtp_mgmt_domain="sche-ch-basel",
    )
]

CDP = Cdp(
    cdp_global=CDP_GLOBAL,
    cdp_neighbors=CDP_NEIGHBORS,
)


@pytest.mark.parametrize(
    "data, expected",
    [
        (
            [],
            None,
        ),
        (STRING_TABLE_1_NEIGHBOR, CDP),
        (
            STRING_TABLE_2_NEIGHBORS,
            Cdp(
                cdp_global=CDP_GLOBAL,
                cdp_neighbors=CDP_NEIGHBORS
                + [
                    CdpNeighbor(
                        neighbor_id="SCHE-CH-BASEL-SW-2",
                        neighbor_port="FastEthernet0/1",
                        local_port="Gi0/0",
                        address=None,
                        capabilities="Host, L2, L3, SB",
                        duplex="full duplex",
                        native_vlan="2",
                        platform="cisco WS-C3560-24PS",
                        platform_details="Cisco IOS Software, C3560 Software (C3560-IPBASE-M), Version 12.2(25)SEB4, RELEASE SOFTWARE (fc1)Copyright (c) 1986-2005 by Cisco Systems, Inc.Compiled Tue 30-Aug-05 14:19 by yenanh",
                        power_consumption="None",
                        vtp_mgmt_domain="sche-ch-basel",
                    )
                ],
            ),
        ),
    ],
    ids=["no data", "with 1 neighbor", "with 2 neighbors"],
)
def test_parse_inv_cdp_cache(data: Sequence[StringByteTable], expected: Cdp | None) -> None:
    parsed = parse_cdp_cache(string_table=data)
    assert parsed == expected


@pytest.mark.parametrize(
    "section, expected",
    [
        (
            Cdp(
                cdp_global=CDP_GLOBAL,
                cdp_neighbors=[],
            ),
            [],
        ),
        (
            CDP,
            [
                HostLabel("cmk/has_cdp_neighbors", "yes"),
            ],
        ),
        (
            Cdp(
                cdp_global=CDP_GLOBAL,
                cdp_neighbors=CDP_NEIGHBORS
                + [
                    CdpNeighbor(
                        neighbor_id="SCHE-CH-BASEL-SW-2",
                        neighbor_port="FastEthernet0/1",
                        local_port="Gi0/0",
                        address=None,
                        capabilities="Host, L2, L3, SB",
                        duplex="full duplex",
                        native_vlan="2",
                        platform="cisco WS-C3560-24PS",
                        platform_details="Cisco IOS Software, C3560 Software (C3560-IPBASE-M), Version 12.2(25)SEB4, RELEASE SOFTWARE (fc1)Copyright (c) 1986-2005 by Cisco Systems, Inc.Compiled Tue 30-Aug-05 14:19 by yenanh",
                        power_consumption="None",
                        vtp_mgmt_domain="sche-ch-basel",
                    )
                ],
            ),
            [
                HostLabel("cmk/has_cdp_neighbors", "yes"),
            ],
        ),
    ],
    ids=["no neighbors", "with 1 neighbor", "with 2 neighbor"],
)
def test_host_label_inv_cdp_cache(section: Cdp, expected: list[HostLabel]) -> None:
    labels = list(host_label_cdp_cache(section=section))
    assert labels == expected


CDP_GLOBAL_ATTRIBUTE = Attributes(
    path=["networking", "cdp_cache"],
    inventory_attributes={
        "enabled": "yes",
        "message_interval": 60,
        "hold_time": 180,
        "local_name": "ip-enke-ch-bsk-r-005",
    },
    status_attributes={},
)

CDP_NEIGHBOR_ATTRIBUTE = TableRow(
    path=["networking", "cdp_cache", "neighbors"],
    key_columns={
        "neighbor_name": "SCHE-CH-BASEL-SW-1",
        "neighbor_port": "FastEthernet0/1",
        "local_port": "Gi0/0",
    },
    inventory_columns={
        "platform_details": "Cisco IOS Software, C3560 Software (C3560-IPBASE-M), Version 12.2(25)SEB4, RELEASE SOFTWARE (fc1)Copyright (c) 1986-2005 by Cisco Systems, Inc.Compiled Tue 30-Aug-05 14:19 by yenanh",
        "platform": "cisco WS-C3560-24PS",
        "capabilities": "Host, L2, L3, SB",
        "vtp_mgmt_domain": "sche-ch-basel",
        "native_vlan": "2",
        "duplex": "full duplex",
        "power_consumption": "None",
    },
    status_columns={},
)


@pytest.mark.parametrize(
    "section, params, expected",
    [
        (
            Cdp(cdp_global=CDP_GLOBAL, cdp_neighbors=[]),
            InventoryParams(
                remove_domain=False,
                remove_columns=[],
                use_short_if_name=False,
            ),
            [CDP_GLOBAL_ATTRIBUTE],
        ),
        (
            CDP,
            InventoryParams(
                remove_domain=False,
                remove_columns=[],
                use_short_if_name=False,
            ),
            [CDP_GLOBAL_ATTRIBUTE, CDP_NEIGHBOR_ATTRIBUTE],
        ),
    ],
    ids=["no neighbors", "with neighbors"],
)
def test_inventorize_cdp_cache(
    section: Cdp, params: InventoryParams, expected: InventoryResult
) -> None:
    parsed = list(inventorize_cdp_cache(params=params, section=section))
    assert parsed == expected
