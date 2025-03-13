#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import CheckResult, Result, Service, State, StringTable
from cmk.plugins.audiocodes.agent_based.system_events import (
    check_audiocodes_system_events,
    discover_audiocodes_system_events,
    parse_audiocodes_system_events,
)

_STRING_TABLE = [
    [
        ["1", "512321", "07 E5 08 02 14 28 38 00 ", "Alarm1", "Description1", "Source1", "5"],
        ["2", "221311", "07 E5 08 02 14 28 38 00 ", "Alarm2", "Description2", "Source2", "3"],
    ],
    [["1"], ["2"], ["3"], ["4"], ["5"], ["6"], ["7"], ["8"], ["9"], ["10"]],
]
_STRING_TABLE_WITH_BYTES = [
    [["1", "512321", "\x07å\x08\x02\x14(8\x00", "name", "description", "source", "5"]],
    [["1"], ["2"], ["3"], ["4"], ["5"], ["6"], ["7"], ["8"], ["9"], ["10"]],
]

_DEFAULT_PARAMS = {
    "severity_state_mapping": {
        "cleared": 0,
        "indeterminate": 3,
        "warning": 1,
        "minor": 1,
        "major": 2,
        "critical": 2,
    }
}


def test_discovery_function() -> None:
    assert list(
        discover_audiocodes_system_events(parse_audiocodes_system_events(_STRING_TABLE))
    ) == [Service()]


@pytest.mark.parametrize(
    "params, string_table, expected",
    [
        pytest.param(
            _DEFAULT_PARAMS,
            _STRING_TABLE,
            [
                Result(state=State.OK, summary="Critical alarms: 1, Warnings: 1"),
                Result(state=State.OK, summary="Archived: 10"),
                Result(
                    state=State.CRIT,
                    summary="Alarm #1: Name: Alarm1, Severity: critical, Sysuptime: 5 days 22 hours, Description: Description1, Source: Source1, Date and Time: 2021-08-02 20:40:56",
                ),
                Result(
                    state=State.WARN,
                    summary="Alarm #2: Name: Alarm2, Severity: minor, Sysuptime: 2 days 13 hours, Description: Description2, Source: Source2, Date and Time: 2021-08-02 20:40:56",
                ),
            ],
            id="Default params. One critical and one warning alarm",
        ),
        pytest.param(
            {
                "severity_state_mapping": {
                    "cleared": 0,
                    "indeterminate": 0,
                    "warning": 0,
                    "minor": 0,
                    "major": 0,
                    "critical": 0,
                }
            },
            _STRING_TABLE,
            [
                Result(state=State.OK, summary="Critical alarms: 0, Warnings: 0"),
                Result(state=State.OK, summary="Archived: 10"),
                Result(
                    state=State.OK,
                    notice="Alarm #1: Name: Alarm1, Severity: critical, Sysuptime: 5 days 22 hours, Description: Description1, Source: Source1, Date and Time: 2021-08-02 20:40:56",
                ),
                Result(
                    state=State.OK,
                    notice="Alarm #2: Name: Alarm2, Severity: minor, Sysuptime: 2 days 13 hours, Description: Description2, Source: Source2, Date and Time: 2021-08-02 20:40:56",
                ),
            ],
            id="User-defined params. All severity levels are mapped to OK",
        ),
        pytest.param(
            _DEFAULT_PARAMS,
            _STRING_TABLE_WITH_BYTES,
            [
                Result(state=State.OK, summary="Critical alarms: 1, Warnings: 0"),
                Result(state=State.OK, summary="Archived: 10"),
                Result(
                    state=State.CRIT,
                    summary="Alarm #1: Name: name, Severity: critical, Sysuptime: 5 days 22 hours, Description: description, Source: source, Date and Time: 2021-08-02 20:40:56",
                ),
            ],
            id="String table with bytes",
        ),
    ],
)
def test_check_function(
    params: Mapping[str, Mapping[str, int]],
    string_table: Sequence[StringTable],
    expected: CheckResult,
) -> None:
    assert (
        list(check_audiocodes_system_events(params, parse_audiocodes_system_events(string_table)))
        == expected
    )
