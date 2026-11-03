#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
import time_machine

from cmk.agent_based.v2 import GetRateError, Result, Service, State
from cmk.plugins.innovaphone.agent_based import (
    innovaphone_priports_l1 as innovaphone_priports_l1_module,
)
from cmk.plugins.innovaphone.agent_based.innovaphone_priports_l1 import (
    check_innovaphone_priports_l1,
    discover_innovaphone_priports_l1,
    parse_innovaphone_priports_l1,
    PriPort,
)


@pytest.fixture(name="value_store")
def fixture_value_store(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    # The previous check run saw a signal loss counter of 0 at t=50s.
    value_store: dict[str, object] = {"innovaphone_priports_l1.Port 1": (50.0, 0)}
    monkeypatch.setattr(innovaphone_priports_l1_module, "get_value_store", lambda: value_store)
    return value_store


def test_parse_innovaphone_priports_l1_maps_rows_by_item() -> None:
    string_table = [
        ["Port 1", "2", "42", "23"],
        ["Port 2", "1", "0", "5"],
    ]

    assert parse_innovaphone_priports_l1(string_table) == {
        "Port 1": PriPort(state=2, sigloss=42, slip=23),
        "Port 2": PriPort(state=1, sigloss=0, slip=5),
    }


@pytest.mark.parametrize(
    "row",
    [
        pytest.param([], id="empty row"),
        pytest.param(["Port 1", "2", "0"], id="missing column"),
        pytest.param(["Port 1", "", "0", "0"], id="empty state"),
        pytest.param(["Port 1", "2", "not-a-number", "0"], id="signal loss not a number"),
        pytest.param(["Port 1", "2", "0", "-1"], id="negative slip count"),
    ],
)
def test_parse_innovaphone_priports_l1_skips_rows_that_cannot_be_parsed(row: list[str]) -> None:
    assert parse_innovaphone_priports_l1([row, ["Port 2", "2", "0", "0"]]) == {
        "Port 2": PriPort(state=2, sigloss=0, slip=0),
    }


def test_discover_innovaphone_priports_l1_skips_down_ports_and_remembers_slip_count() -> None:
    section = {
        "Up": PriPort(state=2, sigloss=0, slip=23),
        "Down": PriPort(state=1, sigloss=0, slip=5),
    }

    assert list(discover_innovaphone_priports_l1(section)) == [
        Service(item="Up", parameters={"err_slip_count": 23}),
    ]


def test_check_innovaphone_priports_l1_missing_item_yields_nothing() -> None:
    assert not list(check_innovaphone_priports_l1("Missing", {"err_slip_count": 0}, {}))


@time_machine.travel(60.0)
def test_check_innovaphone_priports_l1_first_run_initializes_signal_loss_counter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value_store: dict[str, object] = {}
    monkeypatch.setattr(innovaphone_priports_l1_module, "get_value_store", lambda: value_store)
    section = {"Port 1": PriPort(state=2, sigloss=0, slip=0)}

    with pytest.raises(GetRateError):
        list(check_innovaphone_priports_l1("Port 1", {"err_slip_count": 0}, section))

    assert value_store == {"innovaphone_priports_l1.Port 1": (60.0, 0)}


# fmt: off
@pytest.mark.parametrize(
    "state, expected",
    [
        pytest.param(2, Result(state=State.OK, summary="Current state is UP"), id="up"),
        pytest.param(1, Result(state=State.CRIT, summary="Current state is Down"), id="down"),
        pytest.param(0, Result(state=State.UNKNOWN, summary="Current state is unknown (0)"), id="unknown"),
    ],
)
# fmt: on
@time_machine.travel(60.0)
@pytest.mark.usefixtures("value_store")
def test_check_innovaphone_priports_l1_reports_port_state(state: int, expected: Result) -> None:
    section = {"Port 1": PriPort(state=state, sigloss=0, slip=0)}

    assert list(check_innovaphone_priports_l1("Port 1", {"err_slip_count": 0}, section)) == [
        expected
    ]


@time_machine.travel(60.0)
@pytest.mark.usefixtures("value_store")
def test_check_innovaphone_priports_l1_signal_loss_is_crit() -> None:
    section = {"Port 1": PriPort(state=2, sigloss=42, slip=0)}

    assert list(check_innovaphone_priports_l1("Port 1", {"err_slip_count": 0}, section)) == [
        Result(state=State.OK, summary="Current state is UP"),
        Result(state=State.CRIT, summary="Signal loss is 4.20/sec"),
    ]


@time_machine.travel(60.0)
@pytest.mark.usefixtures("value_store")
def test_check_innovaphone_priports_l1_slip_count_above_discovered_is_crit() -> None:
    section = {"Port 1": PriPort(state=2, sigloss=0, slip=24)}

    assert list(check_innovaphone_priports_l1("Port 1", {"err_slip_count": 23}, section)) == [
        Result(state=State.OK, summary="Current state is UP"),
        Result(state=State.CRIT, summary="Slip error count at 24"),
    ]


@time_machine.travel(60.0)
@pytest.mark.usefixtures("value_store")
def test_check_innovaphone_priports_l1_slip_count_at_discovered_is_ok() -> None:
    section = {"Port 1": PriPort(state=2, sigloss=0, slip=23)}

    assert list(check_innovaphone_priports_l1("Port 1", {"err_slip_count": 23}, section)) == [
        Result(state=State.OK, summary="Current state is UP"),
    ]
