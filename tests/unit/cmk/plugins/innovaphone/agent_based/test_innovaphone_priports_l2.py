#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.innovaphone.agent_based.innovaphone_priports_l2 import (
    check_innovaphone_priports_l2,
    discover_innovaphone_priports_l2,
    parse_innovaphone_priports_l2,
    PriPort,
)


def test_parse_innovaphone_priports_l2_maps_rows_by_item() -> None:
    string_table = [
        ["Port 1", "2", "1"],
        ["Port 2", "1", "2"],
    ]

    assert parse_innovaphone_priports_l2(string_table) == {
        "Port 1": PriPort(state=2, mode=1),
        "Port 2": PriPort(state=1, mode=2),
    }


def test_parse_innovaphone_priports_l2_falls_back_to_zero_for_non_integers() -> None:
    assert parse_innovaphone_priports_l2([["Port 1", "", "not-a-number"]]) == {
        "Port 1": PriPort(state=0, mode=0),
    }


def test_discover_innovaphone_priports_l2_skips_down_ports_and_remembers_mode() -> None:
    section = {
        "Up": PriPort(state=2, mode=2),
        "Down": PriPort(state=1, mode=1),
    }

    assert list(discover_innovaphone_priports_l2(section)) == [
        Service(item="Up", parameters={"mode": 2}),
    ]


def test_check_innovaphone_priports_l2_missing_item_yields_nothing() -> None:
    assert not list(check_innovaphone_priports_l2("Missing", {"mode": 1}, {}))


def test_check_innovaphone_priports_l2_up_port_in_discovered_mode_is_ok() -> None:
    section = {"Port 1": PriPort(state=2, mode=1)}

    assert list(check_innovaphone_priports_l2("Port 1", {"mode": 1}, section)) == [
        Result(state=State.OK, summary="State: UP"),
        Result(state=State.OK, summary="Mode: TE"),
    ]


def test_check_innovaphone_priports_l2_down_port_is_crit() -> None:
    section = {"Port 1": PriPort(state=1, mode=1)}

    assert list(check_innovaphone_priports_l2("Port 1", {"mode": 1}, section)) == [
        Result(state=State.CRIT, summary="State: Down"),
        Result(state=State.OK, summary="Mode: TE"),
    ]


def test_check_innovaphone_priports_l2_changed_mode_is_crit() -> None:
    section = {"Port 1": PriPort(state=2, mode=2)}

    assert list(check_innovaphone_priports_l2("Port 1", {"mode": 1}, section)) == [
        Result(state=State.OK, summary="State: UP"),
        Result(state=State.CRIT, summary="Mode: NT"),
    ]
