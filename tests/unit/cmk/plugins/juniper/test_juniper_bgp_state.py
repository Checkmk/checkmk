#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.juniper.agent_based.juniper_bgp_state import (
    check_juniper_bgp_state,
    discover_juniper_bgp_state,
    parse_juniper_bgp_state,
    Section,
)


def test_parse_juniper_bgp_state_parses_with_ipv4_data() -> None:
    # OIDBytes columns return list[int] at runtime, which doesn't fit StringTable = list[list[str]].
    # This is a known typing gap in the framework; ints are kept here to reflect actual SNMP data.
    parsed = parse_juniper_bgp_state([["6", "2", [100, 96, 1, 34]], ["3", "2", [100, 96, 1, 38]]])  # type: ignore[list-item]
    assert parsed == {
        "100.96.1.34": {"operational_state": "running", "state": "established"},
        "100.96.1.38": {"operational_state": "running", "state": "active"},
    }


def test_discover_juniper_bgp_state_has_two_services_with_ipv4_data() -> None:
    section: Section = {
        "100.96.1.34": {"operational_state": "running", "state": "established"},
        "100.96.1.38": {"operational_state": "running", "state": "active"},
    }
    results = discover_juniper_bgp_state(section)
    assert list(results) == [Service(item="100.96.1.34"), Service(item="100.96.1.38")]


def test_check_juniper_bgp_state_with_ipv4_data_has_valid_results() -> None:
    section: Section = {
        "100.96.1.34": {"operational_state": "running", "state": "established"},
        "100.96.1.38": {"operational_state": "running", "state": "active"},
    }

    results = check_juniper_bgp_state("100.96.1.34", section)

    assert list(results) == [
        Result(state=State.OK, summary="Status with peer 100.96.1.34 is established"),
        Result(state=State.OK, summary="operational status: running"),
    ]

    results = check_juniper_bgp_state("100.96.1.38", section)

    assert list(results) == [
        Result(state=State.CRIT, summary="Status with peer 100.96.1.38 is active"),
        Result(state=State.OK, summary="operational status: running"),
    ]


def test_parse_juniper_bgp_state_parses_with_ipv6_data() -> None:
    parsed = parse_juniper_bgp_state(
        [
            [
                "4",
                "1",
                [  # type: ignore[list-item]
                    "222",
                    "173",
                    "190",
                    "239",
                    "0",
                    "64",
                    "1",
                    "17",
                    "0",
                    "0",
                    "0",
                    "0",
                    "0",
                    "0",
                    "0",
                    "1",
                ],
            ],
            ["4", "2", ["0"] * 16],  # type: ignore[list-item]
        ]
    )
    assert parsed == {
        "[dead:beef:40:111::1]": {"operational_state": "halted", "state": "opensent"},
        "[::]": {"operational_state": "running", "state": "opensent"},
    }


def test_discover_juniper_bgp_state_has_two_services_with_ipv6_data() -> None:
    section: Section = {
        "[dead:beef:40:111::1]": {"operational_state": "halted", "state": "opensent"},
        "[::]": {"operational_state": "running", "state": "opensent"},
    }
    results = discover_juniper_bgp_state(section)
    assert list(results) == [Service(item="[dead:beef:40:111::1]"), Service(item="[::]")]


def test_check_juniper_bgp_state_with_ipv6_data_has_valid_results() -> None:
    section: Section = {
        "[dead:beef:40:111::1]": {"operational_state": "halted", "state": "opensent"},
        "[::]": {"operational_state": "running", "state": "opensent"},
    }

    results = check_juniper_bgp_state("[dead:beef:40:111::1]", section)

    assert list(results) == [
        Result(state=State.OK, summary="Status with peer [dead:beef:40:111::1] is opensent"),
        Result(state=State.WARN, summary="operational status: halted"),
    ]

    results = check_juniper_bgp_state("[::]", section)

    assert list(results) == [
        Result(state=State.CRIT, summary="Status with peer [::] is opensent"),
        Result(state=State.OK, summary="operational status: running"),
    ]
