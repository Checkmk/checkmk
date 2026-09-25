#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.checkengine.specs.parameters import Parameters
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


@pytest.mark.xfail(
    strict=True,
    reason="the check treats the Parameters mapping as legacy string params",
)
@pytest.mark.parametrize(
    "params, string_table, expected_results",
    [
        pytest.param(
            Parameters({"discovered_state": "all"}),
            [["all"]],
            [Result(state=State.OK, summary="Current state: all")],
            id="discovered state unchanged",
        ),
        pytest.param(
            Parameters({"discovered_state": "local"}),
            [["all"]],
            [Result(state=State.CRIT, summary="Current state: all (Expected: local)")],
            id="discovered state changed",
        ),
        pytest.param(
            Parameters({"discovered_state": "local", "expected_state": "all"}),
            [["all"]],
            [Result(state=State.OK, summary="Current state: all")],
            id="expected state from rule overrides discovered state",
        ),
        pytest.param(
            Parameters({"discovered_state": "all", "expected_state": "none"}),
            [["all"]],
            [Result(state=State.CRIT, summary="Current state: all (Expected: none)")],
            id="expected state from rule not met",
        ),
    ],
)
def test_check_heartbeat_rscstatus(
    params: Parameters,
    string_table: StringTable,
    expected_results: Sequence[Result],
) -> None:
    parsed = parse_heartbeat_rscstatus(string_table)
    result = list(check_heartbeat_rscstatus(params, parsed))
    assert result == expected_results
