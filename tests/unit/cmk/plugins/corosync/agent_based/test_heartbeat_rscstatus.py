#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.corosync.agent_based.heartbeat_rscstatus import (
    check_heartbeat_rscstatus,
    discover_heartbeat_rscstatus,
    parse_heartbeat_rscstatus,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        ([["all"]], [Service(parameters={"discovered_state": "all"})]),
    ],
)
def test_discover_heartbeat_rscstatus(
    string_table: StringTable, expected_discoveries: Sequence[Service]
) -> None:
    """Test discovery function for heartbeat_rscstatus check."""
    parsed = parse_heartbeat_rscstatus(string_table)
    result = list(discover_heartbeat_rscstatus(parsed))
    assert result == expected_discoveries


@pytest.mark.parametrize(
    "params, string_table, expected_results",
    [
        (
            {"discovered_state": "all"},
            [["all"]],
            [Result(state=State.OK, summary="Current state: all")],
        ),
        (
            {"discovered_state": "local"},
            [["all"]],
            [Result(state=State.CRIT, summary="Current state: all (Expected: local)")],
        ),
    ],
)
def test_check_heartbeat_rscstatus(
    params: Mapping[str, str],
    string_table: StringTable,
    expected_results: Sequence[Result],
) -> None:
    """Test check function for heartbeat_rscstatus check."""
    parsed = parse_heartbeat_rscstatus(string_table)
    result = list(check_heartbeat_rscstatus(params, parsed))
    assert result == expected_results
