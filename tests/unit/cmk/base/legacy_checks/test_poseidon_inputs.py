#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v1.type_defs import StringTable
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
                ("Bezeichnung Eingang 1", {}),
                ("Bezeichnung Eingang 2", {}),
                ("Bezeichnung Eingang 3", {}),
                ("Bezeichnung Eingang 4", {}),
                ("Comm Monitor 1", {}),
            ],
        ),
    ],
)
def test_discover_poseidon_inputs(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for poseidon_inputs check."""
    parsed = parse_poseidon_inputs(string_table)
    result = list(discover_poseidon_inputs(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "Bezeichnung Eingang 1",
            {},
            [
                ["1", "Bezeichnung Eingang 1", "1", "0"],
                ["0", "Bezeichnung Eingang 2", "2", "0"],
                ["0", "Bezeichnung Eingang 3", "1", "1"],
                ["0", "Bezeichnung Eingang 4", "1", "1"],
                ["0", "Comm Monitor 1", "0", "0"],
            ],
            [
                (0, "Bezeichnung Eingang 1: AlarmSetup: activeOff"),
                (0, "Alarm State: normal"),
                (0, "Values on"),
            ],
        ),
        (
            "Bezeichnung Eingang 2",
            {},
            [
                ["1", "Bezeichnung Eingang 1", "1", "0"],
                ["0", "Bezeichnung Eingang 2", "2", "0"],
                ["0", "Bezeichnung Eingang 3", "1", "1"],
                ["0", "Bezeichnung Eingang 4", "1", "1"],
                ["0", "Comm Monitor 1", "0", "0"],
            ],
            [
                (0, "Bezeichnung Eingang 2: AlarmSetup: activeOn"),
                (0, "Alarm State: normal"),
                (0, "Values off"),
            ],
        ),
        (
            "Bezeichnung Eingang 3",
            {},
            [
                ["1", "Bezeichnung Eingang 1", "1", "0"],
                ["0", "Bezeichnung Eingang 2", "2", "0"],
                ["0", "Bezeichnung Eingang 3", "1", "1"],
                ["0", "Bezeichnung Eingang 4", "1", "1"],
                ["0", "Comm Monitor 1", "0", "0"],
            ],
            [
                (0, "Bezeichnung Eingang 3: AlarmSetup: activeOff"),
                (2, "Alarm State: alarm"),
                (0, "Values off"),
            ],
        ),
        (
            "Bezeichnung Eingang 4",
            {},
            [
                ["1", "Bezeichnung Eingang 1", "1", "0"],
                ["0", "Bezeichnung Eingang 2", "2", "0"],
                ["0", "Bezeichnung Eingang 3", "1", "1"],
                ["0", "Bezeichnung Eingang 4", "1", "1"],
                ["0", "Comm Monitor 1", "0", "0"],
            ],
            [
                (0, "Bezeichnung Eingang 4: AlarmSetup: activeOff"),
                (2, "Alarm State: alarm"),
                (0, "Values off"),
            ],
        ),
        (
            "Comm Monitor 1",
            {},
            [
                ["1", "Bezeichnung Eingang 1", "1", "0"],
                ["0", "Bezeichnung Eingang 2", "2", "0"],
                ["0", "Bezeichnung Eingang 3", "1", "1"],
                ["0", "Bezeichnung Eingang 4", "1", "1"],
                ["0", "Comm Monitor 1", "0", "0"],
            ],
            [
                (0, "Comm Monitor 1: AlarmSetup: inactive"),
                (0, "Alarm State: normal"),
                (0, "Values off"),
            ],
        ),
    ],
)
def test_check_poseidon_inputs(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for poseidon_inputs check."""
    parsed = parse_poseidon_inputs(string_table)
    result = list(check_poseidon_inputs(item, params, parsed))
    assert result == expected_results
