#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence

import pytest

from cmk.base.legacy_checks.isc_dhcpd import check_isc_dhcpd, inventory_isc_dhcpd
from cmk.base.plugins.agent_based.isc_dhcpd import DhcpdSection, parse_isc_dhcpd


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


def test_inventory_cisco_ucs_mem(section: DhcpdSection) -> None:
    assert list(inventory_isc_dhcpd(section)) == [
        ("10.42.97.30-10.42.97.191", None),
        ("10.42.101.30-10.42.101.191", None),
        ("10.42.103.101-10.42.103.191", None),
        ("10.42.153.30-10.42.153.191", None),
        ("10.42.155.101-10.42.155.191", None),
        ("10.42.157.30-10.42.157.191", None),
    ]


@pytest.mark.parametrize(
    "item, params, expected_output",
    [
        pytest.param("missing", {"free_leases": (15.0, 5.0)}, [], id="Item missing in data"),
        pytest.param(
            "10.42.97.30-10.42.97.191",
            {"free_leases": (15.0, 5.0)},
            [
                (0, "Free leases: 155", []),
                (0, "95.68%", []),
                (0, "", [("free_dhcp_leases", 155.0, 24.3, 8.1, 0.0, 162.0)]),
                (0, "Used leases: 7", []),
                (0, "4.32%", []),
                (0, "", [("used_dhcp_leases", 7.0, None, None, 0.0, 162.0)]),
            ],
            id="Some used leases",
        ),
        pytest.param(
            "10.42.101.30-10.42.101.191",
            {"free_leases": (15.0, 5.0)},
            [
                (0, "Free leases: 162", []),
                (0, "100.00%", []),
                (0, "", [("free_dhcp_leases", 162.0, 24.3, 8.1, 0.0, 162.0)]),
                (0, "Used leases: 0", []),
                (0, "0%", []),
                (0, "", [("used_dhcp_leases", 0.0, None, None, 0.0, 162.0)]),
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
