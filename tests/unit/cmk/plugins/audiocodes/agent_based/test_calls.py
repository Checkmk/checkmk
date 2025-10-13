#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="type-arg"

from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import (
    CheckResult,
    FixedLevelsT,
    Metric,
    NoLevelsT,
    Result,
    State,
    StringTable,
)
from cmk.plugins.audiocodes.agent_based.calls import (
    check_audiocodes_calls_testable,
    discover_audiocodes_calls,
    parse_audiocodes_calls,
)


def test_parse_function() -> None:
    assert parse_audiocodes_calls([[], [["22", "12"]]]) is None


@pytest.mark.parametrize(
    "string_table, num_services",
    [
        pytest.param(
            [[["247", "", "", "0", "0", "88", "94", "12", "12"]]],
            1,
            id="Missing active_calls_in and active_calls_out",
        ),
        pytest.param(
            [[["247", "151", "153", "0", "0", "88", "94", "12", "12"]]],
            1,
            id="Has all expected OIDs",
        ),
        pytest.param([[["", "", "", "", "", "", "94", "", ""]]], 1, id="Has only one expected OID"),
        # Service still gets yielded in this case, but not rendered because
        # there are no checks.
        pytest.param([[["", "", "", "", "", "", "", "", ""]]], 1, id="Missing all expected OIDs"),
    ],
)
def test_audiocodes_discovery_function(
    string_table: Sequence[StringTable], num_services: int
) -> None:
    calls = parse_audiocodes_calls(string_table)
    assert calls is not None
    assert len(list(discover_audiocodes_calls(calls))) == num_services


@pytest.mark.parametrize(
    "string_table, params, expected",
    [
        pytest.param(
            [[["247", "151", "153", "0", "0", "88", "94", "12", "11"]]],
            {},
            [
                Result(state=State.OK, notice="Average call duration: 4 minutes 7 seconds"),
                Metric("audiocodes_average_call_duration", 247.0),
                Result(state=State.OK, summary="Active calls in: 151"),
                Metric("audiocodes_active_calls_in", 151.0),
                Result(state=State.OK, summary="Active calls out: 153"),
                Metric("audiocodes_active_calls_out", 153.0),
                Result(state=State.OK, notice="Established calls in rate: 0.00/s"),
                Metric("audiocodes_established_calls_in", 0.0),
                Result(state=State.OK, notice="Established calls out rate: 0.00/s"),
                Metric("audiocodes_established_calls_out", 0.0),
                Result(state=State.OK, notice="Answer seizure ratio: 88.00%"),
                Metric("audiocodes_answer_seizure_ratio", 88.0),
                Result(state=State.OK, notice="Network effectiveness ratio: 94.00%"),
                Metric("audiocodes_network_effectiveness_ratio", 94.0),
                Result(state=State.OK, notice="Abnormal terminated calls in: 12"),
                Metric("audiocodes_abnormal_terminated_calls_in_total", 12.0),
                Result(state=State.OK, notice="Abnormal terminated calls out: 11"),
                Metric("audiocodes_abnormal_terminated_calls_out_total", 11.0),
            ],
            id="No params. Everything OK",
        ),
        pytest.param(
            [[["247", "151", "", "0", "0", "88", "94", "12", "11"]]],
            {},
            [
                Result(state=State.OK, notice="Average call duration: 4 minutes 7 seconds"),
                Metric("audiocodes_average_call_duration", 247.0),
                Result(state=State.OK, summary="Active calls in: 151"),
                Metric("audiocodes_active_calls_in", 151.0),
                Result(state=State.OK, notice="Established calls in rate: 0.00/s"),
                Metric("audiocodes_established_calls_in", 0.0),
                Result(state=State.OK, notice="Established calls out rate: 0.00/s"),
                Metric("audiocodes_established_calls_out", 0.0),
                Result(state=State.OK, notice="Answer seizure ratio: 88.00%"),
                Metric("audiocodes_answer_seizure_ratio", 88.0),
                Result(state=State.OK, notice="Network effectiveness ratio: 94.00%"),
                Metric("audiocodes_network_effectiveness_ratio", 94.0),
                Result(state=State.OK, notice="Abnormal terminated calls in: 12"),
                Metric("audiocodes_abnormal_terminated_calls_in_total", 12.0),
                Result(state=State.OK, notice="Abnormal terminated calls out: 11"),
                Metric("audiocodes_abnormal_terminated_calls_out_total", 11.0),
            ],
            id="Missing active_calls_out",
        ),
        pytest.param(
            [[["247", "151", "153", "0", "0", "88", "94", "12", "11"]]],
            {
                "network_effectiveness_ratio_lower_levels": ("fixed", (95.0, 90.0)),
            },
            [
                Result(state=State.OK, notice="Average call duration: 4 minutes 7 seconds"),
                Metric("audiocodes_average_call_duration", 247.0),
                Result(state=State.OK, summary="Active calls in: 151"),
                Metric("audiocodes_active_calls_in", 151.0),
                Result(state=State.OK, summary="Active calls out: 153"),
                Metric("audiocodes_active_calls_out", 153.0),
                Result(state=State.OK, notice="Established calls in rate: 0.00/s"),
                Metric("audiocodes_established_calls_in", 0.0),
                Result(state=State.OK, notice="Established calls out rate: 0.00/s"),
                Metric("audiocodes_established_calls_out", 0.0),
                Result(state=State.OK, notice="Answer seizure ratio: 88.00%"),
                Metric("audiocodes_answer_seizure_ratio", 88.0),
                Result(
                    state=State.WARN,
                    notice="Network effectiveness ratio: 94.00% (warn/crit below 95.00%/90.00%)",
                ),
                Metric("audiocodes_network_effectiveness_ratio", 94.0),
                Result(state=State.OK, notice="Abnormal terminated calls in: 12"),
                Metric("audiocodes_abnormal_terminated_calls_in_total", 12.0),
                Result(state=State.OK, notice="Abnormal terminated calls out: 11"),
                Metric("audiocodes_abnormal_terminated_calls_out_total", 11.0),
            ],
            id="Warn on low network effectiveness ratio",
        ),
        pytest.param(
            [[["247", "151", "153", "0", "0", "88", "94", "12", "11"]]],
            {
                "answer_seizure_ratio_lower_levels": ("fixed", (95.0, 90.0)),
            },
            [
                Result(state=State.OK, notice="Average call duration: 4 minutes 7 seconds"),
                Metric("audiocodes_average_call_duration", 247.0),
                Result(state=State.OK, summary="Active calls in: 151"),
                Metric("audiocodes_active_calls_in", 151.0),
                Result(state=State.OK, summary="Active calls out: 153"),
                Metric("audiocodes_active_calls_out", 153.0),
                Result(state=State.OK, notice="Established calls in rate: 0.00/s"),
                Metric("audiocodes_established_calls_in", 0.0),
                Result(state=State.OK, notice="Established calls out rate: 0.00/s"),
                Metric("audiocodes_established_calls_out", 0.0),
                Result(
                    state=State.CRIT,
                    notice="Answer seizure ratio: 88.00% (warn/crit below 95.00%/90.00%)",
                ),
                Metric("audiocodes_answer_seizure_ratio", 88.0),
                Result(state=State.OK, notice="Network effectiveness ratio: 94.00%"),
                Metric("audiocodes_network_effectiveness_ratio", 94.0),
                Result(state=State.OK, notice="Abnormal terminated calls in: 12"),
                Metric("audiocodes_abnormal_terminated_calls_in_total", 12.0),
                Result(state=State.OK, notice="Abnormal terminated calls out: 11"),
                Metric("audiocodes_abnormal_terminated_calls_out_total", 11.0),
            ],
            id="Crit on low answer seizure ratio",
        ),
    ],
)
def test_check_function(
    string_table: Sequence[StringTable],
    params: Mapping[str, NoLevelsT | FixedLevelsT],
    expected: CheckResult,
) -> None:
    calls = parse_audiocodes_calls(string_table)
    assert calls is not None  # Make mypy happy
    assert (
        list(
            check_audiocodes_calls_testable(
                params=params,
                section=calls,
            ),
        )
        == expected
    )
