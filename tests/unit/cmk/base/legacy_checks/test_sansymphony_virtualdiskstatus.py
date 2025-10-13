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
from cmk.base.legacy_checks.sansymphony_virtualdiskstatus import (
    check_sansymphony_virtualdiskstatus,
    discover_sansymphony_virtualdiskstatus,
    parse_sansymphony_virtualdiskstatus,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [["testvmfs01", "Online"], ["vmfs01", "anything", "else"]],
            [("testvmfs01", {}), ("vmfs01", {})],
        ),
    ],
)
def test_discover_sansymphony_virtualdiskstatus(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for sansymphony_virtualdiskstatus check."""
    parsed = parse_sansymphony_virtualdiskstatus(string_table)
    result = list(discover_sansymphony_virtualdiskstatus(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "testvmfs01",
            {},
            [["testvmfs01", "Online"], ["vmfs01", "anything", "else"]],
            [(0, "Volume state is: Online")],
        ),
        (
            "vmfs01",
            {},
            [["testvmfs01", "Online"], ["vmfs01", "anything", "else"]],
            [(2, "Volume state is: anything else")],
        ),
    ],
)
def test_check_sansymphony_virtualdiskstatus(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for sansymphony_virtualdiskstatus check."""
    parsed = parse_sansymphony_virtualdiskstatus(string_table)
    result = list(check_sansymphony_virtualdiskstatus(item, params, parsed))
    assert result == expected_results
