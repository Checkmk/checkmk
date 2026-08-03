#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.viprinet.agent_based.viprinet_router import (
    check_viprinet_router,
    CheckParams,
    discover_viprinet_router,
    parse_viprinet_router,
)

_STRING_TABLE = [["1"]]


def test_discover_viprinet_router() -> None:
    section = parse_viprinet_router(_STRING_TABLE)
    assert list(discover_viprinet_router(section)) == [Service(parameters={"mode_inv": "1"})]


def test_discover_viprinet_router_no_data() -> None:
    section = parse_viprinet_router([])
    assert list(discover_viprinet_router(section)) == []


@pytest.mark.parametrize(
    "params, expected",
    [
        (
            {},
            [Result(state=State.OK, summary="Hub")],
        ),
        (
            {"expect_mode": "node"},
            [
                Result(
                    state=State.CRIT,
                    summary="Mode 'Hub' differs from expected mode 'Node'",
                )
            ],
        ),
        (
            {"expect_mode": "hub"},
            [Result(state=State.OK, summary="Hub")],
        ),
        (
            {"expect_mode": "inventory", "mode_inv": "0"},
            [
                Result(
                    state=State.CRIT,
                    summary="Mode 'Hub' differs from expected mode 'Node'",
                )
            ],
        ),
        (
            {"expect_mode": "inventory", "mode_inv": "1"},
            [Result(state=State.OK, summary="Hub")],
        ),
    ],
)
def test_check_viprinet_router(params: CheckParams, expected: list[Result]) -> None:
    section = parse_viprinet_router(_STRING_TABLE)
    assert list(check_viprinet_router(params, section)) == expected


def test_check_viprinet_router_undefined_mode() -> None:
    section = parse_viprinet_router([["9"]])
    assert list(check_viprinet_router({}, section)) == [
        Result(state=State.UNKNOWN, summary="Undefined Mode"),
    ]
