#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.collection.agent_based.threepar_system import (
    check_threepar_system,
    discover_threepar_system,
    parse_threepar_system,
)

STRING_TABLE = [
    [
        '{"id":168676,"name":"test-name","systemVersion":"9.5.3.12","IPv4Addr":"172.17.37.20","model":"HPEAlletra9060","serialNumber":"CZ222908M6","totalNodes":2,"masterNode":0,"onlineNodes":[0,1],"clusterNodes":[0,1]}'
    ]
]


@pytest.mark.parametrize(
    "section, expected_discovery_result",
    [
        pytest.param(
            STRING_TABLE,
            [
                Service(item="test-name"),
            ],
            id="For every that has a name, a Service is discovered.",
        ),
        pytest.param(
            [],
            [],
            id="If there are no items in the input, nothing is discovered.",
        ),
    ],
)
def test_discover_3par_system(
    section: StringTable,
    expected_discovery_result: Sequence[Service],
) -> None:
    assert (
        list(discover_threepar_system(parse_threepar_system(section))) == expected_discovery_result
    )


@pytest.mark.parametrize(
    "section, expected_check_result",
    [
        pytest.param(
            STRING_TABLE,
            [
                Result(
                    state=State.OK,
                    summary="Model: HPEAlletra9060, Version: 9.5.3.12, Serial number: CZ222908M6, Online nodes: 2/2",
                )
            ],
            id="The first check result is always OK.",
        ),
        pytest.param(
            [
                [
                    '{"id":168676,"name":"test-name","systemVersion":"9.5.3.12","IPv4Addr":"172.17.37.20","model":"HPEAlletra9060","serialNumber":"CZ222908M6","totalNodes":2,"masterNode":0,"onlineNodes":[0,1],"clusterNodes":[0,1,2]}'
                ]
            ],
            [
                Result(
                    state=State.OK,
                    summary="Model: HPEAlletra9060, Version: 9.5.3.12, Serial number: CZ222908M6, Online nodes: 2/3",
                ),
                Result(state=State.CRIT, summary="(Node 2 not available)"),
            ],
            id="If the number of online nodes is lower than the number of available cluster nodes, the check result is CRIT.",
        ),
        pytest.param(
            [
                [
                    '{"id":168676,"name":"test-name","systemVersion":"9.5.3.12","IPv4Addr":"172.17.37.20","model":"HPEAlletra9060","serialNumber":"CZ222908M6","totalNodes":2,"masterNode":0}'
                ]
            ],
            [
                Result(
                    state=State.OK,
                    summary="Model: HPEAlletra9060, Version: 9.5.3.12, Serial number: CZ222908M6, Online nodes: 0/0",
                ),
            ],
            id="No online and cluster nodes available",
        ),
    ],
)
def test_check_3par_system(
    section: StringTable,
    expected_check_result: Sequence[Result],
) -> None:
    assert (
        list(
            check_threepar_system(
                item="test-name",
                section=parse_threepar_system(section),
            )
        )
        == expected_check_result
    )
