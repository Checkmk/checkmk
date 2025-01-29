#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.collection.agent_based.apc_powerswitch import (
    check_apc_powerswitch,
    discover_apc_powerswitch,
    parse_apc_powerswitch,
)

STRING_TABLE = [
    [
        ["1", "Rubrik rbot2 1-4", "1"],
        ["2", "C13 NOT IN USE", "1"],
        ["3", "Sampo 2A", "1"],
        ["24", "C19 NOT IN USE", ""],
        ["30", "C19 NOT IN USE", "6"],
    ]
]


def test_discover_apc_powerswitch() -> None:
    assert list(discover_apc_powerswitch(parse_apc_powerswitch(STRING_TABLE))) == [
        Service(item="1", parameters={"discovered_status": "1"}),
        Service(item="2", parameters={"discovered_status": "1"}),
        Service(item="3", parameters={"discovered_status": "1"}),
    ]


def test_discover_apc_powerswitch_no_items() -> None:
    assert not list(discover_apc_powerswitch({}))


def test_check_apc_powerswitch_item_not_found() -> None:
    assert not list(
        check_apc_powerswitch(
            item="Not there",
            section=parse_apc_powerswitch(STRING_TABLE),
        )
    )


def test_check_apc_powerswitch() -> None:
    assert list(
        check_apc_powerswitch(
            item="1",
            section=parse_apc_powerswitch(STRING_TABLE),
        )
    ) == [
        Result(state=State.OK, summary="Port Rubrik rbot2 1-4 has status on"),
    ]


def test_check_apc_powerswitch_empty_string_state() -> None:
    assert list(
        check_apc_powerswitch(
            item="24",
            section=parse_apc_powerswitch(STRING_TABLE),
        )
    ) == [Result(state=State.UNKNOWN, summary="Port C19 NOT IN USE has status unknown")]


def test_check_apc_powerswitch_unknown_state() -> None:
    assert list(check_apc_powerswitch(item="30", section=parse_apc_powerswitch(STRING_TABLE))) == [
        Result(
            state=State.UNKNOWN,
            summary="Port C19 NOT IN USE has status unknown (6)",
        )
    ]
