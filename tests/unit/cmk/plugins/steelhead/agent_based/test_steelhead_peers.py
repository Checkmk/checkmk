#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.steelhead.agent_based.steelhead_peers import (
    check_steelhead_peers,
    discover_steelhead_peers,
    parse_steelhead_peers,
)

STRING_TABLE = [
    ["vadetsh1", "8.5.3c", "10.1.0.14", "CX770"],
    ["vadetsh2", "9.2.0a", "10.1.0.15", "CX570"],
    ["laptop-01", "4.8.1", "10.1.0.55", "Steelhead Mobile"],
]


def test_discovery_skips_steelhead_mobile_peers() -> None:
    section = parse_steelhead_peers(STRING_TABLE)

    result = list(discover_steelhead_peers(section))

    assert result == [Service(item="vadetsh1"), Service(item="vadetsh2")]


def test_check_is_ok_for_connected_peer() -> None:
    section = parse_steelhead_peers(STRING_TABLE)

    result = list(check_steelhead_peers("vadetsh1", section))

    assert result == [
        Result(state=State.OK, summary="Version: 8.5.3c, Client Address: 10.1.0.14 (CX770)")
    ]


def test_check_is_crit_for_missing_peer() -> None:
    section = parse_steelhead_peers(STRING_TABLE)

    result = list(check_steelhead_peers("vadetsh3", section))

    assert result == [Result(state=State.CRIT, summary="Peer not connected")]
