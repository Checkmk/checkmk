#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from collections.abc import Mapping, Sequence
from typing import Any
from zoneinfo import ZoneInfo

import pytest
import time_machine

from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.legacy_checks.systemtime import check_systemtime, discover_systemtime
from cmk.plugins.collection.agent_based.systemtime import parse_systemtime


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        ([["1593509210"]], [(None, {})]),
    ],
)
def test_inventory_systemtime(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str | None, Mapping[str, Any]]]
) -> None:
    """Test discovery function for systemtime check."""
    parsed = parse_systemtime(string_table)
    result = list(discover_systemtime(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            None,
            {"levels": (30, 60)},
            [["1593509210"]],
            [
                (
                    2,
                    "Offset: 263 days 12 hours (warn/crit at 30 seconds/1 minute 0 seconds)",
                    [("offset", 22769275, 30, 60)],
                )
            ],
        ),
    ],
)
def test_check_systemtime(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for systemtime check."""
    with time_machine.travel(
        datetime.datetime.fromisoformat("2019-10-10 20:38:55").replace(tzinfo=ZoneInfo("UTC")),
        tick=False,
    ):
        parsed = parse_systemtime(string_table)
        result = list(check_systemtime(item, params, parsed))
        assert result == expected_results
