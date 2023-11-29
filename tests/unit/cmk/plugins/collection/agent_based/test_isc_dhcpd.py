#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.collection.agent_based.isc_dhcpd import (
    check_isc_dhcpd,
    DhcpdSection,
    discovery_isc_dhcpd,
    parse_isc_dhcpd,
)


@pytest.fixture(name="section", scope="module")
def fixture_section() -> DhcpdSection:
    return parse_isc_dhcpd(
        [
            ["[general]"],
            ["PID:", "29868"],
            ["[pools]"],
            ["10.42.97.30", "10.42.97.191"],
            ["10.42.101.30", "10.42.101.191"],
            ["10.42.103.101", "10.42.103.191"],
            ["10.42.153.30", "10.42.153.191"],
            ["10.42.155.101", "10.42.155.191"],
            ["10.42.157.30", "10.42.157.191"],
            ["[leases]"],
            ["10.66.45.98"],
            ["10.66.45.157"],
            ["10.66.45.164"],
            ["10.66.53.78"],
            ["10.66.55.174"],
            ["10.66.53.35"],
            ["10.42.97.160"],
            ["10.42.97.144"],
            ["10.42.97.173"],
            ["10.42.97.161"],
            ["10.42.97.116"],
            ["10.42.97.139"],
            ["10.42.97.184"],
        ]
    )


def test_discovery_cisco_ucs_mem(section: DhcpdSection) -> None:
    assert list(discovery_isc_dhcpd(section)) == [
        Service(item="10.42.97.30-10.42.97.191"),
        Service(item="10.42.101.30-10.42.101.191"),
        Service(item="10.42.103.101-10.42.103.191"),
        Service(item="10.42.153.30-10.42.153.191"),
        Service(item="10.42.155.101-10.42.155.191"),
        Service(item="10.42.157.30-10.42.157.191"),
    ]


@pytest.mark.parametrize(
    "item, params, expected_output",
    [
        pytest.param("missing", {"free_leases": (15.0, 5.0)}, [], id="Item missing in data"),
        pytest.param(
            "10.42.97.30-10.42.97.191",
            {"free_leases": (15.0, 5.0)},
            [
                Result(state=State.OK, summary="Free leases: 155"),
                Result(state=State.OK, summary="95.68%"),
                Metric("free_dhcp_leases", 155.0, levels=(24.3, 8.1), boundaries=(0.0, 162.0)),
                Result(state=State.OK, summary="Used leases: 7"),
                Result(state=State.OK, summary="4.32%"),
                Metric("used_dhcp_leases", 7.0, boundaries=(0.0, 162.0)),
            ],
            id="Some used leases",
        ),
        pytest.param(
            "10.42.101.30-10.42.101.191",
            {"free_leases": (15.0, 5.0)},
            [
                Result(state=State.OK, summary="Free leases: 162"),
                Result(state=State.OK, summary="100.00%"),
                Metric("free_dhcp_leases", 162.0, levels=(24.3, 8.1), boundaries=(0.0, 162.0)),
                Result(state=State.OK, summary="Used leases: 0"),
                Result(state=State.OK, summary="0%"),
                Metric("used_dhcp_leases", 0.0, boundaries=(0.0, 162.0)),
            ],
            id="No used leases",
        ),
    ],
)
def test_check_cisco_ucs_mem(
    item: str,
    params: Mapping[str, tuple],
    expected_output: Sequence[object],
    section: DhcpdSection,
) -> None:
    assert list(check_isc_dhcpd(item, params, section)) == expected_output
