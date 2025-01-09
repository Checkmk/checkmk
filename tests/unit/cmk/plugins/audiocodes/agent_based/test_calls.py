#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.agent_based.v2 import CheckResult, FixedLevelsT, Metric, NoLevelsT, Result, Service, State
from cmk.plugins.audiocodes.agent_based.calls import (
    Calls,
    check_audiocodes_calls_testable,
    discover_audiocodes_calls,
    parse_audiocodes_calls,
)


def _parsed_section() -> Calls:
    calls = parse_audiocodes_calls([[["1332", "1130325", "85", "231"]], [["22", "12"]]])
    assert calls
    return calls


def test_parse_function() -> None:
    assert parse_audiocodes_calls([[], [["22", "12"]]]) is None


def test_discovery_function() -> None:
    assert list(discover_audiocodes_calls(_parsed_section())) == [Service()]


@pytest.mark.parametrize(
    "params, expected",
    [
        pytest.param(
            {},
            [
                Result(state=State.OK, summary="Active Calls: 1332.00"),
                Metric("audiocodes_active_calls", 1332.0),
                Result(state=State.OK, summary="Calls per Second: 18816.50/s"),
                Metric("audiocodes_calls_per_sec", 18816.5),
                Result(state=State.OK, summary="Average Succes Ratio: 85.00%"),
                Metric("audiocodes_average_success_ratio", 85.0),
                Result(state=State.OK, summary="Average Call Duration: 3 minutes 51 seconds"),
                Metric("audiocodes_average_call_duration", 231.0),
                Result(state=State.OK, notice="Active Calls In: 22.00"),
                Metric("audiocodes_active_calls_in", 22.0),
                Result(state=State.OK, notice="Active Calls Out: 12.00"),
                Metric("audiocodes_active_calls_out", 12.0),
            ],
            id="No params. Everything OK",
        ),
        pytest.param(
            {"asr_lower_levels": ("fixed", (90.0, 80.0))},
            [
                Result(state=State.OK, summary="Active Calls: 1332.00"),
                Metric("audiocodes_active_calls", 1332.0),
                Result(state=State.OK, summary="Calls per Second: 18816.50/s"),
                Metric("audiocodes_calls_per_sec", 18816.5),
                Result(
                    state=State.WARN,
                    summary="Average Succes Ratio: 85.00% (warn/crit below 90.00%/80.00%)",
                ),
                Metric("audiocodes_average_success_ratio", 85.0),
                Result(state=State.OK, summary="Average Call Duration: 3 minutes 51 seconds"),
                Metric("audiocodes_average_call_duration", 231.0),
                Result(state=State.OK, notice="Active Calls In: 22.00"),
                Metric("audiocodes_active_calls_in", 22.0),
                Result(state=State.OK, notice="Active Calls Out: 12.00"),
                Metric("audiocodes_active_calls_out", 12.0),
            ],
            id="Average Success Ratio WARN",
        ),
        pytest.param(
            {"asr_lower_levels": ("fixed", (90.0, 86.0))},
            [
                Result(state=State.OK, summary="Active Calls: 1332.00"),
                Metric("audiocodes_active_calls", 1332.0),
                Result(state=State.OK, summary="Calls per Second: 18816.50/s"),
                Metric("audiocodes_calls_per_sec", 18816.5),
                Result(
                    state=State.CRIT,
                    summary="Average Succes Ratio: 85.00% (warn/crit below 90.00%/86.00%)",
                ),
                Metric("audiocodes_average_success_ratio", 85.0),
                Result(state=State.OK, summary="Average Call Duration: 3 minutes 51 seconds"),
                Metric("audiocodes_average_call_duration", 231.0),
                Result(state=State.OK, notice="Active Calls In: 22.00"),
                Metric("audiocodes_active_calls_in", 22.0),
                Result(state=State.OK, notice="Active Calls Out: 12.00"),
                Metric("audiocodes_active_calls_out", 12.0),
            ],
            id="Average Success Ratio CRIT",
        ),
    ],
)
def test_check_function(
    params: Mapping[str, NoLevelsT | FixedLevelsT],
    expected: CheckResult,
) -> None:
    now = 1731363504
    value_store = {"total_calls": (now - 60, 1335)}
    assert (
        list(
            check_audiocodes_calls_testable(
                params=params,
                section=_parsed_section(),
                now=now,
                value_store=value_store,
            ),
        )
        == expected
    )
