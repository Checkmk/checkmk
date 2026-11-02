#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.agent_based.v2 import CheckResult, Result, Service, State, StringTable
from cmk.plugins.audiocodes.agent_based.overall_operational_state import (
    check_audiocodes_overall_operational_state,
    discover_audiocodes_overall_operational_state,
    parse_audiocodes_overall_operational_state,
)


def test_discovery_function() -> None:
    section = parse_audiocodes_overall_operational_state([["2", "0", "", "0"]])
    assert section is not None
    assert list(discover_audiocodes_overall_operational_state(section)) == [Service()]


@pytest.mark.parametrize(
    "string_table, expected",
    [
        pytest.param(
            [["2", "0", "", "0"]],
            [
                Result(state=State.OK, summary="Highest alarm severity: No alarm"),
                Result(state=State.OK, notice="Operational state: Enabled"),
            ],
            id="no alarm, error ID 0 is not shown",
        ),
        pytest.param(
            [["2", "4", "", "0"]],
            [
                Result(state=State.CRIT, summary="Highest alarm severity: Major"),
                Result(state=State.OK, notice="Operational state: Enabled"),
            ],
            id="major alarm without error message",
        ),
        pytest.param(
            [["1", "2", "Some error message", "1"]],
            [
                Result(state=State.WARN, summary="Highest alarm severity: Warning"),
                Result(state=State.CRIT, summary="Operational state: Disabled"),
                Result(state=State.OK, notice="Error message: Some error message"),
                Result(state=State.OK, notice="Error ID: 1"),
            ],
            id="disabled device with error message and error ID",
        ),
        pytest.param(
            [["2", "0", "NOTIC:some log", "0"]],
            [
                Result(state=State.OK, summary="Highest alarm severity: No alarm"),
                Result(state=State.OK, notice="Operational state: Enabled"),
                Result(state=State.OK, notice="Error message: NOTIC:some log"),
            ],
            id="error message without error ID",
        ),
        pytest.param(
            [["2", "0", "", ""]],
            [
                Result(state=State.OK, summary="Highest alarm severity: No alarm"),
                Result(state=State.OK, notice="Operational state: Enabled"),
            ],
            id="empty error ID is not shown",
        ),
    ],
)
def test_check_function(
    string_table: StringTable,
    expected: CheckResult,
) -> None:
    section = parse_audiocodes_overall_operational_state(string_table)
    assert section is not None
    assert list(check_audiocodes_overall_operational_state(section)) == expected
