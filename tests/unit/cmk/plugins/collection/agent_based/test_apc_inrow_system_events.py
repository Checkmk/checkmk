#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import Result, State
from cmk.plugins.collection.agent_based.apc_inrow_system_events import (
    check_apc_inrow_system_events,
    discover_apc_inrow_system_events,
    parse_apc_inrow_system_events,
)


def test_no_events_disover() -> None:
    assert list(discover_apc_inrow_system_events(parse_apc_inrow_system_events([])))


def test_no_events_are_ok() -> None:
    assert list(check_apc_inrow_system_events({"state": 1}, parse_apc_inrow_system_events([]))) == [
        Result(state=State.OK, summary="No service events")
    ]


def test_report_an_event() -> None:
    assert list(
        check_apc_inrow_system_events(
            {"state": 2}, parse_apc_inrow_system_events([["Zombie-appocalypse", "is", "happening"]])
        )
    ) == [Result(state=State.CRIT, summary="Zombie-appocalypse")]
