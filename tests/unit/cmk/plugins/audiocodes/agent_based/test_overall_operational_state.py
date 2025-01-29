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
                Result(state=State.OK, summary="Gateway: No alarm"),
                Result(state=State.OK, notice="Error message: (empty)\nError ID: 0"),
            ],
            id="Everything OK. No Error messages",
        ),
        pytest.param(
            [["1", "2", "Some error message", "1"]],
            [
                Result(state=State.WARN, summary="Gateway: Warning"),
                Result(
                    state=State.CRIT,
                    summary="Highest alarm severity: Disabled",
                    details="Error message: Some error message\nError ID: 1",
                ),
            ],
            id="CRIT operational state, WARN gw severity, error message",
        ),
        pytest.param(
            [["2", "0", "", ""]],
            [
                Result(state=State.OK, summary="Gateway: No alarm"),
                Result(state=State.OK, notice="Highest alarm severity: Enabled"),
            ],
            id="OK operational state, OK gw severity, no error message",
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
