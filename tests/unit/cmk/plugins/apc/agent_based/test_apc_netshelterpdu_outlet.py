#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.apc.agent_based.apc_netshelterpdu_outlet import (
    check_apc_netshelterpdu_outlet,
    discover_apc_netshelterpdu_outlet,
    parse_apc_netshelterpdu_outlet,
)


def test_discovery_only_on_outlets() -> None:
    # status 2=on, 1=off — only discover "on" outlets
    section = parse_apc_netshelterpdu_outlet(
        [
            [
                ["1", "OUTLET 1", "2"],
                ["2", "OUTLET 2", "1"],
                ["3", "OUTLET 3", "2"],
            ]
        ]
    )

    discoveries = sorted(discover_apc_netshelterpdu_outlet(section), key=lambda s: s.item or "")
    assert discoveries == [
        Service(item="1"),
        Service(item="3"),
    ]


def test_check_outlet_on() -> None:
    section = parse_apc_netshelterpdu_outlet([[["1", "OUTLET 1", "2"]]])

    result = list(check_apc_netshelterpdu_outlet("1", section))
    assert result == [Result(state=State.OK, summary="OUTLET 1: on")]


def test_check_outlet_off() -> None:
    section = parse_apc_netshelterpdu_outlet([[["1", "OUTLET 1", "1"]]])

    result = list(check_apc_netshelterpdu_outlet("1", section))
    assert result == [Result(state=State.WARN, summary="OUTLET 1: off")]


def test_check_outlet_missing() -> None:
    section = parse_apc_netshelterpdu_outlet([[["1", "OUTLET 1", "2"]]])

    result = list(check_apc_netshelterpdu_outlet("99", section))
    assert result == []


def test_check_outlet_unknown_status() -> None:
    section = parse_apc_netshelterpdu_outlet([[["1", "OUTLET 1", "3"]]])

    result = list(check_apc_netshelterpdu_outlet("1", section))
    assert result == [Result(state=State.UNKNOWN, summary="OUTLET 1: unknown (3)")]


def test_parse_empty() -> None:
    section = parse_apc_netshelterpdu_outlet([[]])
    assert section == {}
