#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.legacy_checks.fortigate_sslvpn import (
    check_fortigate_sslvpn,
    discover_fortigate_sslvpn,
    parse_fortigate_sslvpn,
    Section,
    VPNDomain,
)


@pytest.fixture(name="string_table")
def _string_table() -> Sequence[StringTable]:
    return [[["root"]], [["2", "9", "6", "6", "20"]]]


@pytest.fixture(name="section")
def _section(string_table: Sequence[StringTable]) -> Section:
    return parse_fortigate_sslvpn(string_table)


def test_parse_fortigate_sslvpn(string_table: Sequence[StringTable]) -> None:
    assert parse_fortigate_sslvpn(string_table) == {
        "root": VPNDomain(state="2", users=9, web_sessions=6, tunnels=6, tunnels_max=20)
    }


def test_parse_fortigate_sslvpn_empty_data() -> None:
    assert parse_fortigate_sslvpn([[], []]) == {}


def test_discover_fortigate_sslvpn(section: Section) -> None:
    assert list(discover_fortigate_sslvpn(section)) == [Service(item="root")]


def test_discover_fortigate_sslvpn_empty_section() -> None:
    assert not list(discover_fortigate_sslvpn({}))


@pytest.mark.parametrize(
    "params, expected_tunnel_results",
    [
        pytest.param(
            {},
            [
                Result(state=State.OK, summary="Tunnels: 6"),
                Metric("active_vpn_tunnels", 6.0, boundaries=(0.0, 20.0)),
            ],
            id="no levels",
        ),
        pytest.param(
            {"tunnel_levels": (5, 10)},
            [
                Result(state=State.WARN, summary="Tunnels: 6 (warn/crit at 5/10)"),
                Metric("active_vpn_tunnels", 6.0, levels=(5.0, 10.0), boundaries=(0.0, 20.0)),
            ],
            id="warn",
        ),
        pytest.param(
            {"tunnel_levels": (3, 5)},
            [
                Result(state=State.CRIT, summary="Tunnels: 6 (warn/crit at 3/5)"),
                Metric("active_vpn_tunnels", 6.0, levels=(3.0, 5.0), boundaries=(0.0, 20.0)),
            ],
            id="crit",
        ),
    ],
)
def test_check_fortigate_sslvpn(
    section: Section,
    params: Mapping[str, object],
    expected_tunnel_results: Sequence[object],
) -> None:
    assert list(check_fortigate_sslvpn("root", params, section)) == [
        Result(state=State.OK, summary="enabled"),
        Result(state=State.OK, summary="Users: 9"),
        Metric("active_vpn_users", 9.0),
        Result(state=State.OK, summary="Web sessions: 6"),
        Metric("active_vpn_websessions", 6.0),
        *expected_tunnel_results,
    ]


def test_check_fortigate_sslvpn_disabled_state() -> None:
    section = parse_fortigate_sslvpn([[["root"]], [["1", "0", "0", "0", "20"]]])

    assert list(check_fortigate_sslvpn("root", {}, section)) == [
        Result(state=State.OK, summary="disabled"),
        Result(state=State.OK, summary="Users: 0"),
        Metric("active_vpn_users", 0.0),
        Result(state=State.OK, summary="Web sessions: 0"),
        Metric("active_vpn_websessions", 0.0),
        Result(state=State.OK, summary="Tunnels: 0"),
        Metric("active_vpn_tunnels", 0.0, boundaries=(0.0, 20.0)),
    ]


def test_check_fortigate_sslvpn_multiple_domains() -> None:
    section = parse_fortigate_sslvpn(
        [
            [["root"], ["branch1"]],
            [["2", "9", "6", "6", "20"], ["2", "3", "2", "1", "10"]],
        ]
    )

    assert list(discover_fortigate_sslvpn(section)) == [
        Service(item="root"),
        Service(item="branch1"),
    ]
    assert Result(state=State.OK, summary="Users: 9") in list(
        check_fortigate_sslvpn("root", {}, section)
    )
    assert Result(state=State.OK, summary="Users: 3") in list(
        check_fortigate_sslvpn("branch1", {}, section)
    )


def test_check_fortigate_sslvpn_missing_item(section: Section) -> None:
    assert not list(check_fortigate_sslvpn("nonexistent", {}, section))
