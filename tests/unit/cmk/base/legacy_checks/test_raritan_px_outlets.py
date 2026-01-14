#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import StringTable
from cmk.base.legacy_checks.raritan_px_outlets import (
    check_raritan_px_outlets,
    discover_raritan_px_outlets,
    parse_raritan_px_outlets,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [["3", "label", "1", "3", "3", "3", "3", "3"], ["2", "", "1", "3", "3", "3", "3", "3"]],
            [("3", {}), ("2", {})],
        ),
    ],
)
def test_discover_raritan_px_outlets(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for raritan_px_outlets check."""
    parsed = parse_raritan_px_outlets(string_table)
    result = list(discover_raritan_px_outlets(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "3",
            {},
            [["3", "label", "1", "3", "3", "3", "3", "3"], ["2", "", "1", "3", "3", "3", "3", "3"]],
            [
                (0, "[label]"),
                (0, "Device status: on(0)"),
                (0, "Voltage: 0.0 V", [("voltage", 0.003, None, None)]),
                (0, "Current: 0.0 A", [("current", 0.003, None, None)]),
                (0, "Power: 3.0 W", [("power", 3.0, None, None)]),
                (0, "Apparent Power: 3.0 VA", [("appower", 3.0, None, None)]),
                (0, "Energy: 3.0 Wh", [("energy", 3.0, None, None)]),
            ],
        ),
        (
            "2",
            {},
            [["3", "label", "1", "3", "3", "3", "3", "3"], ["2", "", "1", "3", "3", "3", "3", "3"]],
            [
                (0, "Device status: on(0)"),
                (0, "Voltage: 0.0 V", [("voltage", 0.003, None, None)]),
                (0, "Current: 0.0 A", [("current", 0.003, None, None)]),
                (0, "Power: 3.0 W", [("power", 3.0, None, None)]),
                (0, "Apparent Power: 3.0 VA", [("appower", 3.0, None, None)]),
                (0, "Energy: 3.0 Wh", [("energy", 3.0, None, None)]),
            ],
        ),
    ],
)
def test_check_raritan_px_outlets(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for raritan_px_outlets check."""
    parsed = parse_raritan_px_outlets(string_table)
    result = list(check_raritan_px_outlets(item, params, parsed))
    assert result == expected_results
