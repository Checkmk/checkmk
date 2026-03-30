#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, State, StringTable
from cmk.plugins.pulse_secure.agent_based.pulse_secure_disk_util import (
    check_pulse_secure_disk_util,
    discover_pulse_secure_disk_util,
    parse_pulse_secure_disk_util,
    PulseSecureDiskUtilParams,
)


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
    "params, string_table, expected_state, expected_summary_substring",
    [
        (
            {"upper_levels": (80.0, 90.0)},
            [["7"]],
            State.OK,
            "Percentage of disk space used",
        ),
    ],
)
def test_check_pulse_secure_disk(
    params: PulseSecureDiskUtilParams,
    string_table: StringTable,
    expected_state: State,
    expected_summary_substring: str,
) -> None:
    """Test check function for pulse_secure_disk_util check."""
    parsed = parse_pulse_secure_disk_util(string_table)
    assert parsed is not None
    results = list(check_pulse_secure_disk_util(params, parsed))
    result_objs = [r for r in results if isinstance(r, Result)]
    metric_objs = [r for r in results if isinstance(r, Metric)]
    assert len(result_objs) == 1
    assert result_objs[0].state == expected_state
    assert expected_summary_substring in result_objs[0].summary
    assert len(metric_objs) == 1
    assert metric_objs[0].name == "disk_utilization"
