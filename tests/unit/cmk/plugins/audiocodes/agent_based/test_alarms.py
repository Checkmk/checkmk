#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.agent_based.v2 import CheckResult, Result, Service, State
from cmk.plugins.audiocodes.agent_based.alarms import (
    check_audiocodes_alarms,
    discover_audiocodes_alarms,
    parse_audiocodes_alarms,
)

_STRING_TABLE = [
    [
        ["1", "512321", "07 E5 08 02 14 28 38 00 ", "Alarm1", "Description1", "Source1", "5"],
        ["2", "221311", "07 E5 08 02 14 28 38 00 ", "Alarm2", "Description2", "Source2", "3"],
    ],
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
    assert list(discover_audiocodes_alarms(parse_audiocodes_alarms(_STRING_TABLE))) == [Service()]


@pytest.mark.parametrize(
    "params, expected",
    [
        pytest.param(
            _DEFAULT_PARAMS,
            [
                Result(state=State.OK, summary="Critical alarms: 1, Warning alarms: 1"),
                Result(state=State.OK, summary="Archived alarms: 10"),
                Result(
                    state=State.CRIT,
                    summary="Alarm #1: Name: Alarm1, Severity: critical, Sysuptime: 5 days 22 hours, Date and Time: 2021-08-02 20:40:56, Description: Description1, Source: Source1",
                ),
                Result(
                    state=State.WARN,
                    summary="Alarm #2: Name: Alarm2, Severity: minor, Sysuptime: 2 days 13 hours, Date and Time: 2021-08-02 20:40:56, Description: Description2, Source: Source2",
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
            [
                Result(state=State.OK, summary="Critical alarms: 0, Warning alarms: 0"),
                Result(state=State.OK, summary="Archived alarms: 10"),
                Result(
                    state=State.OK,
                    notice="Alarm #1: Name: Alarm1, Severity: critical, Sysuptime: 5 days 22 hours, Date and Time: 2021-08-02 20:40:56, Description: Description1, Source: Source1",
                ),
                Result(
                    state=State.OK,
                    notice="Alarm #2: Name: Alarm2, Severity: minor, Sysuptime: 2 days 13 hours, Date and Time: 2021-08-02 20:40:56, Description: Description2, Source: Source2",
                ),
            ],
            id="User-defined params. All severity levels are mapped to OK",
        ),
    ],
)
def test_check_function(
    params: Mapping[str, Mapping[str, int]],
    expected: CheckResult,
) -> None:
    assert list(check_audiocodes_alarms(params, parse_audiocodes_alarms(_STRING_TABLE))) == expected
