#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="no-untyped-call"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

# mypy: disable-error-code="var-annotated"

from typing import Any

import pytest
import time_machine

from cmk.base.legacy_checks import innovaphone_priports_l1


@pytest.fixture(name="parsed", scope="module")
def fixture_parsed() -> dict[str, Any]:
    string_table = [
        ["Foo", "1", "0", "23"],  # item, state, sigloss, slip
        ["Bar", "2", "42", "23"],  # item, state, sigloss, slip
    ]
    return innovaphone_priports_l1.parse_innovaphone_priports_l1(string_table)


def test_parse_innovaphone_priports_l1() -> None:
    string_table = [
        ["Foo", "1", "0", "23"],
        ["Bar", "2", "42", "23"],
    ]
    result = innovaphone_priports_l1.parse_innovaphone_priports_l1(string_table)

    expected = {
        "Foo": {"state": 1, "sigloss": 0, "slip": 23},
        "Bar": {"state": 2, "sigloss": 42, "slip": 23},
    }
    assert result == expected


def test_discover_innovaphone_priports_l1(parsed: dict[str, Any]) -> None:
    result = list(innovaphone_priports_l1.discover_innovaphone_priports_l1(parsed))

    # Only "Bar" should be discovered because it has state != 1
    assert result == [("Bar", {"err_slip_count": 23})]


@time_machine.travel(60.0)
def test_check_innovaphone_priports_l1_down_state(
    parsed: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test check function for item in Down state (state=1)"""
    # Pre-populate value store to avoid GetRateError on first run
    value_store = {"innovaphone_priports_l1.Foo": (50.0, 0)}  # Previous: time=50, value=0
    monkeypatch.setattr(innovaphone_priports_l1, "get_value_store", lambda: value_store)

    result = list(
        innovaphone_priports_l1.check_innovaphone_priports_l1("Foo", {"err_slip_count": 22}, parsed)
    )

    assert len(result) == 2

    # State check
    state, summary = result[0][:2]
    assert state == 2  # CRIT because state is Down
    assert "Current state is Down" in summary

    # Slip error check
    state, summary = result[1][:2]
    assert state == 2  # CRIT because slip count exceeds threshold
    assert "Slip error count at 23" in summary


@time_machine.travel(60.0)
def test_check_innovaphone_priports_l1_up_state(
    parsed: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test check function for item in UP state (state=2) with signal loss"""
    # Pre-populate value store to simulate rate calculation
    value_store = {"innovaphone_priports_l1.Bar": (50.0, 0)}  # Previous: time=50, value=0
    monkeypatch.setattr(innovaphone_priports_l1, "get_value_store", lambda: value_store)

    result = list(
        innovaphone_priports_l1.check_innovaphone_priports_l1("Bar", {"err_slip_count": 23}, parsed)
    )

    assert len(result) == 2

    # State check
    state, summary = result[0][:2]
    assert state == 0  # OK because state is UP
    assert "Current state is UP" in summary

    # Signal loss rate check
    state, summary = result[1][:2]
    assert state == 2  # CRIT because signal loss rate > 0
    assert "Signal loss is 4.20/sec" in summary
    # Rate calculation: (42 - 0) / (60 - 50) = 42 / 10 = 4.20


@time_machine.travel(60.0)
def test_check_innovaphone_priports_l1_no_signal_loss(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test check function with no signal loss"""
    string_table = [
        ["Test", "2", "0", "15"],  # UP state, no signal loss, low slip count
    ]
    parsed = innovaphone_priports_l1.parse_innovaphone_priports_l1(string_table)

    # Pre-populate value store to avoid GetRateError on first run
    value_store = {"innovaphone_priports_l1.Test": (50.0, 0)}  # Previous: time=50, value=0
    monkeypatch.setattr(innovaphone_priports_l1, "get_value_store", lambda: value_store)

    result = list(
        innovaphone_priports_l1.check_innovaphone_priports_l1(
            "Test", {"err_slip_count": 20}, parsed
        )
    )

    # Should only have state check, no signal loss or slip error
    assert len(result) == 1

    state, summary = result[0][:2]
    assert state == 0
    assert "Current state is UP" in summary


def test_check_innovaphone_priports_l1_item_not_found() -> None:
    """Test check function with non-existent item"""
    parsed = {}
    result = list(innovaphone_priports_l1.check_innovaphone_priports_l1("NonExistent", {}, parsed))

    assert len(result) == 0
