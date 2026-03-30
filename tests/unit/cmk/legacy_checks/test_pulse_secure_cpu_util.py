#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, State, StringTable
from cmk.legacy_checks.pulse_secure_cpu_util import (
    check_pulse_secure_cpu,
    discover_pulse_secure_cpu_util,
    parse_pulse_secure_cpu_util,
)


@pytest.fixture
def empty_value_store(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "cmk.legacy_checks.pulse_secure_cpu_util.get_value_store",
        lambda: {},
    )


@pytest.mark.parametrize(
    "info, expected_discoveries",
    [
        ([["1"]], [True]),
    ],
)
def test_discover_pulse_secure_cpu(info: StringTable, expected_discoveries: Sequence[bool]) -> None:
    """Test discovery function for pulse_secure_cpu_util check."""
    parsed = parse_pulse_secure_cpu_util(info)
    if parsed is not None:
        result = list(discover_pulse_secure_cpu_util(parsed))
    else:
        result = []
    assert len(result) == len(expected_discoveries)


@pytest.mark.parametrize(
    "params, string_table, expected_state, expected_summary_substring",
    [
        (
            {"util": (80.0, 90.0)},
            [["1"]],
            State.OK,
            "Total CPU",
        ),
    ],
)
def test_check_pulse_secure_cpu(
    params: Mapping[str, object],
    string_table: StringTable,
    expected_state: State,
    expected_summary_substring: str,
    empty_value_store: None,
) -> None:
    """Test check function for pulse_secure_cpu_util check."""
    parsed = parse_pulse_secure_cpu_util(string_table)
    assert parsed is not None
    results = list(check_pulse_secure_cpu(params, parsed))
    result_objs = [r for r in results if isinstance(r, Result)]
    metric_objs = [r for r in results if isinstance(r, Metric)]
    assert len(result_objs) >= 1
    assert result_objs[0].state == expected_state
    assert expected_summary_substring in result_objs[0].summary
    assert len(metric_objs) >= 1
