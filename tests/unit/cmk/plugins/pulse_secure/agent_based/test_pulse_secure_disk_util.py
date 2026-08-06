#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, State, StringTable
from cmk.plugins.pulse_secure.agent_based.pulse_secure_disk_util import (
    check_pulse_secure_disk_util,
    discover_pulse_secure_disk_util,
    parse_pulse_secure_disk_util,
    PulseSecureDiskUtilParams,
)

PARAMS = PulseSecureDiskUtilParams(upper_levels=(80.0, 90.0))


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        ([["7"]], [True]),
    ],
)
def test_discover_pulse_secure_disk(
    string_table: StringTable, expected_discoveries: Sequence[bool]
) -> None:
    """Test discovery function for pulse_secure_disk_util check."""
    parsed = parse_pulse_secure_disk_util(string_table)
    if parsed is not None:
        result = list(discover_pulse_secure_disk_util(parsed))
    else:
        result = []
    assert len(result) == len(expected_discoveries)


@pytest.mark.parametrize(
    "utilization, expected_result",
    [
        pytest.param(
            "7",
            Result(state=State.OK, summary="Percentage of disk space used: 7.00%"),
            id="below_the_levels",
        ),
        pytest.param(
            "85",
            Result(
                state=State.WARN,
                summary="Percentage of disk space used: 85.00% (warn/crit at 80.00%/90.00%)",
            ),
            id="above_the_warn_level",
        ),
        pytest.param(
            "95",
            Result(
                state=State.CRIT,
                summary="Percentage of disk space used: 95.00% (warn/crit at 80.00%/90.00%)",
            ),
            id="above_the_crit_level",
        ),
    ],
)
def test_check_pulse_secure_disk(utilization: str, expected_result: Result) -> None:
    parsed = parse_pulse_secure_disk_util([[utilization]])
    assert parsed is not None

    assert list(check_pulse_secure_disk_util(PARAMS, parsed)) == [
        expected_result,
        Metric("disk_utilization", float(utilization), levels=(80.0, 90.0)),
    ]


def test_check_without_configured_levels() -> None:
    parsed = parse_pulse_secure_disk_util([["7"]])
    assert parsed is not None

    assert list(check_pulse_secure_disk_util(PulseSecureDiskUtilParams(), parsed)) == [
        Result(state=State.OK, summary="Percentage of disk space used: 7.00%"),
        Metric("disk_utilization", 7.0),
    ]
