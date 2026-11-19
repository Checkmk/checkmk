#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.hp_proliant.agent_based.hp_proliant_da_cntlr import (
    check_hp_proliant_da_cntlr,
    DEFAULT_PARAMETERS,
    discovery_hp_proliant_da_cntlr,
    Params,
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

    assert list(check_hp_proliant_da_cntlr("foo", DEFAULT_PARAMETERS, section)) == [
        Result(state=State.UNKNOWN, summary="Controller not found in SNMP data"),
    ]


def test_check_incomplete_data() -> None:
    section = parse_hp_proliant_da_cntlr([["9", "0", "0", "0", "0", "0", "0", ""]])

    assert list(check_hp_proliant_da_cntlr("9", DEFAULT_PARAMETERS, section)) == [
        Result(state=State.UNKNOWN, summary="Controller not found in SNMP data"),
    ]


def test_healthy_controller_is_ok() -> None:
    section = parse_hp_proliant_da_cntlr([["0", "54", "0", "2", "3", "2", "2", "N/A"]])

    assert list(check_hp_proliant_da_cntlr("0", DEFAULT_PARAMETERS, section)) == [
        Result(state=State.OK, summary="Condition: ok"),
        Result(state=State.OK, summary="Board-Condition: ok"),
        Result(state=State.OK, summary="Board-Status: ok"),
        Result(
            state=State.OK,
            summary="Role: active, Model: 54, Slot: 0, Serial: N/A",
        ),
    ]


def test_degraded_condition_is_warn() -> None:
    section = parse_hp_proliant_da_cntlr([["3", "52", "3", "3", "1", "2", "2", "PXXXX0BRH6X59X"]])

    assert list(check_hp_proliant_da_cntlr("3", DEFAULT_PARAMETERS, section)) == [
        Result(state=State.WARN, summary="Condition: degraded"),
        Result(state=State.OK, summary="Board-Condition: ok"),
        Result(state=State.OK, summary="Board-Status: ok"),
        Result(
            state=State.OK,
            summary="Role: other, Model: 52, Slot: 3, Serial: PXXXX0BRH6X59X",
        ),
    ]


def test_failed_condition_is_crit() -> None:
    section = parse_hp_proliant_da_cntlr([["3", "52", "3", "4", "1", "2", "2", "PXXXX0BRH6X59X"]])

    assert list(check_hp_proliant_da_cntlr("3", DEFAULT_PARAMETERS, section)) == [
        Result(state=State.CRIT, summary="Condition: failed"),
        Result(state=State.OK, summary="Board-Condition: ok"),
        Result(state=State.OK, summary="Board-Status: ok"),
        Result(
            state=State.OK,
            summary="Role: other, Model: 52, Slot: 3, Serial: PXXXX0BRH6X59X",
        ),
    ]


def test_failed_board_condition_is_crit() -> None:
    section = parse_hp_proliant_da_cntlr([["3", "52", "3", "2", "1", "2", "4", "PXXXX0BRH6X59X"]])

    assert list(check_hp_proliant_da_cntlr("3", DEFAULT_PARAMETERS, section)) == [
        Result(state=State.OK, summary="Condition: ok"),
        Result(state=State.CRIT, summary="Board-Condition: failed"),
        Result(state=State.OK, summary="Board-Status: ok"),
        Result(
            state=State.OK,
            summary="Role: other, Model: 52, Slot: 3, Serial: PXXXX0BRH6X59X",
        ),
    ]


def test_board_status_cable_problem_is_crit() -> None:
    section = parse_hp_proliant_da_cntlr([["3", "52", "3", "2", "1", "4", "2", "PXXXX0BRH6X59X"]])

    assert list(check_hp_proliant_da_cntlr("3", DEFAULT_PARAMETERS, section)) == [
        Result(state=State.OK, summary="Condition: ok"),
        Result(state=State.OK, summary="Board-Condition: ok"),
        Result(state=State.CRIT, summary="Board-Status: cable problem"),
        Result(
            state=State.OK,
            summary="Role: other, Model: 52, Slot: 3, Serial: PXXXX0BRH6X59X",
        ),
    ]


def test_board_status_updating_is_warn() -> None:
    section = parse_hp_proliant_da_cntlr([["3", "52", "3", "2", "1", "19", "2", "PXXXX0BRH6X59X"]])

    assert list(check_hp_proliant_da_cntlr("3", DEFAULT_PARAMETERS, section)) == [
        Result(state=State.OK, summary="Condition: ok"),
        Result(state=State.OK, summary="Board-Condition: ok"),
        Result(state=State.WARN, summary="Board-Status: updating"),
        Result(
            state=State.OK,
            summary="Role: other, Model: 52, Slot: 3, Serial: PXXXX0BRH6X59X",
        ),
    ]


def test_other_board_condition_is_warn_and_explained() -> None:
    section = parse_hp_proliant_da_cntlr([["6", "1", "6", "2", "1", "8", "1", "PEYHN0ARCC307J"]])

    assert list(check_hp_proliant_da_cntlr("6", DEFAULT_PARAMETERS, section)) == [
        Result(state=State.OK, summary="Condition: ok"),
        Result(state=State.WARN, summary="Board-Condition: other"),
        Result(state=State.OK, summary="Board-Status: enabled"),
        Result(
            state=State.OK,
            summary="Role: other, Model: 1, Slot: 6, Serial: PEYHN0ARCC307J",
        ),
        Result(
            state=State.OK,
            notice="The instrument agent does not recognize the status of the controller. You may need to upgrade the instrument agent.",
        ),
    ]


def test_configured_state_replaces_default() -> None:
    section = parse_hp_proliant_da_cntlr([["6", "1", "6", "2", "1", "8", "1", "PEYHN0ARCC307J"]])
    params: Params = {
        "condition": DEFAULT_PARAMETERS["condition"],
        "board_condition": {"other": State.OK.value},
        "board_status": DEFAULT_PARAMETERS["board_status"],
    }

    assert list(check_hp_proliant_da_cntlr("6", params, section))[1] == Result(
        state=State.OK, summary="Board-Condition: other"
    )


def test_unconfigured_values_keep_default() -> None:
    section = parse_hp_proliant_da_cntlr([["3", "52", "3", "3", "1", "2", "2", "PXXXX0BRH6X59X"]])
    params: Params = {
        "condition": {"other": State.OK.value},
        "board_condition": DEFAULT_PARAMETERS["board_condition"],
        "board_status": DEFAULT_PARAMETERS["board_status"],
    }

    assert list(check_hp_proliant_da_cntlr("3", params, section))[0] == Result(
        state=State.WARN, summary="Condition: degraded"
    )
