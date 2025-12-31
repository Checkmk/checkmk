#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.base.legacy_checks.poseidon_inputs import (
    check_poseidon_inputs,
    discover_poseidon_inputs,
    parse_poseidon_inputs,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                ["1", "Bezeichnung Eingang 1", "1", "0"],
                ["0", "Bezeichnung Eingang 2", "2", "0"],
                ["0", "Bezeichnung Eingang 3", "1", "1"],
                ["0", "Bezeichnung Eingang 4", "1", "1"],
                ["0", "Comm Monitor 1", "0", "0"],
            ],
            [
                Service(item="Bezeichnung Eingang 1"),
                Service(item="Bezeichnung Eingang 2"),
                Service(item="Bezeichnung Eingang 3"),
                Service(item="Bezeichnung Eingang 4"),
                Service(item="Comm Monitor 1"),
            ],
        ),
    ],
)
def test_discover_poseidon_inputs(
    string_table: StringTable, expected_discoveries: Sequence[Service]
) -> None:
    parsed = parse_poseidon_inputs(string_table)
    assert parsed is not None
    assert list(discover_poseidon_inputs(parsed)) == expected_discoveries


@pytest.mark.parametrize(
    "item, string_table, expected_results",
    [
        (
            "Bezeichnung Eingang 1",
            [
                ["1", "Bezeichnung Eingang 1", "1", "0"],
                ["0", "Bezeichnung Eingang 2", "2", "0"],
                ["0", "Bezeichnung Eingang 3", "1", "1"],
                ["0", "Bezeichnung Eingang 4", "1", "1"],
                ["0", "Comm Monitor 1", "0", "0"],
            ],
            [
                Result(state=State.OK, summary="Bezeichnung Eingang 1: AlarmSetup: activeOff"),
                Result(state=State.OK, summary="Alarm State: normal"),
                Result(state=State.OK, summary="Values on"),
            ],
        ),
        (
            "Bezeichnung Eingang 2",
            [
                ["1", "Bezeichnung Eingang 1", "1", "0"],
                ["0", "Bezeichnung Eingang 2", "2", "0"],
                ["0", "Bezeichnung Eingang 3", "1", "1"],
                ["0", "Bezeichnung Eingang 4", "1", "1"],
                ["0", "Comm Monitor 1", "0", "0"],
            ],
            [
                Result(state=State.OK, summary="Bezeichnung Eingang 2: AlarmSetup: activeOn"),
                Result(state=State.OK, summary="Alarm State: normal"),
                Result(state=State.OK, summary="Values off"),
            ],
        ),
        (
            "Bezeichnung Eingang 3",
            [
                ["1", "Bezeichnung Eingang 1", "1", "0"],
                ["0", "Bezeichnung Eingang 2", "2", "0"],
                ["0", "Bezeichnung Eingang 3", "1", "1"],
                ["0", "Bezeichnung Eingang 4", "1", "1"],
                ["0", "Comm Monitor 1", "0", "0"],
            ],
            [
                Result(state=State.OK, summary="Bezeichnung Eingang 3: AlarmSetup: activeOff"),
                Result(state=State.CRIT, summary="Alarm State: alarm"),
                Result(state=State.OK, summary="Values off"),
            ],
        ),
        (
            "Bezeichnung Eingang 4",
            [
                ["1", "Bezeichnung Eingang 1", "1", "0"],
                ["0", "Bezeichnung Eingang 2", "2", "0"],
                ["0", "Bezeichnung Eingang 3", "1", "1"],
                ["0", "Bezeichnung Eingang 4", "1", "1"],
                ["0", "Comm Monitor 1", "0", "0"],
            ],
            [
                Result(state=State.OK, summary="Bezeichnung Eingang 4: AlarmSetup: activeOff"),
                Result(state=State.CRIT, summary="Alarm State: alarm"),
                Result(state=State.OK, summary="Values off"),
            ],
        ),
        (
            "Comm Monitor 1",
            [
                ["1", "Bezeichnung Eingang 1", "1", "0"],
                ["0", "Bezeichnung Eingang 2", "2", "0"],
                ["0", "Bezeichnung Eingang 3", "1", "1"],
                ["0", "Bezeichnung Eingang 4", "1", "1"],
                ["0", "Comm Monitor 1", "0", "0"],
            ],
            [
                Result(state=State.OK, summary="Comm Monitor 1: AlarmSetup: inactive"),
                Result(state=State.OK, summary="Alarm State: normal"),
                Result(state=State.OK, summary="Values off"),
            ],
        ),
    ],
)
def test_check_poseidon_inputs(
    item: str, string_table: StringTable, expected_results: Sequence[Result]
) -> None:
    parsed = parse_poseidon_inputs(string_table)
    assert parsed is not None
    assert list(check_poseidon_inputs(item, parsed)) == expected_results
