#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.enterasys.agent_based.enterasys_powersupply import (
    check_enterasys_powersupply,
    discover_enterasys_powersupply,
    parse_enterasys_powersupply,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [["101", "3", "1", "1"], ["102", "", "", "1"]],
            [Service(item="101")],  # Only PSU 101 has state "3" (installed and operating)
        ),
    ],
)
def test_discover_enterasys_powersupply_regression(
    string_table: StringTable, expected_discoveries: Sequence[Service]
) -> None:
    """Test discovery function for enterasys_powersupply regression test."""
    parsed = parse_enterasys_powersupply(string_table)
    assert list(discover_enterasys_powersupply(parsed)) == list(expected_discoveries)


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
    results = list(check_enterasys_powersupply(item, params, parsed))

    assert results, "Expected at least one result"
    first = results[0]
    assert isinstance(first, Result)
    assert first.state is State.OK, f"Expected state OK, got {first.state}"
    assert expected_status in first.summary, (
        f"Expected '{expected_status}' in summary '{first.summary}'"
    )
