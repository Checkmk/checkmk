#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

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


@pytest.mark.parametrize(
    "row",
    [
        pytest.param([], id="empty row"),
        pytest.param(["Port 1", "2"], id="missing column"),
        pytest.param(["Port 1", "", "1"], id="empty state"),
        pytest.param(["Port 1", "2", "not-a-number"], id="mode not a number"),
        pytest.param(["Port 1", "-1", "1"], id="negative state"),
    ],
)
@pytest.mark.xfail(strict=True, reason="rows that cannot be parsed are not skipped")
def test_parse_innovaphone_priports_l2_skips_rows_that_cannot_be_parsed(row: list[str]) -> None:
    assert parse_innovaphone_priports_l2([row, ["Port 2", "2", "1"]]) == {
        "Port 2": PriPort(state=2, mode=1),
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
