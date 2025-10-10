#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.base.legacy_checks.ibm_storage_ts import (
    check_ibm_storage_ts,
    inventory_ibm_storage_ts,
    parse_ibm_storage_ts,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                [["3100 Storage", "IBM", "v1.2.3"]],
                ["3"],
                [
                    ["0", "3", "1234567890", "2", "0", "2", ""],
                    ["1", "3", "1234567891", "2", "2", "2", "Message 2"],
                ],
                [["0", "9876543210", "0", "0", "0", "0"], ["1", "9876543211", "3", "4", "5", "6"]],
            ],
            [(None, None)],
        ),
    ],
)
def test_inventory_ibm_storage_ts(
    string_table: Sequence[list[list[str]]],
    expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]],
) -> None:
    """Test discovery function for ibm_storage_ts check."""
    parsed = parse_ibm_storage_ts(string_table)
    result = list(inventory_ibm_storage_ts(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            None,
            {},
            [
                [["3100 Storage", "IBM", "v1.2.3"]],
                ["3"],
                [
                    ["0", "3", "1234567890", "2", "0", "2", ""],
                    ["1", "3", "1234567891", "2", "2", "2", "Message 2"],
                ],
                [["0", "9876543210", "0", "0", "0", "0"], ["1", "9876543211", "3", "4", "5", "6"]],
            ],
            [0, "IBM 3100 Storage, Version v1.2.3"],
        ),
    ],
)
def test_check_ibm_storage_ts(
    item: str,
    params: Mapping[str, Any],
    string_table: Sequence[list[list[str]]],
    expected_results: Sequence[Any],
) -> None:
    """Test check function for ibm_storage_ts check."""
    parsed = parse_ibm_storage_ts(string_table)
    result = list(check_ibm_storage_ts(item, params, parsed))
    assert result == expected_results
