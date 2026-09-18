#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

import pytest
import time_machine

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.innovaphone.agent_based import innovaphone_priports_l1
from cmk.plugins.innovaphone.agent_based.innovaphone_priports_l1 import PriPort, Section

_STRING_TABLE = [
    ["Foo", "1", "0", "23"],  # item, state, sigloss, slip
    ["Bar", "2", "42", "23"],  # item, state, sigloss, slip
]


@pytest.fixture(name="section", scope="module")
def fixture_section() -> Section:
    return innovaphone_priports_l1.parse_innovaphone_priports_l1(_STRING_TABLE)


def test_parse_innovaphone_priports_l1() -> None:
    assert innovaphone_priports_l1.parse_innovaphone_priports_l1(_STRING_TABLE) == {
        "Foo": PriPort(state=1, sigloss=0, slip=23),
        "Bar": PriPort(state=2, sigloss=42, slip=23),
    }


def test_discover_innovaphone_priports_l1(section: Section) -> None:
    # Only "Bar" should be discovered because it has state != 1
    assert list(innovaphone_priports_l1.discover_innovaphone_priports_l1(section)) == [
        Service(item="Bar", parameters={"err_slip_count": 23})
    ]


@time_machine.travel(60.0)
def test_check_innovaphone_priports_l1_down_state(
    section: Section, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test check function for item in Down state (state=1)"""
    # Pre-populate value store to avoid GetRateError on first run
    value_store = {"innovaphone_priports_l1.Foo": (50.0, 0)}  # Previous: time=50, value=0
    monkeypatch.setattr(innovaphone_priports_l1, "get_value_store", lambda: value_store)

    assert list(
        innovaphone_priports_l1.check_innovaphone_priports_l1(
            "Foo", {"err_slip_count": 22}, section
        )
    ) == [
        Result(state=State.CRIT, summary="Current state is Down"),
        Result(state=State.CRIT, summary="Slip error count at 23"),
    ]


@time_machine.travel(60.0)
def test_check_innovaphone_priports_l1_up_state(
    section: Section, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test check function for item in UP state (state=2) with signal loss"""
    # Pre-populate value store to simulate rate calculation
    value_store = {"innovaphone_priports_l1.Bar": (50.0, 0)}  # Previous: time=50, value=0
    monkeypatch.setattr(innovaphone_priports_l1, "get_value_store", lambda: value_store)

    # Rate calculation: (42 - 0) / (60 - 50) = 42 / 10 = 4.20
    assert list(
        innovaphone_priports_l1.check_innovaphone_priports_l1(
            "Bar", {"err_slip_count": 23}, section
        )
    ) == [
        Result(state=State.OK, summary="Current state is UP"),
        Result(state=State.CRIT, summary="Signal loss is 4.20/sec"),
    ]


@time_machine.travel(60.0)
def test_check_innovaphone_priports_l1_no_signal_loss(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test check function with no signal loss"""
    section = innovaphone_priports_l1.parse_innovaphone_priports_l1(
        [["Test", "2", "0", "15"]]  # UP state, no signal loss, low slip count
    )

    # Pre-populate value store to avoid GetRateError on first run
    value_store = {"innovaphone_priports_l1.Test": (50.0, 0)}  # Previous: time=50, value=0
    monkeypatch.setattr(innovaphone_priports_l1, "get_value_store", lambda: value_store)

    # Should only have state check, no signal loss or slip error
    assert list(
        innovaphone_priports_l1.check_innovaphone_priports_l1(
            "Test", {"err_slip_count": 20}, section
        )
    ) == [Result(state=State.OK, summary="Current state is UP")]


def test_check_innovaphone_priports_l1_item_not_found() -> None:
    """Test check function with non-existent item"""
    assert not list(innovaphone_priports_l1.check_innovaphone_priports_l1("NonExistent", {}, {}))
