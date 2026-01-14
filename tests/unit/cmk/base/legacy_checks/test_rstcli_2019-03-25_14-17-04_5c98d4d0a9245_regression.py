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
from cmk.base.legacy_checks.rstcli import (
    check_rstcli,
    check_rstcli_pdisks,
    discover_rstcli,
    discover_rstcli_pdisks,
    parse_rstcli,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [["rstcli not found"]],  # rstcli command not available
            [],  # Should discover nothing when rstcli not found
        ),
    ],
)
def test_discover_rstcli_regression(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str | None, Mapping[str, Any]]]
) -> None:
    """Test discovery function for rstcli regression test."""
    parsed = parse_rstcli(string_table)
    result = list(discover_rstcli(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [["rstcli not found"]],  # rstcli command not available
            [],  # Should discover nothing when rstcli not found
        ),
    ],
)
def test_discover_rstcli_pdisks_regression(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str | None, Mapping[str, Any]]]
) -> None:
    """Test pdisks discovery function for rstcli regression test."""
    parsed = parse_rstcli(string_table)
    result = list(discover_rstcli_pdisks(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_result_length",
    [
        (
            "nonexistent_volume",
            {},
            [["rstcli not found"]],
            0,  # No check results when rstcli not found
        ),
    ],
)
def test_check_rstcli_regression(
    item: str | None,
    params: Mapping[str, Any],
    string_table: StringTable,
    expected_result_length: int,
) -> None:
    """Test check function for rstcli regression test."""
    parsed = parse_rstcli(string_table)
    result = list(check_rstcli(item, params, parsed))

    # When rstcli is not found, check should return empty list
    assert len(result) == expected_result_length


@pytest.mark.parametrize(
    "item, params, string_table, expected_result",
    [
        (
            "nonexistent/disk",
            {},
            [["rstcli not found"]],
            None,  # No check result when rstcli not found
        ),
    ],
)
def test_check_rstcli_pdisks_regression(
    item: str | None, params: Mapping[str, Any], string_table: StringTable, expected_result: Any
) -> None:
    """Test pdisks check function for rstcli regression test."""
    parsed = parse_rstcli(string_table)
    result = check_rstcli_pdisks(item, params, parsed)

    # When rstcli is not found, check should return None
    assert result == expected_result
