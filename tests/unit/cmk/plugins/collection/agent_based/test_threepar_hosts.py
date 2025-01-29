#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.collection.agent_based.threepar_hosts import (
    check_threepar_hosts,
    discover_threepar_hosts,
    parse_threepar_hosts,
)

STRING_TABLE = [
    [
        '{"total":24,"members":[{"id":0,"name":"host-name","descriptors":{"os":"RHELinux"},"FCPaths":[{"wwn":"1000FABEF2D00030"},{"wwn":"1000FABEF2D00032"}],"iSCSIPaths":[]}]}'
    ]
]


@pytest.mark.parametrize(
    "section, expected_discovery_result",
    [
        pytest.param(
            STRING_TABLE,
            [Service(item="host-name")],
            id="For every host that has a name, a Service is discovered.",
        ),
        pytest.param(
            [],
            [],
            id="If there are no items in the input, nothing is discovered.",
        ),
    ],
)
def test_discover_3par_hosts(
    section: StringTable,
    expected_discovery_result: Sequence[Service],
) -> None:
    assert list(discover_threepar_hosts(parse_threepar_hosts(section))) == expected_discovery_result


@pytest.mark.parametrize(
    "section, item, expected_check_result",
    [
        pytest.param(
            STRING_TABLE,
            "not_found",
            [],
            id="If the item is not found, there are no results.",
        ),
        pytest.param(
            [['{"total":24,"members":[{"id":0,"name":"host-name"}]}']],
            "host-name",
            [Result(state=State.OK, summary="ID: 0")],
            id="If only the name is available, the check result is OK and it's indicated what the ID of the host is.",
        ),
        pytest.param(
            [
                [
                    '{"total":24,"members":[{"id":0,"name":"host-name","descriptors":{"os":"RHELinux"}}]}'
                ]
            ],
            "host-name",
            [
                Result(state=State.OK, summary="ID: 0"),
                Result(state=State.OK, summary="OS: RHELinux"),
            ],
            id="If there are desciptors for the operating system available, the check result is OK and information about the OS is given.",
        ),
        pytest.param(
            STRING_TABLE,
            "host-name",
            [
                Result(state=State.OK, summary="ID: 0"),
                Result(state=State.OK, summary="OS: RHELinux"),
                Result(state=State.OK, summary="FC Paths: 2"),
            ],
            id="If there are FC paths available, the check result is OK and it is indicated how many FC paths are available.",
        ),
        pytest.param(
            [
                [
                    '{"total":24,"members":[{"id":0,"name":"host-name","descriptors":{"os":"RHELinux"},"iSCSIPaths":[{"wwn":"1000FABEF2D00030"},{"wwn":"1000FABEF2D00032"}]}]}'
                ]
            ],
            "host-name",
            [
                Result(state=State.OK, summary="ID: 0"),
                Result(state=State.OK, summary="OS: RHELinux"),
                Result(state=State.OK, summary="iSCSI Paths: 2"),
            ],
            id="If there are iSCSI paths available, but no FC paths, the check result is OK and it is indicated how many iSCSI paths are available.",
        ),
    ],
)
def test_check_3par_hosts(
    section: StringTable,
    item: str,
    expected_check_result: Sequence[Result],
) -> None:
    assert (
        list(
            check_threepar_hosts(
                item=item,
                section=parse_threepar_hosts(section),
            )
        )
        == expected_check_result
    )
