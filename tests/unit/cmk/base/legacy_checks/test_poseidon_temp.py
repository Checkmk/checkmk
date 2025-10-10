#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.legacy_checks.poseidon_temp import (
    check_poseidon_temp,
    discover_poseidon_temp,
    parse_poseidon_temp,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        ([["Bezeichnung Sensor 1", "1", "16.8 C"]], [("Bezeichnung Sensor 1", {})]),
    ],
)
def test_discover_poseidon_temp(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for poseidon_temp check."""
    parsed = parse_poseidon_temp(string_table)
    result = list(discover_poseidon_temp(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "Bezeichnung Sensor 1",
            {},
            [["Bezeichnung Sensor 1", "1", "16.8 C"]],
            [
                (0, "Sensor Bezeichnung Sensor 1, State normal"),
                (0, "16.8 °C", [("temp", 16.8, None, None)]),
            ],
        ),
    ],
)
def test_check_poseidon_temp(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for poseidon_temp check."""
    parsed = parse_poseidon_temp(string_table)
    result = list(check_poseidon_temp(item, params, parsed))
    assert result == expected_results
