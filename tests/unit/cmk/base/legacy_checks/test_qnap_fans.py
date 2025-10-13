#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.legacy_checks.qnap_fans import check_qnap_fans, discover_qnap_fans, parse_qnap_fans


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        ([["1", "1027 RPM"], ["2", "968 RPM"]], [("1", {}), ("2", {})]),
    ],
)
def test_discover_qnap_fans(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for qnap_fans check."""
    parsed = parse_qnap_fans(string_table)
    result = list(discover_qnap_fans(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "1",
            {"upper": (6000, 6500), "lower": (None, None)},
            [["1", "1027 RPM"], ["2", "968 RPM"]],
            [(0, "Speed: 1027 RPM", [])],
        ),
        (
            "2",
            {"upper": (6000, 6500), "lower": (None, None)},
            [["1", "1027 RPM"], ["2", "968 RPM"]],
            [(0, "Speed: 968 RPM", [])],
        ),
    ],
)
def test_check_qnap_fans(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for qnap_fans check."""
    parsed = parse_qnap_fans(string_table)
    result = list(check_qnap_fans(item, params, parsed))
    assert result == expected_results
