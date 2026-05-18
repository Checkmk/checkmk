#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.citrix.agent_based.citrix_sessions import (
    check_citrix_sessions,
    discover_citrix_sessions,
    parse_citrix_sessions,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [["sessions", "1"], ["active_sessions", "1"], ["inactive_sessions", "0"]],
            [Service(parameters={"total": (60, 65), "active": (60, 65), "inactive": (10, 15)})],
        ),
    ],
)
def test_discover_citrix_sessions(
    string_table: StringTable,
    expected_discoveries: Sequence[Service],
) -> None:
    """Test discovery function for citrix_sessions check."""
    parsed = parse_citrix_sessions(string_table)
    result = list(discover_citrix_sessions(parsed))
    assert result == expected_discoveries


@pytest.mark.parametrize(
    "params, string_table, expected_results",
    [
        (
            {"active": (60, 65), "inactive": (10, 15), "total": (60, 65)},
            [["sessions", "1"], ["active_sessions", "1"], ["inactive_sessions", "0"]],
            [
                Result(state=State.OK, summary="Total: 1.00"),
                Metric("total", 1.0, levels=(60.0, 65.0)),
                Result(state=State.OK, summary="Active: 1.00"),
                Metric("active", 1.0, levels=(60.0, 65.0)),
                Result(state=State.OK, summary="Inactive: 0.00"),
                Metric("inactive", 0.0, levels=(10.0, 15.0)),
            ],
        ),
    ],
)
def test_check_citrix_sessions(
    params: Mapping[str, Any],
    string_table: StringTable,
    expected_results: Sequence[Result | Metric],
) -> None:
    """Test check function for citrix_sessions check."""
    parsed = parse_citrix_sessions(string_table)
    result = list(check_citrix_sessions(params, parsed))
    assert result == expected_results
