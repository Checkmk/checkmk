#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import (
    StringByteTable,
)
from cmk.plugins.network.agent_based.lldp_cache import (
    Lldp,
    LldpGlobal,
    LldpNeighbor,
    parse_lldp_cache_fortinet,
)

STRING_TABLE = [
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
    [
        [
            "1",
            "port1",
        ]
    ],
    [
        [
            "8FPTF23021584-0: port51 ::8FPTF23021548-0: port49 ::8FPTF23012793-0: port45  port46 ::HPV01-AGGREGATE: port25  port26  port27  port28 ::HPV02-AGGREGATE: port29  port30  port31  port32 ::HPV03-AGGREGATE: port33  port34  port35  port36 ::NAS-AGGREGATE: port1  port2  port3  port4 ::NAS_SYNO-AGGR: port5  port6 ::GT60FTK2309BA7T: port47 ::GT60FTK2309BCNJ: port48 ::"
        ]
    ],
]


LLDP_GLOBAL = LldpGlobal(
    id="00:04:60:9B:BD:4F",
    name="Local Sys Name",
    description="Local Sys Desc",
    cap_supported="Phone, Repeater, Router",
    cap_enabled="Phone, Repeater, Router",
)

LLDP_NEIGHBORS = [
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
    )
]

LLDP = Lldp(
    lldp_global=LLDP_GLOBAL,
    lldp_neighbors=LLDP_NEIGHBORS,
)


@pytest.mark.parametrize(
    "data, expected",
    [
        pytest.param([], None, id="no data"),
        pytest.param(STRING_TABLE, LLDP, id="lldp available"),
        pytest.param(
            [[], [], [], [], [], []],
            Lldp(lldp_global=None, lldp_neighbors=[]),
            id="empty individual items (from siteless tests)",
        ),
    ],
)
def test_parse_lldp_cache_fortinet(data: Sequence[StringByteTable], expected: Lldp | None) -> None:
    parsed = parse_lldp_cache_fortinet(string_table=data)

    assert parsed == expected
