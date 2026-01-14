#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import StringTable
from cmk.base.legacy_checks.enterasys_powersupply import (
    check_enterasys_powersupply,
    discover_enterasys_powersupply,
    parse_enterasys_powersupply,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [["101", "3", "1", "1"], ["102", "", "", "1"]],
            [("101", {})],  # Only PSU 101 has state "3" (installed and operating)
        ),
    ],
)
def test_discover_enterasys_powersupply_regression(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for enterasys_powersupply regression test."""
    parsed = parse_enterasys_powersupply(string_table)
    result = list(discover_enterasys_powersupply(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_status",
    [
        (
            "101",
            {"redundancy_ok_states": [1]},
            [["101", "3", "1", "1"], ["102", "", "", "1"]],
            "working and redundant (ac-dc)",  # PSU 101: state=3, type=1 (ac-dc), redundancy=1 (redundant)
        ),
    ],
)
def test_check_enterasys_powersupply_regression(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_status: str
) -> None:
    """Test check function for enterasys_powersupply regression test."""
    parsed = parse_enterasys_powersupply(string_table)
    result = check_enterasys_powersupply(item, params, parsed)

    # Check that we get a valid result tuple
    assert result is not None
    assert len(result) >= 2

    state, message = result[0], result[1]

    # Check that the state is OK (0) and message contains expected status
    assert state == 0, f"Expected state 0 (OK), got {state}"
    assert expected_status in message, f"Expected '{expected_status}' in message '{message}'"
