#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.hp_proliant.agent_based.hp_proliant_da_cntlr import (
    check_hp_proliant_da_cntlr,
    discovery_hp_proliant_da_cntlr,
    parse_hp_proliant_da_cntlr,
)


def test_discovery_creates_one_service_per_controller() -> None:
    section = parse_hp_proliant_da_cntlr(
        [
            ["0", "54", "0", "2", "1", "2", "2", "N/A"],
            ["3", "52", "3", "3", "1", "2", "2", "PXXXX0BRH6X59X"],
            ["9", "0", "0", "0", "0", "0", "0", ""],
        ]
    )

    assert list(discovery_hp_proliant_da_cntlr(section)) == [
        Service(item="0"),
        Service(item="3"),
        Service(item="9"),
    ]


def test_discovery_creates_no_service_without_controllers() -> None:
    section = parse_hp_proliant_da_cntlr([])

    assert not list(discovery_hp_proliant_da_cntlr(section))


def test_check_unknown_item() -> None:
    section = parse_hp_proliant_da_cntlr([["0", "54", "0", "2", "1", "2", "2", "N/A"]])

    assert list(check_hp_proliant_da_cntlr("foo", section)) == [
        Result(state=State.UNKNOWN, summary="Controller not found in SNMP data"),
    ]


def test_check_incomplete_data() -> None:
    section = parse_hp_proliant_da_cntlr([["9", "0", "0", "0", "0", "0", "0", ""]])

    assert list(check_hp_proliant_da_cntlr("9", section)) == [
        Result(state=State.UNKNOWN, summary="Controller not found in SNMP data"),
    ]


def test_healthy_controller_is_ok() -> None:
    section = parse_hp_proliant_da_cntlr([["0", "54", "0", "2", "3", "2", "2", "N/A"]])

    assert list(check_hp_proliant_da_cntlr("0", section)) == [
        Result(
            state=State.OK,
            summary="Condition: ok, Board-Condition: ok, Board-Status: ok (Role: active, Model: 54, Slot: 0, Serial: N/A)",
        ),
    ]


def test_degraded_condition_is_warn() -> None:
    section = parse_hp_proliant_da_cntlr([["3", "52", "3", "3", "1", "2", "2", "PXXXX0BRH6X59X"]])

    assert list(check_hp_proliant_da_cntlr("3", section)) == [
        Result(
            state=State.WARN,
            summary="Condition: degraded, Board-Condition: ok, Board-Status: ok (Role: other, Model: 52, Slot: 3, Serial: PXXXX0BRH6X59X)",
        ),
    ]


def test_failed_condition_is_crit() -> None:
    section = parse_hp_proliant_da_cntlr([["3", "52", "3", "4", "1", "2", "2", "PXXXX0BRH6X59X"]])

    assert list(check_hp_proliant_da_cntlr("3", section)) == [
        Result(
            state=State.CRIT,
            summary="Condition: failed, Board-Condition: ok, Board-Status: ok (Role: other, Model: 52, Slot: 3, Serial: PXXXX0BRH6X59X)",
        ),
    ]


def test_failed_board_condition_is_crit() -> None:
    section = parse_hp_proliant_da_cntlr([["3", "52", "3", "2", "1", "2", "4", "PXXXX0BRH6X59X"]])

    assert list(check_hp_proliant_da_cntlr("3", section)) == [
        Result(
            state=State.CRIT,
            summary="Condition: ok, Board-Condition: failed, Board-Status: ok (Role: other, Model: 52, Slot: 3, Serial: PXXXX0BRH6X59X)",
        ),
    ]


def test_board_status_cable_problem_is_crit() -> None:
    section = parse_hp_proliant_da_cntlr([["3", "52", "3", "2", "1", "4", "2", "PXXXX0BRH6X59X"]])

    assert list(check_hp_proliant_da_cntlr("3", section)) == [
        Result(
            state=State.CRIT,
            summary="Condition: ok, Board-Condition: ok, Board-Status: cable problem (Role: other, Model: 52, Slot: 3, Serial: PXXXX0BRH6X59X)",
        ),
    ]


def test_board_status_updating_is_warn() -> None:
    section = parse_hp_proliant_da_cntlr([["3", "52", "3", "2", "1", "19", "2", "PXXXX0BRH6X59X"]])

    assert list(check_hp_proliant_da_cntlr("3", section)) == [
        Result(
            state=State.WARN,
            summary="Condition: ok, Board-Condition: ok, Board-Status: updating (Role: other, Model: 52, Slot: 3, Serial: PXXXX0BRH6X59X)",
        ),
    ]


def test_other_board_condition_is_warn_and_explained() -> None:
    section = parse_hp_proliant_da_cntlr([["6", "1", "6", "2", "1", "8", "1", "PEYHN0ARCC307J"]])

    assert list(check_hp_proliant_da_cntlr("6", section)) == [
        Result(
            state=State.WARN,
            summary="Condition: ok, Board-Condition: other, Board-Status: enabled (Role: other, Model: 1, Slot: 6, Serial: PEYHN0ARCC307J)",
            details="The instrument agent does not recognize the status of the controller. You may need to upgrade the instrument agent.",
        ),
    ]
