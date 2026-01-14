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
from cmk.base.legacy_checks.heartbeat_rscstatus import (
    check_heartbeat_rscstatus,
    discover_heartbeat_rscstatus,
    parse_heartbeat_rscstatus,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        ([["all"]], [(None, {"discovered_state": "all"})]),
    ],
)
def test_discover_heartbeat_rscstatus(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for heartbeat_rscstatus check."""
    parsed = parse_heartbeat_rscstatus(string_table)
    result = list(discover_heartbeat_rscstatus(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (None, {"discovered_state": "all"}, [["all"]], [(0, "Current state: all")]),
        (
            None,
            {"discovered_state": "local"},
            [["all"]],
            [(2, "Current state: all (Expected: local)")],
        ),
        (None, '"all"', [["all"]], [(0, "Current state: all")]),
        (None, '"local"', [["all"]], [(2, "Current state: all (Expected: local)")]),
    ],
)
def test_check_heartbeat_rscstatus(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for heartbeat_rscstatus check."""
    parsed = parse_heartbeat_rscstatus(string_table)
    result = list(check_heartbeat_rscstatus(item, params, parsed))
    assert result == expected_results
