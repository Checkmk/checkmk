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
from cmk.base.legacy_checks.netscaler_mem import (
    check_netscaler_mem,
    discover_netscaler_mem,
    parse_netscaler_mem,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        ([["4.2", "23"]], [(None, {})]),
    ],
)
def test_discover_netscaler_mem(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for netscaler_mem check."""
    parsed = parse_netscaler_mem(string_table)
    result = list(discover_netscaler_mem(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            None,
            {"levels": (80.0, 90.0)},
            [["4.2", "23"]],
            [
                (
                    0,
                    "Usage: 4.20% - 989 KiB of 23.0 MiB",
                    [
                        (
                            "mem_used",
                            1012924.4160000001,
                            19293798.400000002,
                            21705523.2,
                            0,
                            24117248.0,
                        )
                    ],
                )
            ],
        ),
    ],
)
def test_check_netscaler_mem(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for netscaler_mem check."""
    parsed = parse_netscaler_mem(string_table)
    result = list(check_netscaler_mem(item, params, parsed))
    assert result == expected_results
